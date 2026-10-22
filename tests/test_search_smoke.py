"""
Smoke test verifying real keyword and exact phrase queries against the built index.
"""
from backend.index_reader import IndexReader
from backend.bm25 import BM25Scorer
from backend.phrase import PhraseMatcher
from backend.snippets import generate_snippet


def test_keyword_search():
    reader = IndexReader("data/index")
    scorer = BM25Scorer(reader)
    
    # Query: "python"
    results = scorer.score_keyword_query(["python"], top_k=5)
    assert len(results) > 0
    top_doc_id, score = results[0]
    title, _, _, _ = reader.get_doc_metadata(top_doc_id)
    assert score > 0
    assert len(title) > 0
    
    # Verify snippet generation
    _, text, _ = reader.get_article_text(top_doc_id)
    snippet = generate_snippet(text, ["python"])
    assert "<b>" in snippet


def test_phrase_search():
    reader = IndexReader("data/index")
    matcher = PhraseMatcher(reader)
    
    # Phrase: "solar system"
    results = matcher.search_phrase(["solar", "system"], top_k=5)
    assert len(results) > 0
    for doc_id, score in results:
        title, text, _ = reader.get_article_text(doc_id)
        assert score > 0
        assert "solar system" in text.lower()


def test_nonexistent_phrase():
    reader = IndexReader("data/index")
    matcher = PhraseMatcher(reader)
    
    # Completely made-up juxtaposition that won't appear as consecutive tokens
    results = matcher.search_phrase(["xylophone", "hyperbolic", "banana", "galaxy"], top_k=5)
    assert len(results) == 0


if __name__ == "__main__":
    test_keyword_search()
    test_phrase_search()
    test_nonexistent_phrase()
    print("[+] All search smoke tests passed!")
