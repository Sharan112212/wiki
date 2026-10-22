"""
Integration tests for the FastAPI HTTP endpoints:
- GET /stats
- GET /search (keyword mode)
- GET /search (phrase mode)
- GET /article/{id}
"""
from fastapi.testclient import TestClient
from backend.main import app, init_engine
from pathlib import Path

# Initialize engine with the real built index
init_engine(Path("data/index"))
client = TestClient(app)


def test_stats_endpoint():
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["num_docs"] == 270509
    assert data["num_unique_terms"] > 1000000
    assert data["total_tokens"] > 80000000
    assert "MB" in data["index_size_human"] or "GB" in data["index_size_human"]
    assert data["postings_compressed"] is False


def test_search_keyword_endpoint():
    response = client.get("/search?q=albert+einstein&mode=keyword&k=5")
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "albert einstein"
    assert data["mode"] == "keyword"
    assert data["took_ms"] >= 0
    assert data["total"] > 0
    assert len(data["results"]) <= 5
    
    # Check top result
    first = data["results"][0]
    assert first["rank"] == 1
    assert first["score"] > 0
    assert "Albert Einstein" in [r["title"] for r in data["results"]]


def test_search_phrase_endpoint():
    response = client.get("/search?q=solar+system&mode=phrase&k=5")
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "solar system"
    assert data["mode"] == "phrase"
    assert data["took_ms"] >= 0
    assert data["total"] > 0
    
    # All results must be valid exact phrases
    for r in data["results"]:
        assert r["score"] > 0
        assert r["snippet"] is not None


def test_article_endpoint():
    # Retrieve article 0
    response = client.get("/article/0")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 0
    assert len(data["title"]) > 0
    assert len(data["text"]) > 0
    assert "CC BY-SA" in data["attribution"]


def test_article_404():
    response = client.get("/article/9999999")
    assert response.status_code == 404
