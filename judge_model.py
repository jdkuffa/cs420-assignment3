from openai import OpenAI
from collections import deque
import pandas as pd
import time
import os
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential



OUTPUT_DATABASE = "data/output_db.csv"

def convert_to_azure_messages(messages):
  azure_messages = []
  for msg in messages:
    if msg["role"] == "user":
      azure_messages.append(UserMessage(content=msg["content"]))
    elif msg["role"] == "system":
      azure_messages.append(SystemMessage(content=msg["content"]))
  return azure_messages


def main():
    # Read in token
    with open("token", "r") as f:
        GITHUB_TOKEN = f.read().strip()

    # Set GitHub token as an environment variable
    os.environ["GITHUB_TOKEN"] = GITHUB_TOKEN
    token = os.environ["GITHUB_TOKEN"]
    endpoint = "https://models.github.ai/inference"

    # Llama AI configuration
    llama_model = "meta/Llama-3.1-405B"

    llama_client = ChatCompletionsClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(token),
    )

    # Read csv 
    output_db = pd.read_csv(OUTPUT_DATABASE)
    for i in range(len(output_db)):
        row = output_db.iloc[i]
        prompt = row['Prompt']
        output_m1 = row['Output Model 1']
        output_m2 = row['Output Model 2']
        system_prompt = "You are an expert judge evaluating the performance of two large language models—Mistral Large and OpenAI GPT-4—on the following programming prompt: " + prompt 
        user_prompt = "Please compare Model 1 (GPT-4) and Model 2 (Mistral Large) using correctness, completeness, code quality, and efficiency as the criteria. In your response, include a brief summary for each model’s performance under each criterion and a final recommendation of which model performed better overall and why. \n" +
        "Model 1 (OpenAI GPT-4): " + output_m1 + "\n" +
        "Model 2 (Mistral Large): " + output_m2
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
        azure_messages = convert_to_azure_messages(messages)
        response = llama_client.complete(
            model=llama_model,
            messages=azure_messages,
            max_tokens=4096,
            temperature=0.7,
        )
        output_db.loc[i, 'Output Model 3: Meta Llama 3.1 405B'] = response.choices[0].message.content

