"""
Query Parser and Dispatcher for WikiSearch.
Uses the identical shared tokenizer to process incoming user queries.
"""
from typing import List, Literal, Tuple
from indexer.tokenizer import tokenize_terms

SearchMode = Literal["keyword", "phrase"]


def parse_query(query_str: str, mode: str = "keyword") -> Tuple[SearchMode, List[str]]:
    """
    Parses and normalizes search query using identical tokenizer.
    
    Args:
        query_str: Raw input query from user or API client.
        mode: Requested search mode ("keyword" or "phrase").
        
    Returns:
        (normalized_mode, terms_list)
    """
    clean_mode: SearchMode = "phrase" if mode.lower().strip() == "phrase" else "keyword"
    terms = tokenize_terms(query_str)
    return clean_mode, terms
