import os
import pandas as pd
from sentence_transformers import SentenceTransformer, util
from difflib import SequenceMatcher
from nltk.tokenize import word_tokenize
import collections
import math
import nltk

# File paths - use absolute paths from project root
EVALUATION_METRICS = "data/evaluation_metrics.csv"
OUTPUT_DATABASE = "data/output_db.csv"

# General purpose model for sentence embeddings
model = None

# Download the punkt tokenizer
print("Downloading tokenizer...")
nltk.download('punkt')
nltk.download('punkt_tab')


def get_model():
    global model
    if model is None:
        print("Loading sentence transformer model...")
        model = SentenceTransformer("all-MiniLM-L6-v2")
    return model


def is_code(output):
    return "```" in output


def evaluate_output(output1, output2, db):    
    # Check if either output is code
    is_code1 = is_code(output1)
    is_code2 = is_code(output2)
    print(f"Output1 is code: {is_code1}, Output2 is code: {is_code2}")

    # If both outputs are code, use code metrics
    if is_code1 and is_code2:
        score = compute_exact_match(output1, output2)
        metric = f"Exact match: {score}"
        print(f"Using exact match metric: {score}")
    
    # If both outputs are natural language, use natural language metric
    elif not is_code1 and not is_code2:
        score = compute_bleu(output1, output2)
        metric = f"BLEU score: {score}"
        print(f"Using BLEU metric: {score}")                    
    
    # If one is code and one is natural language, use sentence embedding similarity
    else:
        score = sentence_embedding(output1, output2)
        metric = f"Sentence embedding similarity: {score}"
        print(f"Using sentence embedding metric: {score}")
    
    # Add to DataFrame
    print(f"Adding to DataFrame. Current shape: {db.shape}")
    
    new_row = pd.DataFrame([[output1, output2, metric]], columns=['output1', 'output2', 'metric'])
    db = pd.concat([db, new_row], ignore_index=True)
    
    print(f"New DataFrame shape: {db.shape}")
    
    return db

def sentence_embedding(output1, output2):
    model = get_model()
    embedding1 = model.encode(output1, convert_to_tensor=True)
    embedding2 = model.encode(output2, convert_to_tensor=True)
    return float(util.pytorch_cos_sim(embedding1, embedding2))


def compute_exact_match(output1, output2):
    return SequenceMatcher(None, output1, output2).ratio()


def _get_ngrams(segment, max_order):
    ngram_counts = collections.Counter()
    for order in range(1, max_order + 1):
        for i in range(0, len(segment) - order + 1):
            ngram = tuple(segment[i:i + order])
            ngram_counts[ngram] += 1
    return ngram_counts


def compute_bleu(output1, output2, max_order=4, smooth=False):
    # Tokenize the outputs
    tokens1 = word_tokenize(output1.lower())
    tokens2 = word_tokenize(output2.lower())

    # Get n-grams
    ref_ngram_counts = _get_ngrams(tokens1, max_order)
    translation_ngram_counts = _get_ngrams(tokens2, max_order)
    
    # Calculate matches and possible matches
    matches_by_order = [0] * max_order
    possible_matches_by_order = [0] * max_order
    
    # Calculate overlap
    overlap = translation_ngram_counts & ref_ngram_counts
    for ngram in overlap:
        matches_by_order[len(ngram)-1] += overlap[ngram]
    
    for order in range(1, max_order + 1):
        possible_matches = len(tokens2) - order + 1
        if possible_matches > 0:
            possible_matches_by_order[order-1] += possible_matches
    
    # Calculate precisions
    precisions = [0] * max_order
    for i in range(0, max_order):
        if smooth:
            precisions[i] = ((matches_by_order[i] + 1.) /
                           (possible_matches_by_order[i] + 1.))
        else:
            if possible_matches_by_order[i] > 0:
                precisions[i] = (float(matches_by_order[i]) /
                               possible_matches_by_order[i])
            else:
                precisions[i] = 0.0

    # Calculate geometric mean
    if min(precisions) > 0:
        p_log_sum = sum((1. / max_order) * math.log(p) for p in precisions)
        geo_mean = math.exp(p_log_sum)
    else:
        geo_mean = 0
    
    # Calculate brevity penalty
    ratio = float(len(tokens2)) / len(tokens1)
    if ratio > 1.0:
        bp = 1.
    else:
        bp = math.exp(1 - 1. / ratio)
    
    # Calculate final BLEU score
    bleu = geo_mean * bp
    return bleu


def main():
    print(f"Starting evaluation metrics processing...")
    print(f"Looking for evaluation metrics file at: {EVALUATION_METRICS}")
    
    # Create the data directory if it doesn't exist
    if not os.path.exists(os.path.dirname(EVALUATION_METRICS)):
        print(f"Creating data directory: {os.path.dirname(EVALUATION_METRICS)}")
        os.makedirs(os.path.dirname(EVALUATION_METRICS), exist_ok=True)
    
    # Read the CSV file
    try:
        print("Attempting to read evaluation metrics file...")
        evaluation_metrics = pd.read_csv(EVALUATION_METRICS)
        print(f"Successfully read evaluation metrics file. Current shape: {evaluation_metrics.shape}")
    except Exception as e:
        print("Warning: File is empty or missing. Creating new DataFrame...")
        evaluation_metrics = pd.DataFrame(columns=['output1', 'output2', 'metric'])
        evaluation_metrics.to_csv(EVALUATION_METRICS, index=False)
        print("New DataFrame created and saved to file")
    
    # Read the output database
    print("Reading output database...")
    output_db = pd.read_csv(OUTPUT_DATABASE)
    print(f"Found {len(output_db)} outputs to evaluate")
    
    # Get the model output columns
    model_columns = [col for col in output_db.columns if col.startswith('Output Model')]
    print(f"Found model columns: {model_columns}")
    
    # Evaluate pairs of model outputs
    for i in range(len(model_columns)-1):
        for j in range(i+1, len(model_columns)):
            model1 = model_columns[i]
            model2 = model_columns[j]
            print(f"\nComparing {model1} and {model2}...")
            
            # Compare outputs for each problem
            for _, row in output_db.iterrows():
                output1 = row[model1]
                output2 = row[model2]
                
                # Skip if either output is empty
                if pd.isna(output1) or pd.isna(output2):
                    print(f"Skipping empty outputs") # for {row['Problem']}")
                    continue
                    
                # print(f"Evaluating outputs for problem: {row['Problem']}")
                evaluate_output(output1, output2, evaluation_metrics)
    
    # Save the updated metrics
    print("\nSaving evaluation metrics...")
    print(f"Final DataFrame shape before saving: {evaluation_metrics.shape}")
    print(f"First few rows of DataFrame:\n{evaluation_metrics.head()}\n")

    evaluation_metrics.to_csv(EVALUATION_METRICS, index=False)

    print(f"Evaluation metrics saved. Final shape: {evaluation_metrics.shape}")
    print("Evaluation metrics processing completed")


if __name__ == "__main__":
    main() 