"""
Unit tests for the shared tokenizer module.
"""
import pytest
from indexer.tokenizer import tokenize, tokenize_terms


def test_basic_tokenization():
    text = "Hello World! This is a TEST."
    tokens = tokenize(text)
    expected = [
        ("hello", 0),
        ("world", 1),
        ("this", 2),
        ("is", 3),
        ("a", 4),
        ("test", 5),
    ]
    assert tokens == expected


def test_alphanumeric_and_numbers():
    text = "Python 3.11 release in 2023 at 100% speed"
    tokens = tokenize(text)
    terms = [t for t, _ in tokens]
    assert terms == ["python", "3", "11", "release", "in", "2023", "at", "100", "speed"]
    positions = [p for _, p in tokens]
    assert positions == list(range(len(terms)))


def test_punctuation_and_symbols():
    text = "c++ / c# & node.js -> (hello-world) [test_case] {foo:bar}"
    tokens = tokenize(text)
    terms = [t for t, _ in tokens]
    assert terms == ["c", "c", "node", "js", "hello", "world", "test", "case", "foo", "bar"]


def test_empty_and_whitespace():
    assert tokenize("") == []
    assert tokenize("   \t\n\r  ") == []
    assert tokenize_terms("") == []
    assert tokenize_terms("   ") == []


def test_token_positions_monotonic():
    text = "one two three four five six seven eight nine ten"
    tokens = tokenize(text)
    assert len(tokens) == 10
    for idx, (term, pos) in enumerate(tokens):
        assert pos == idx


def test_tokenize_terms_matches():
    text = "The Quick Brown Fox Jumps Over 42 Lazy Dogs."
    tokens = tokenize(text)
    terms = tokenize_terms(text)
    assert [t for t, _ in tokens] == terms


def test_exact_phrase_positions():
    phrase = "solar system"
    tokens = tokenize(phrase)
    assert tokens == [("solar", 0), ("system", 1)]
