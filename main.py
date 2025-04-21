from openai import OpenAI
from collections import deque
import pandas as pd
import time
import os


# File paths
INPUT_DB = "data/data.csv"
OUTPUT_DB = "data/output_db.csv"

# Read in token
with open("token", "r") as f:
    GITHUB_TOKEN = f.read().strip()

# Set GitHub token as an environment variable
os.environ["GITHUB_TOKEN"] = GITHUB_TOKEN

# OpenAI client
client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.environ["GITHUB_TOKEN"],
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
    response = send_response(messages, model)
    reply = response.choices[0].message.content
    outputs.append(reply)
    messages.append({"role": "system", "content": reply})
    followup = prompts[i + 1]
    messages.append({"role": "user", "content": followup})

  return "".join(outputs)


def self_consistency(input, code, model):
  prompt = input + code
  messages = {"role": "user", "content": prompt}

  # Generate 5 output attempts for each prompt
  outputs = []
  for attempt in range(5):
    response = send_response(messages, model)
    outputs.append("Output Attempt " + str(attempt) + ": " +
                   response.choices[0].message.content + "\n\n")

  return "".join(outputs)


def zero_few_cot(input, code, model):
  prompt = input + code
  messages = [{"role": "user", "content": prompt}]
  response = send_response(messages, model)
  return response.choices[0].message.content


def send_response(messages, model):
  # Check if we need to wait for rate limiting
  if len(request_times) > 0:
    time_since_last_request = time.time() - request_times[-1]
    if time_since_last_request < MIN_REQUEST_INTERVAL:
      time.sleep(MIN_REQUEST_INTERVAL - time_since_last_request)
  request_times.append(time.time())

  # Send request
  response = client.chat.completions.create(
      model=model,
      messages=messages,
      max_tokens=1024,
      temperature=0.7,
  )

  print("Response: ", response.choices[0].message.content)
  return response


def select_strategy(strategy, input, code, model):
  strategy = strategy.lower()
  if strategy == "zero shot" or strategy == "few shot" or strategy == "chain of thought":
    return zero_few_cot(input, code, model)
  elif strategy == "prompt chaining":
    return prompt_chaining(input, code, model)
  elif strategy == "self consistency":
    return self_consistency(input, code, model)


def main():
    # Start timing the entire script
    script_start_time = time.time()
    
    model_choices = ["microsoft/MAI-DS-R1", "Codestral-2501"]
    input_db = pd.read_csv(INPUT_DB)
    
    output_db_cols = [
        "Problem", "Prompt", model_choices[0] + " Output",
        model_choices[1] + " Output"
    ]
    output_db = pd.DataFrame(columns=pd.Index(output_db_cols))
    
    for i in range(3):
        # Start timing each problem
        problem_start_time = time.time()
        print(f"\nProcessing problem {i+1}/3...")
        
        row = input_db.iloc[i]
        code = row['Code Input']
        prompt_1_strat = row['Prompt 1 Strategy']
        prompt_1_input = row['Prompt 1']
        prompt_2_strat = row['Prompt 2 Strategy']
        prompt_2_input = row['Prompt 2']
        
        # Get outputs from both models for each prompt
        prompt_1_output_m0 = select_strategy(prompt_1_strat, prompt_1_input, code, model_choices[0])
        prompt_1_output_m1 = select_strategy(prompt_1_strat, prompt_1_input, code, model_choices[1])
        
        prompt_2_output_m0 = select_strategy(prompt_2_strat, prompt_2_input, code, model_choices[0])
        prompt_2_output_m1 = select_strategy(prompt_2_strat, prompt_2_input, code, model_choices[1])
        
        # Add outputs to output_db
        output_db.loc[len(output_db)] = [
            i, prompt_1_input, prompt_1_output_m0, prompt_1_output_m1
        ]
        output_db.loc[len(output_db)] = [
            i, prompt_2_input, prompt_2_output_m0, prompt_2_output_m1
        ]
        
        # Print timing for this problem
        problem_time = time.time() - problem_start_time
        print(f"Problem {i+1} completed in {problem_time:.2f} seconds")
    
    output_db.to_csv(OUTPUT_DB, index=False)
    
    # Print total script execution time
    total_time = time.time() - script_start_time
    print(f"\nTotal execution time: {total_time:.2f} seconds")
    print(f"Average time per problem: {total_time/3:.2f} seconds")


if __name__ == "__main__":
  main()
