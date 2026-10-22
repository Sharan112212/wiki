"""
Shared tokenizer module for WikiSearch.
Guarantees identical tokenization at index time and query time.
"""
import re
from typing import List, Tuple

# Token pattern: sequences of lowercase alphanumeric characters
TOKEN_RE = re.compile(r"[a-z0-9]+")

def tokenize(text: str) -> List[Tuple[str, int]]:
    """
    Tokenizes input text into a list of (token, position) tuples.
    
    Position is the 0-based token index in the stream.
    Processing:
      1. Converts text to lowercase.
      2. Extracts all contiguous alphanumeric tokens matching [a-z0-9]+.
      3. Assigns sequential integer positions: 0, 1, 2, ...
    
    Args:
        text: The string to tokenize.
        
    Returns:
        List of (token, position) tuples.
    """
    if not text:
        return []
    
    tokens = TOKEN_RE.findall(text.lower())
    return [(token, pos) for pos, token in enumerate(tokens)]


def tokenize_terms(text: str) -> List[str]:
    """
    Tokenizes input text and returns only the list of token strings.
    Useful for queries where positions are not strictly needed or for fast lookups.
    """
    if not text:
        return []
    return TOKEN_RE.findall(text.lower())
