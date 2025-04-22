from openai import OpenAI
from collections import deque
import pandas as pd
import time
import os
import logging
from azure.core.credentials import AzureKeyCredential

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

OUTPUT_DATABASE = "data/output_db.csv"
TEMP_DATABASE = "data/temp_output_db.csv"  # For saving progress

# Rate limiting configuration
request_times = deque(maxlen=3)  # Keep track of last 3 request times
MIN_REQUEST_INTERVAL = 20  # 20 seconds between requests (3 per minute)

# Error message 
ERROR_MESSAGE = "ERROR: Failed to process"

def wait_for_rate_limit():
    """Wait if needed to respect rate limits"""
    if len(request_times) > 0:
        time_since_last_request = time.time() - request_times[-1]
        if time_since_last_request < MIN_REQUEST_INTERVAL:
            wait_time = MIN_REQUEST_INTERVAL - time_since_last_request
            logging.info(f"Rate limiting: waiting {wait_time:.2f} seconds...")
            time.sleep(wait_time)
    request_times.append(time.time())

def process_row(row, client, model):
    """Process a single row with retries and error handling"""
    prompt = row['Prompt']
    output_m1 = row['Output Model 1: OpenAI GPT-4']
    output_m2 = row['Output Model 2: Mistral Large']
    
    system_prompt = "You are an expert judge evaluating the performance of two large language models—Mistral Large and OpenAI GPT-4—on the following programming prompt: " + prompt 
    user_prompt = "Please compare Model 1 (GPT-4) and Model 2 (Mistral Large) using correctness, completeness, code quality, and efficiency as the criteria. In your response, include a brief summary for each model's performance under each criterion and a final recommendation of which model performed better overall and why. \n" + \
        "Model 1 (OpenAI GPT-4): " + output_m1 + "\n" + \
        "Model 2 (Mistral Large): " + output_m2
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    try:
        wait_for_rate_limit()
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=4096,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"API request failed: {str(e)}")
        return ERROR_MESSAGE

def main():
    # Read in token
    with open("token", "r") as f:
        GITHUB_TOKEN = f.read().strip()

    # Set GitHub token as an environment variable
    os.environ["GITHUB_TOKEN"] = GITHUB_TOKEN
    token = os.environ["GITHUB_TOKEN"]
    
    # Base endpoint URL
    endpoint = "https://models.github.ai/inference"
    
    # Initialize the client
    client = OpenAI(
        api_key=token,
        base_url=endpoint
    )

    # Model configuration
    model = "meta/Llama-4-Maverick-17B-128E-Instruct-FP8"

    # Read csv 
    output_db = pd.read_csv(OUTPUT_DATABASE)
    for i in range(len(output_db)):
        row = output_db.iloc[i]

        # Skip if already completed
        if row['Completed'] == 1:
            continue

        # Process row
        result = process_row(row, client, model)
        if result == ERROR_MESSAGE:
            continue
        
        # Update output database with completed status and output
        output_db.loc[i, 'Completed'] = 1
        output_db.loc[i, 'Output Model 3: Meta Llama 3.1 405B'] = result
        output_db.to_csv(OUTPUT_DATABASE, index=False)

if __name__ == "__main__":
    main()
