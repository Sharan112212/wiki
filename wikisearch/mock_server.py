#!/usr/bin/env python3
"""
WikiSearch Mock Backend Server (FastAPI)
Implements the exact API contract for local testing before the laptop backend is connected.

Run with:
    pip install fastapi uvicorn
    python3 mock_server.py
or
    uvicorn mock_server:app --host 0.0.0.0 --port 8000 --reload
"""

import time
import re
from typing import Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="WikiSearch Mock Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock Articles Database
MOCK_ARTICLES = {
    12: {
        "id": 12,
        "title": "Solar eclipse",
        "text": (
            "A solar eclipse occurs when the Moon passes between Earth and the Sun, "
            "thereby totally or partly obscuring the image of the Sun for a viewer on Earth. "
            "A total solar eclipse occurs when the Moon's apparent diameter is larger than the Sun's, "
            "blocking all direct sunlight, turning day into darkness. Total eclipses occur in a narrow path "
            "across Earth's surface, with the partial solar eclipse visible over a surrounding region thousands "
            "of kilometres wide. During a total solar eclipse, the solar corona is clearly visible to the naked eye.\n\n"
            "Eclipses have fascinated humanity for millennia. Ancient astronomers learned to predict eclipses by observing "
            "the Saros cycle of orbital alignments."
        )
    },
    42: {
        "id": 42,
        "title": "Albert Einstein",
        "text": (
            "Albert Einstein (14 March 1879 – 18 April 1955) was a German-born theoretical physicist who is widely "
            "held to be one of the greatest and most influential scientists of all time. Best known for developing "
            "the theory of relativity, Einstein also made important contributions to quantum mechanics, and was "
            "thus a central figure in the revolutionary reshaping of the scientific understanding of nature that "
            "modern physics accomplished in the first decades of the twentieth century.\n\n"
            "His mass–energy equivalence formula E = mc², which arises from relativity theory, has been dubbed 'the world's "
            "most famous equation'. He received the 1921 Nobel Prize in Physics for his services to theoretical physics, "
            "and especially for his discovery of the law of the photoelectric effect."
        )
    },
    108: {
        "id": 108,
        "title": "Quantum computing",
        "text": (
            "Quantum computing is a rapidly-emerging technology that harnesses the laws of quantum mechanics to solve "
            "problems too complex for classical computers. Today, IBM Quantum makes real quantum hardware available to "
            "thousands of developers.\n\n"
            "While classical computers store information in binary bits (0s and 1s), quantum computing utilizes quantum bits "
            "or qubits. Qubits leverage superposition and quantum entanglement to evaluate massive solution spaces simultaneously."
        )
    },
    204: {
        "id": 204,
        "title": "Black hole",
        "text": (
            "A black hole is a region of spacetime where gravity is so strong that nothing — no particles or even "
            "electromagnetic radiation such as light — can escape from it. The theory of general relativity predicts that "
            "a sufficiently compact mass can deform spacetime to form a black hole.\n\n"
            "The boundary of no escape is called the event horizon. Although the event horizon has an enormous effect on "
            "the fate and circumstances of an object crossing it, according to general relativity it has no locally detectable "
            "features."
        )
    },
    512: {
        "id": 512,
        "title": "World War II",
        "text": (
            "World War II or the Second World War was a global conflict that lasted from 1939 to 1945. The vast majority "
            "of the world's countries — including all of the great powers — fought as part of two opposing military alliances: "
            "the Allies and the Axis powers."
        )
    }
}

@app.get("/search")
def search(
    q: str = Query(..., description="Query string"),
    mode: str = Query("keyword", description="Search mode: keyword or phrase"),
    k: int = Query(10, description="Results limit")
):
    start_time = time.time()
    clean_q = q.strip().strip('"').lower()

    if not clean_q:
        return {"took_ms": 1.1, "total": 0, "results": []}

    results = []
    rank_score = 15.5

    for doc_id, doc in MOCK_ARTICLES.items():
        doc_text = doc["text"].lower()
        title_lower = doc["title"].lower()

        is_match = False
        if mode == "phrase":
            is_match = (clean_q in title_lower) or (clean_q in doc_text)
        else:
            query_tokens = [t for t in clean_q.split() if len(t) >= 2]
            is_match = any((token in title_lower or token in doc_text) for token in query_tokens)

        if is_match:
            # Generate snippet with <b> tags
            snippet_text = doc["text"][:180] + "..."
            if clean_q:
                regex = re.compile(re.escape(clean_q), re.IGNORECASE)
                snippet_text = regex.sub(lambda m: f"<b>{m.group(0)}</b>", snippet_text)

            results.append({
                "id": doc["id"],
                "title": doc["title"],
                "score": round(rank_score, 2),
                "snippet": snippet_text
            })
            rank_score -= 2.3

    results = results[:k]
    took_ms = round((time.time() - start_time) * 1000 + 2.5, 2)

    return {
        "took_ms": took_ms,
        "total": len(results),
        "results": results
    }

@app.get("/article/{article_id}")
def get_article(article_id: int):
    if article_id in MOCK_ARTICLES:
        return MOCK_ARTICLES[article_id]
    raise HTTPException(status_code=404, detail=f"Article with ID {article_id} not found in index.")

@app.get("/stats")
def get_stats():
    return {
        "doc_count": 200000,
        "build_time_s": 412.5,
        "index_size_mb": 310.2,
        "corpus_size_mb": 650.0,
        "ratio": 0.48,
        "compressed": True
    }

if __name__ == "__main__":
    print("Starting WikiSearch Mock Backend on http://0.0.0.0:8000 ...")
    uvicorn.run("mock_server:app", host="0.0.0.0", port=8000, reload=True)
