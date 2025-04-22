
from sentence_transformers import SentenceTransformer, util
from difflib import SequenceMatcher

# File paths
EVALUATION_METRICS = "data/evaluation_metrics.csv"

# General purpose model for sentence embeddings
model = SentenceTransformer("all-MiniLM-L6-v2") 

def is_code(output):
    return output.contains("```python") or output.startswith("```")

def evaluate_output(output1, output2, db):
    # Check if either output is code
    is_code1 = is_code(output1)
    is_code2 = is_code(output2)

    # If both outputs are code, use code metrics
    if is_code1 and is_code2:
        db.loc[len(db)] = [output1, output2, 
                            exact_match(output1, output2), 
                            tree_similarity(output1, output2), 
                            CodeBLEU(output1, output2)]
    # If both outputs are natural language, use natural language metric
    elif not is_code1 and not is_code2:
        db.loc[len(db)] = [output1, output2, 
                            BLEU(output1, output2), 
                            ROUGE(output1, output2), 
                            METEOR(output1, output2)]
                        
    # If one is code and one is natural language, use sentence embedding similarity
    else:
        similarity = sentence_embedding(output1, output2)
        db.loc[len(db)] = [output1, output2, similarity, None, None]


def sentence_embedding(output1, output2):
    embedding1 = model.encode(output1, convert_to_tensor=True)
    embedding2 = model.encode(output2, convert_to_tensor=True)
    return float(util.pytorch_cos_sim(embedding1, embedding2))


def exact_match(output1, output2):
    return SequenceMatcher(None, output1, output2).ratio()


def tree_similarity(output1, output2):
    pass

def CodeBLEU(output1, output2):
    pass

def BLEU(output1, output2):
    pass

def ROUGE(output1, output2):
    pass

def METEOR(output1, output2):
    pass


def main():
    evaluation_metrics = pd.read_csv(EVALUATION_METRICS) 

if __name__ == "__main__":
    main()
