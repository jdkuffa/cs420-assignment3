from openai import OpenAI
from collections import deque
import pandas as pd
import time
import os
import requests
import json
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

# Model configurations
endpoint = "https://models.github.ai/inference"

openai_model = "openai/gpt-4.1"
mistral_model = "mistral/mistral-large"
llama_model = "meta/llama-3.1-405b"

# Initialize clients
openai_client = ChatCompletionsClient(
    endpoint=endpoint,
    credential=AzureKeyCredential(token)
)

mistral_client = ChatCompletionsClient(
    endpoint=endpoint,
    credential=AzureKeyCredential(token)
)

llama_client = ChatCompletionsClient(
    endpoint=endpoint,
    credential=AzureKeyCredential(token)
)

# Model configurations with their specific parameters
models = {
    "gpt-4": {
        "client": openai_client,
        "model": openai_model,
        "max_tokens": 2048,
        "temperature": 0.7,
        "top_p": 1
    },
    "mistral-large": {
        "client": mistral_client,
        "model": mistral_model,
        "max_tokens": 2048,
        "temperature": 0.7,
        "top_p": 1
    },
    "llama": {
        "client": llama_client,
        "model": llama_model,
        "max_tokens": 2048,
        "temperature": 0.7,
        "top_p": 1
    }
}

# Rate limiting variables
request_times = deque(maxlen=3)  # Keep track of last 3 request times
MIN_REQUEST_INTERVAL = 20  # 20 seconds between requests (3 per minute)


def prompt_chaining(input, code, model, client):
    # Split input into individual prompts
    prompts = []
    current_prompt = ""
    for line in input.split('\n'):
        if line.startswith("Prompt "):
            if current_prompt:
                prompts.append(current_prompt.strip())
            current_prompt = line.split(":", 1)[1].strip()
        else:
            current_prompt += "\n" + line
    if current_prompt:
        prompts.append(current_prompt.strip())
    
    # Add code to first prompt
    prompts[0] += "\n\n" + code
    
    outputs = []
    messages = [{"role": "user", "content": prompts[0]}]
    
    # Process each prompt in sequence
    for i in range(len(prompts)):
        response = send_response(messages, model)
        reply = response.choices[0].message.content
        outputs.append(reply)
        
        if i < len(prompts) - 1:
            messages.append({"role": "assistant", "content": reply})
            messages.append({"role": "user", "content": prompts[i + 1]})
    
    return "\n\n".join(outputs)


def self_consistency(input, code, model, client):
    prompt = input + "\n\n" + code
    messages = [{"role": "user", "content": prompt}]
    
    outputs = []
    for attempt in range(2):
        response = send_response(messages, model)
        outputs.append(f"Output Attempt {attempt + 1}:\n{response.choices[0].message.content}\n")
    
    return "\n".join(outputs)


def zero_few_cot(input, code, model, client):
  prompt = input + code
  messages = [{"role": "user", "content": prompt}]
  try:
    response = send_response(messages, model)
    return response.choices[0].message.content
  except Exception as e:
    print(f"Error making API request: {e}")
    return "Error"


def send_response(messages, model_name):
    # Check if we need to wait for rate limiting
    if len(request_times) > 0:
        time_since_last_request = time.time() - request_times[-1]
        print(f"Time since last request: {time_since_last_request:.2f} seconds")
        if time_since_last_request < MIN_REQUEST_INTERVAL:
            wait_time = MIN_REQUEST_INTERVAL - time_since_last_request
            print(f"Waiting {wait_time:.2f} seconds for rate limiting...")
            time.sleep(wait_time)
    request_times.append(time.time())

    model_config = models[model_name]
    print(f"Sending request to {model_name}...")

    try:
        # Send the request using Azure client
        response = model_config["client"].complete(
            model=model_config["model"],
            messages=messages,
            max_tokens=model_config["max_tokens"],
            temperature=model_config["temperature"],
            top_p=model_config["top_p"]
        )

        print(f"Received response from {model_name}")
        return response
    except Exception as e:
        print(f"Error making API request to {model_name}: {e}")
        # Add a longer delay before retrying
        time.sleep(60)
        return send_response(messages, model_name)  # Retry the request


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


def process_prompt_with_models(prompt_strat, prompt_input, code, model_choices):
    outputs = []
    for model in model_choices:
        print(f"\nProcessing prompt with {model}...")
        output = send_response(
            [{"role": "user", "content": prompt_input + "\n\n" + code}],
            model
        )
        
        if output is None:
            print(f"Failed to get response from {model}, trying next model...")
            continue
            
        print(f"Completed prompt with {model}")
        outputs.append(output.choices[0].message.content)
        
        # If we got a successful response, we can stop trying other models
        if output:
            break
    
    # If all models failed, return a default error message
    if not outputs:
        outputs = ["Error: All model requests failed or timed out"]
    
    return outputs


def add_results_to_db(output_db, problem_idx, prompt_input, prompt_outputs):
    output_db.loc[len(output_db)] = [problem_idx, prompt_input] + prompt_outputs
    print("Results added to output database")


def update_processing_status(input_db, row_idx, completed=True):
    input_db.at[row_idx, 'Completed'] = 1 if completed else 0
    print(f"Updated completion status for row {row_idx} to {completed}")


def process_problem(row, row_idx, model_choices):
    print("Extracting problem data...")
    code = row['Code Input']
    prompt_1_strat = row['Prompt 1 Strategy']
    prompt_1_input = row['Prompt 1']
    prompt_2_strat = row['Prompt 2 Strategy']
    prompt_2_input = row['Prompt 2']
    print(f"Problem data extracted: Strategy1={prompt_1_strat}, Strategy2={prompt_2_strat}")
    
    try:
        # Process both prompts with all models
        prompt_1_outputs = process_prompt_with_models(prompt_1_strat, prompt_1_input, code, model_choices)
        prompt_2_outputs = process_prompt_with_models(prompt_2_strat, prompt_2_input, code, model_choices)
        
        # Only mark as completed if both prompts were processed successfully
        if prompt_1_outputs and prompt_2_outputs:
            update_processing_status(input_db, row_idx, completed=True)
            return prompt_1_input, prompt_1_outputs, prompt_2_input, prompt_2_outputs
        else:
            print(f"Failed to process problem {row_idx + 1}, will retry in next run")
            update_processing_status(input_db, row_idx, completed=False)
            return None, None, None, None
    except Exception as e:
        print(f"Error processing problem {row_idx + 1}: {e}")
        update_processing_status(input_db, row_idx, completed=False)
        return None, None, None, None


def main():
    # Start timing the entire script
    script_start_time = time.time()
    print("\n=== Starting script execution ===")

    # Use the available GitHub Education Pack models
    model_choices = list(models.keys())
    print(f"\nUsing models: {model_choices}")
    
    print("\nReading input database...")
    input_db = pd.read_csv(INPUT_DATABASE)
    
    if 'Completed' not in input_db.columns:
        input_db = input_db.assign(Completed=0)
        print("Added Completed column to input database")
    
    print(f"Successfully read {len(input_db)} rows from input database")
    
    output_db_cols = [
        "Problem", "Prompt"
    ] + [f"{model} Output" for model in model_choices]
    
    output_db = pd.DataFrame(columns=pd.Index(output_db_cols))
    print("\nCreated output database structure")
    
    for i in range(len(input_db)):
        # Skip already completed rows
        if input_db.at[i, 'Completed'] == 1:
            print(f"\nSkipping already completed problem {i+1}/{len(input_db)}")
            break
            
        # Start timing each problem
        problem_start_time = time.time()
        print(f"\n=== Processing problem {i+1}/{len(input_db)} ===")
        
        print(f"\nReading row {i} from input database...")
        row = input_db.iloc[i]
        
        # Process the problem and get all outputs
        prompt_1_input, prompt_1_outputs, prompt_2_input, prompt_2_outputs = process_problem(row, i, model_choices)
        
        # Only add to output database if processing was successful
        if prompt_1_outputs and prompt_2_outputs:
            add_results_to_db(output_db, i, prompt_1_input, prompt_1_outputs)
            add_results_to_db(output_db, i, prompt_2_input, prompt_2_outputs)
        
        # Print timing for each problem
        problem_time = time.time() - problem_start_time
        print(f"\nProblem {i+1} completed in {problem_time:.2f} seconds")
    
    print("\nWriting output database to file...")
    output_db.to_csv(OUTPUT_DATABASE, index=False)
    print("Output database written successfully")
    
    # Save the final state of the input database
    input_db.to_csv(INPUT_DATABASE, index=False)
    print("Input database updated successfully")
    
    # Print total script execution time
    total_time = time.time() - script_start_time
    print(f"\n=== Script completed ===")
    print(f"Total execution time: {total_time:.2f} seconds")
    print(f"Average time per problem: {total_time/3:.2f} seconds")


if __name__ == "__main__":
  main()
