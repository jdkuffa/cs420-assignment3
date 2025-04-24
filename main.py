from openai import OpenAI
from collections import deque
import pandas as pd
import time
import os
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential


# File paths
INPUT_DATABASE = "data/database_complete_column.csv"
OUTPUT_DATABASE = "data/output_db.csv"

# Read in token
with open("token", "r") as f:
    GITHUB_TOKEN = f.read().strip()

# Set GitHub token as an environment variable
os.environ["GITHUB_TOKEN"] = GITHUB_TOKEN
token = os.environ["GITHUB_TOKEN"]
endpoint = "https://models.github.ai/inference"

# Microsoft Azure AI configuration
azure_model = "microsoft/MAI-DS-R1"

azure_client = ChatCompletionsClient(
    endpoint=endpoint,
    credential=AzureKeyCredential(token),
)

# Mistral AI configuration
mistral_model = "Codestral-2501"

mistral_client = ChatCompletionsClient(
    endpoint=endpoint,
    credential=AzureKeyCredential(token),
)

# Rate limiting variables
request_times = deque(maxlen=3)  # Keep track of last 3 request times
MIN_REQUEST_INTERVAL = 20  # 20 seconds between requests (3 per minute)


def prompt_chaining(input, code, model):
  prompts = []
  outputs = []
  for i in range(len(input)):
    prompt = input.split("Prompt " + str(i + 1) + ": ")
    if i == 0:
      prompt.append(code)
    prompts.append("".join(prompt))

  # First prompt
  messages = [{"role": "user", "content": prompts[0]}]

  # Go through prompts
  for i in range(len(prompts) - 1):
    response = send_response(messages, model, client)
    reply = response.choices[0].message.content
    outputs.append(reply)
    messages.append({"role": "system", "content": reply})
    followup = prompts[i + 1]
    messages.append({"role": "user", "content": followup})

  return "".join(outputs)


def self_consistency(input, code, model, client):
  prompt = input + code
  messages = {"role": "user", "content": prompt}

  outputs = []
  for attempt in range(2):
    response = send_response(messages, model, client)
    outputs.append("Output Attempt " + str(attempt) + ": " +
                   response.choices[0].message.content + "\n\n")

  return "".join(outputs)


def zero_few_cot(input, code, model, client):
  prompt = input + code
  messages = [{"role": "user", "content": prompt}]
  try:
    response = send_response(messages, model, client)
    return response.choices[0].message.content
  except Exception as e:
    print(f"Error making API request: {e}")
    return "Error"


def send_response(messages, model, client):
    # Check if we need to wait for rate limiting
    if len(request_times) > 0:
        time_since_last_request = time.time() - request_times[-1]
        print(f"Time since last request: {time_since_last_request:.2f} seconds")
        if time_since_last_request < MIN_REQUEST_INTERVAL:
            wait_time = MIN_REQUEST_INTERVAL - time_since_last_request
            print(f"Waiting {wait_time:.2f} seconds for rate limiting...")
            time.sleep(wait_time)
    request_times.append(time.time())

    # Convert messages based on model type
    if model == "microsoft/MAI-DS-R1":
        formatted_messages = convert_to_azure_messages(messages)
        # Azure request
        try:
            response = client.complete(
                model=model,
                messages=formatted_messages,
                max_tokens=2048,
                temperature=0.7
            )
        except Exception as e:
            print(f"Error making API request to {model}: {e}")
            time.sleep(60)
            return send_response(messages, model, client)
    else:  # Codestral-2501
        formatted_messages = messages  # Use original format
        # Codestral request with publisher
        try:
            response = client.complete(
                model=model,
                messages=formatted_messages,
                max_tokens=2048,
                temperature=0.7,
                publisher="codestral"  # Add publisher for Codestral requests
            )
        except Exception as e:
            print(f"Error making API request to {model}: {e}")
            time.sleep(60)
            return send_response(messages, model, client)

    print(f"Received response from {model}")
    return response


def select_strategy(strategy, input, code, model, client):
  strategy = strategy.lower()
  if strategy == "zero shot" or strategy == "few shot" or strategy == "chain of thought":
    return zero_few_cot(input, code, model, client)
  elif strategy == "prompt chaining":
    return "Not implemented"
    # return prompt_chaining(input, code, model)
  elif strategy == "self consistency":
    return "Not implemented"
    # return self_consistency(input, code, model)


def convert_to_azure_messages(messages):
  azure_messages = []
  for msg in messages:
    if msg["role"] == "user":
      azure_messages.append(UserMessage(content=msg["content"]))
    elif msg["role"] == "system":
      azure_messages.append(SystemMessage(content=msg["content"]))
  return azure_messages


def main():
    # Start timing the entire script
    script_start_time = time.time()
    print("\n=== Starting script execution ===")

    model_choices = [azure_model, mistral_model]
    clients = [azure_client, mistral_client]

    print(f"\nUsing models: {model_choices}")
    
    print("\nReading input database...")
    input_db = pd.read_csv(INPUT_DATABASE)
    print(f"Successfully read {len(input_db)} rows from input database")
    
    output_db_cols = [
        "Problem", "Prompt", model_choices[0] + " Output", model_choices[1] + " Output"
    ]
    output_db = pd.DataFrame(columns=pd.Index(output_db_cols))
    print("\nCreated output database structure")
    
    for i in range(len(input_db)):
        # Check if problem has been completed 
        row = input_db.iloc[i]
        completed = row['Completed']
        if completed == 1:
          continue

        # Start timing each problem
        problem_start_time = time.time()
        print(f"\n=== Processing problem {i+1}/{len(input_db)-1} ===")
        
        print(f"\nReading row {i} from input database...")
        

        print("Extracting problem data...")
        code = row['Code Input']
        prompt_1_strat = row['Prompt 1 Strategy']
        prompt_1_input = row['Prompt 1']
        prompt_2_strat = row['Prompt 2 Strategy']
        prompt_2_input = row['Prompt 2']
        print(f"Problem data extracted: Strategy1={prompt_1_strat}, Strategy2={prompt_2_strat}")
        
        print("\nProcessing Prompt 1 with GPT-4...")
        prompt_1_output_m1 = select_strategy(prompt_1_strat, prompt_1_input, code, model_choices[0], clients[0])
        print("Completed Prompt 1 with GPT-4")
        
        print("\nProcessing Prompt 2 with GPT-4...")
        prompt_2_output_m1 = select_strategy(prompt_2_strat, prompt_2_input, code, model_choices[0], clients[0])
        print("Completed Prompt 2 with GPT-4")

        print("\nProcessing Prompt 1 with Mistral Large...")
        prompt_1_output_m2 = select_strategy(prompt_1_strat, prompt_1_input, code, model_choices[1], clients[1])
        print("Completed Prompt 1 with Mistral Large")
        
        print("\nProcessing Prompt 2 with Mistral Large...")
        prompt_2_output_m2 = select_strategy(prompt_2_strat, prompt_2_input, code, model_choices[1], clients[1])
        print("Completed Prompt 2 with Mistral Large")
        
        print("\nAdding results to output database...")
        output_db.loc[len(output_db)] = [
            i, prompt_1_input, prompt_1_output_m1, prompt_1_output_m2, prompt_1_output_m3
        ]
        output_db.loc[len(output_db)] = [
            i, prompt_2_input, prompt_2_output_m1, prompt_2_output_m2, prompt_2_output_m3
        ]
        print("Results added to output database")
        
        # Print timing for each problem
        problem_time = time.time() - problem_start_time
        print(f"\nProblem {i+1} completed in {problem_time:.2f} seconds")

        # Update completed column 
        input_db.iloc[i]['Completed'] = 1 
    
    print("\nWriting output database to file...")
    output_db.to_csv(OUTPUT_DATABASE, index=False)
    print("Output database written successfully")

    # Save updated input database 
    input_db.to_csv(INPUT_DATABASE, index=False)
    
    # Print total script execution time
    total_time = time.time() - script_start_time
    print(f"\n=== Script completed ===")
    print(f"Total execution time: {total_time:.2f} seconds")
    print(f"Average time per problem: {total_time/3:.2f} seconds")


if __name__ == "__main__":
  main()