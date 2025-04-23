import collections
import math
import nltk
from nltk.tokenize import word_tokenize


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
    
    return compute_bleu