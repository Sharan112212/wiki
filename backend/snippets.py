"""
Dynamic Snippet Generator with Query Term Highlighting.

Locates optimal sliding window of tokens containing query terms,
wraps matching terms with <b>...</b> HTML tags, and truncates smoothly.
"""
import re
from typing import List, Set
from indexer.tokenizer import TOKEN_RE


def generate_snippet(
    text: str,
    query_terms: List[str],
    window_token_radius: int = 15,
    max_chars: int = 220,
) -> str:
    """
    Generates a highlighted snippet from document text around query term matches.
    """
    if not text:
        return ""
        
    query_set = set(t.lower() for t in query_terms if t)
    if not query_set:
        clean = " ".join(text.split())
        return (clean[:max_chars] + "...") if len(clean) > max_chars else clean

    # Find token spans (start_char, end_char, token_str)
    word_re = re.compile(r"[a-zA-Z0-9]+")
    tokens = []
    for match in word_re.finditer(text):
        token_str = match.group(0).lower()
        tokens.append((match.start(), match.end(), token_str))
        
    if not tokens:
        clean = " ".join(text.split())
        return (clean[:max_chars] + "...") if len(clean) > max_chars else clean

    # Identify matching token indices
    match_indices = [idx for idx, (_, _, t_str) in enumerate(tokens) if t_str in query_set]
    
    if not match_indices:
        # Fallback to start of text
        clean = " ".join(text.split())
        return (clean[:max_chars] + "...") if len(clean) > max_chars else clean

    # Choose central match index (first match or cluster center)
    center_idx = match_indices[0]
    
    start_token_idx = max(0, center_idx - window_token_radius)
    end_token_idx = min(len(tokens) - 1, center_idx + window_token_radius)
    
    start_char = tokens[start_token_idx][0]
    end_char = tokens[end_token_idx][1]
    
    # Expand slightly to sentence/word boundaries
    snippet_raw = text[start_char:end_char].strip()
    
    # Highlight query terms (case-insensitively)
    word_pattern = re.compile(r"[a-zA-Z0-9]+")
    def replace_match(m):
        word = m.group(0)
        if word.lower() in query_set:
            return f"<b>{word}</b>"
        return word

    highlighted = word_pattern.sub(replace_match, snippet_raw)
    # Normalize whitespace inside snippet
    highlighted = re.sub(r"\s+", " ", highlighted).strip()
    
    prefix = "... " if start_token_idx > 0 else ""
    suffix = " ..." if end_token_idx < len(tokens) - 1 else ""
    
    res = f"{prefix}{highlighted}{suffix}"
    if len(res) > max_chars + 30:  # accounting for tags
        res = res[:max_chars] + "..."
    return res
