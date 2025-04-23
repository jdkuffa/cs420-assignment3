import pandas as pd
import os

# File paths
INPUT_FILE = 'data/data.csv'
OUTPUT_FILE = 'data/output.csv'

# Column names
OUTPUT_COLUMNS = [
    "Problem",
    "Prompt Strategy",
    "Prompt",
    "Model 1: OpenAI GPT-4",
    "Model 2: Mistral Large",
    "Model 3: Meta Llama 3.1 405B"
]

def validate_input_data(df):
    required_columns = ['Problem', 'Code Input', 'Prompt 1', 'Prompt 2', 
                       'Prompt 1 Strategy', 'Prompt 2 Strategy']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")


def process_prompts(row):
    problem = row['Problem']
    code = row['Code Input']
    
    return [
        {
            'Problem': problem,
            'Prompt Strategy': row['Prompt 1 Strategy'].lower(),
            'Prompt': row['Prompt 1'] + code,
            'Model 1: OpenAI GPT-4': '',
            'Model 2: Mistral Large': '',
            'Model 3: Meta Llama 3.1 405B': ''
        },
        {
            'Problem': problem,
            'Prompt Strategy': row['Prompt 2 Strategy'].lower(),
            'Prompt': row['Prompt 2'] + code,
            'Model 1: OpenAI GPT-4': '',
            'Model 2: Mistral Large': '',
            'Model 3: Meta Llama 3.1 405B': ''
        }
    ]

def main():
    try:
        # Read input data
        if not os.path.exists(INPUT_FILE):
            raise FileNotFoundError(f"Input file {INPUT_FILE} not found")
            
        df = pd.read_csv(INPUT_FILE)
        validate_input_data(df)
        
        # Process all rows and create output DataFrame
        processed_rows = []
        for _, row in df.iterrows():
            processed_rows.extend(process_prompts(row))
            
        output_df = pd.DataFrame(processed_rows, columns=OUTPUT_COLUMNS)
        
        # Save output
        output_df.to_csv(OUTPUT_FILE, index=False)
        print(f"Successfully processed data and saved to {OUTPUT_FILE}")
        
    except Exception as e:
        print(f"Error processing data: {str(e)}")
        raise

if __name__ == "__main__":
    main()