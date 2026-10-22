"""
Query Generator for WikiSearch Benchmarking.

Generates 100+ diverse queries from the actual built index:
- 50 Title-based known-item queries (expects exact article)
- 30 Distinctive 2-3 word phrase queries from article bodies
- 25 General topic queries
Saves query set to benchmark/queries.json.
"""
import json
from pathlib import Path
import random
import re

from backend.index_reader import IndexReader
from indexer.tokenizer import tokenize_terms


TOPIC_QUERIES = [
    ("computer science", "keyword"),
    ("artificial intelligence", "keyword"),
    ("world war ii", "keyword"),
    ("solar system", "keyword"),
    ("renewable energy", "keyword"),
    ("quantum mechanics", "keyword"),
    ("french revolution", "keyword"),
    ("ancient egypt", "keyword"),
    ("machine learning", "keyword"),
    ("climate change", "keyword"),
    ("dna replication", "keyword"),
    ("black hole", "keyword"),
    ("industrial revolution", "keyword"),
    ("operating system", "keyword"),
    ("plate tectonics", "keyword"),
    ("roman empire", "keyword"),
    ("periodic table", "keyword"),
    ("photosynthesis", "keyword"),
    ("internet protocol", "keyword"),
    ("general relativity", "keyword"),
    ("united nations", "keyword"),
    ("evolutionary biology", "keyword"),
    ("gravitational wave", "keyword"),
    ("cellular respiration", "keyword"),
    ("renaissance art", "keyword"),
]


def generate_queries(index_dir: str = "data/index", output_path: str = "benchmark/queries.json") -> Path:
    reader = IndexReader(index_dir)
    num_docs = reader.num_docs
    random.seed(42)  # Deterministic seed for reproducible benchmarks
    
    queries = []
    query_id = 1
    
    # 1. 50 Title Known-Item Queries
    print("[*] Generating 50 Title Known-Item Queries...")
    sampled_doc_ids = random.sample(range(num_docs), 100)
    title_count = 0
    
    for doc_id in sampled_doc_ids:
        if title_count >= 50:
            break
        title, doc_len, _, _ = reader.get_doc_metadata(doc_id)
        # Avoid titles with disambiguation brackets or too short/long
        if "(" in title or "/" in title or len(title) < 4 or len(title) > 40:
            continue
        terms = tokenize_terms(title)
        if len(terms) < 1 or len(terms) > 4:
            continue
            
        queries.append({
            "query_id": f"q_{query_id:04d}",
            "query_text": title,
            "mode": "keyword",
            "type": "title_known_item",
            "expected_doc_id": doc_id,
            "expected_title": title,
        })
        query_id += 1
        title_count += 1

    # 2. 30 Distinctive Phrase Queries
    print("[*] Generating 30 Exact-Phrase Queries from article bodies...")
    phrase_count = 0
    phrase_samples = random.sample(range(num_docs), 200)
    
    for doc_id in phrase_samples:
        if phrase_count >= 30:
            break
        title, text, doc_len = reader.get_article_text(doc_id)
        if doc_len < 50:
            continue
            
        terms = tokenize_terms(text)
        if len(terms) < 30:
            continue
            
        # Pick 2-word or 3-word n-gram that is distinctive
        start_idx = random.randint(10, len(terms) - 10)
        phrase_len = random.choice([2, 3])
        ngram = terms[start_idx : start_idx + phrase_len]
        
        # Avoid phrases with numbers only or common stopwords
        if any(len(t) < 3 for t in ngram):
            continue
            
        phrase_text = " ".join(ngram)
        queries.append({
            "query_id": f"q_{query_id:04d}",
            "query_text": phrase_text,
            "mode": "phrase",
            "type": "exact_phrase",
            "expected_doc_id": doc_id,
            "expected_title": title,
        })
        query_id += 1
        phrase_count += 1

    # 3. 25 Topic Queries
    print("[*] Adding 25 General Topic Queries...")
    for topic, mode in TOPIC_QUERIES:
        queries.append({
            "query_id": f"q_{query_id:04d}",
            "query_text": topic,
            "mode": mode,
            "type": "topic_query",
            "expected_doc_id": None,
            "expected_title": None,
        })
        query_id += 1

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(queries, f, indent=2)

    print(f"[+] Successfully generated {len(queries)} queries to {out_file.resolve()}!")
    return out_file


if __name__ == "__main__":
    generate_queries()
