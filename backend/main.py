"""
WikiSearch Search Engine HTTP Backend.
Serves RESTful endpoints for search, full article retrieval, and system metrics.
"""
import argparse
from contextlib import asynccontextmanager
from pathlib import Path
import time
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.bm25 import BM25Scorer
from backend.index_reader import IndexReader
from backend.phrase import PhraseMatcher
from backend.query import parse_query
from backend.snippets import generate_snippet

# Global index resources
reader: Optional[IndexReader] = None
bm25_scorer: Optional[BM25Scorer] = None
phrase_matcher: Optional[PhraseMatcher] = None
index_path_global: Path = Path("data/index")


def init_engine(index_dir: Path):
    global reader, bm25_scorer, phrase_matcher
    print(f"[*] Initializing search engine with index at: {index_dir.resolve()}...")
    reader = IndexReader(index_dir)
    bm25_scorer = BM25Scorer(reader, k1=1.2, b=0.75, title_boost=2.0)
    phrase_matcher = PhraseMatcher(reader, k1=1.2, b=0.75, title_boost=3.0)
    print(f"[+] Engine ready! {reader.num_docs:,} documents, {reader.num_unique_terms:,} unique terms loaded.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_engine(index_path_global)
    yield
    if reader:
        reader.close()


app = FastAPI(
    title="WikiSearch Engine API",
    description="Local Wikipedia Search Engine with BM25 ranking and exact-phrase search.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for Android clients, emulator (10.0.2.2), and local browser testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Response Models
class SearchResultItem(BaseModel):
    id: int
    title: str
    score: float
    snippet: str
    rank: int


class SearchResponse(BaseModel):
    query: str
    mode: str
    took_ms: float
    total: int
    results: List[SearchResultItem]


class ArticleResponse(BaseModel):
    id: int
    title: str
    text: str
    length: int
    attribution: str = "Content from Simple English Wikipedia, licensed under CC BY-SA 4.0"


class StatsResponse(BaseModel):
    num_docs: int
    num_unique_terms: int
    avg_doc_length: float
    total_tokens: int
    index_size_bytes: int
    index_size_human: str
    build_time_secs: float
    postings_compressed: bool
    # Android client contract aliases
    doc_count: int
    build_time_s: float
    index_size_mb: float
    corpus_size_mb: float
    ratio: float
    compressed: bool


def format_bytes(b: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if b < 1024.0:
            return f"{b:.2f} {unit}"
        b /= 1024.0
    return f"{b:.2f} TB"


@app.get("/search", response_model=SearchResponse)
def search(
    q: str = Query(..., description="Query text string"),
    mode: str = Query("keyword", description="Search mode: 'keyword' or 'phrase'"),
    k: int = Query(10, ge=1, le=100, description="Max results to return"),
):
    if not reader or not bm25_scorer or not phrase_matcher:
        raise HTTPException(status_code=503, detail="Search engine not initialized.")

    start_time = time.perf_counter()
    search_mode, terms = parse_query(q, mode)

    if not terms:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return SearchResponse(
            query=q,
            mode=search_mode,
            took_ms=round(elapsed_ms, 2),
            total=0,
            results=[],
        )

    # Dispatch to appropriate scorer
    if search_mode == "phrase":
        ranked_docs = phrase_matcher.search_phrase(terms, top_k=k)
    else:
        ranked_docs = bm25_scorer.score_keyword_query(terms, top_k=k)

    total_matches = len(ranked_docs)

    # Generate snippets for top results
    results = []
    for rank, (doc_id, score) in enumerate(ranked_docs, start=1):
        title, text, _ = reader.get_article_text(doc_id)
        snippet = generate_snippet(text, terms, window_token_radius=15, max_chars=220)
        results.append(
            SearchResultItem(
                id=doc_id,
                title=title,
                score=score,
                snippet=snippet,
                rank=rank,
            )
        )

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    return SearchResponse(
        query=q,
        mode=search_mode,
        took_ms=round(elapsed_ms, 2),
        total=total_matches,
        results=results,
    )


@app.get("/article/{doc_id}", response_model=ArticleResponse)
def get_article(doc_id: int):
    if not reader:
        raise HTTPException(status_code=503, detail="Search engine not initialized.")
    if doc_id < 0 or doc_id >= reader.num_docs:
        raise HTTPException(status_code=404, detail=f"Article {doc_id} not found.")

    title, text, length = reader.get_article_text(doc_id)
    return ArticleResponse(
        id=doc_id,
        title=title,
        text=text,
        length=length,
    )


@app.get("/stats", response_model=StatsResponse)
def get_stats():
    if not reader:
        raise HTTPException(status_code=503, detail="Search engine not initialized.")

    # Calculate index directory size
    total_bytes = sum(f.stat().st_size for f in reader.index_dir.glob("*.bin"))
    meta_file = reader.index_dir / "meta.json"
    if meta_file.exists():
        total_bytes += meta_file.stat().st_size

    index_mb = round(total_bytes / (1024 * 1024), 2)
    corpus_mb = 523.67
    size_ratio = round(index_mb / corpus_mb, 2)

    return StatsResponse(
        num_docs=reader.num_docs,
        num_unique_terms=reader.num_unique_terms,
        avg_doc_length=reader.avg_doc_length,
        total_tokens=reader.total_tokens,
        index_size_bytes=total_bytes,
        index_size_human=format_bytes(total_bytes),
        build_time_secs=reader.meta.get("build_time_secs", 0.0),
        postings_compressed=reader.meta.get("postings_compressed", False),
        doc_count=reader.num_docs,
        build_time_s=reader.meta.get("build_time_secs", 0.0),
        index_size_mb=index_mb,
        corpus_size_mb=corpus_mb,
        ratio=size_ratio,
        compressed=reader.meta.get("postings_compressed", False),
    )


if __name__ == "__main__":
    import uvicorn
    parser = argparse.ArgumentParser(description="WikiSearch Backend Server")
    parser.add_argument("--index-dir", default="data/index", help="Index directory")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface (0.0.0.0 allows LAN & emulator access)")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    args = parser.parse_args()

    index_path_global = Path(args.index_dir)
    uvicorn.run("backend.main:app", host=args.host, port=args.port, reload=False)
