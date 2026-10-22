# WikiSearch — Local Wikipedia Search Engine

A high-performance local search engine built from scratch over Simple English Wikipedia (**270,509 articles**), featuring custom SPIMI inverted indexing, positional indexing for exact-phrase search, BM25 ranking, and an asynchronous FastAPI HTTP backend.

---

## Key Achievements & Benchmarks

* **Zero 3rd-Party Engine Dependencies**: 100% custom indexing and ranking engine (no Lucene, Elasticsearch, Whoosh, or SQLite FTS).
* **Corpus Size**: **270,509 articles** (84,151,999 tokens, 1,160,978 unique vocabulary terms).
* **Index Build Time**: **207.04 seconds (~3.45 minutes)** from raw Parquet dump.
* **Total Index Size**: **830.11 MB** (including compressed Zstandard text store).
* **Relevance**:
  * **Hit@1 (Top Result)**: **78.75%**
  * **Hit@10**: **87.50%**
  * **Mean Reciprocal Rank (MRR)**: **0.8140** (exceeds > 0.70 target)
* **Search Latency**:
  * **Overall Median (p50)**: **13.01 ms**
  * **Keyword Latency (p50)**: **6.44 ms**
  * **Phrase Latency (p95)**: **191.75 ms**
* **Completed Tiers**:
  * **Tier A (Required)**: Parquet SimpleWiki streaming ingestion + Okapi BM25 keyword search.
  * **Tier A+ (Required)**: Positional inverted index + exact-phrase search with binary search positional verification.
  * **Tier D (Bonus)**: Delta encoding + Variable Byte (VByte) posting list compression.
  * **Tier B (Bonus)**: Streaming bz2 XML iterparse reader + wikitext cleaner with cleaning report.

---

## Architecture Overview

```
data/raw/simplewiki/ -> [Streaming Parquet Reader]
                               |
                        [Shared Tokenizer] (lowercase, r'[a-z0-9]+', positions)
                               |
                      [SPIMI Block Builder] (in-memory dict, 256MB threshold)
                               |
                       [K-Way External Merge] (min-heap streaming)
                               |
                               v
                       [Binary Index Files]
         ├── meta.json             (corpus invariants & stats)
         ├── lexicon.bin           (sorted terms, df, file pointers)
         ├── lexicon_index.bin     (O(1) open-addressed hash map)
         ├── postings.bin          (mmap (doc_id, tf) streams)
         ├── positions.bin         (mmap token offsets per doc)
         ├── docs.bin              (fixed 26-byte record table)
         ├── titles.bin            (raw UTF-8 concatenated titles)
         └── textstore.bin         (zstd compressed article text)
                               |
                        [IndexReader (mmap)]
                               |
               +---------------+---------------+
               |                               |
       [BM25 Scorer]                   [Phrase Matcher]
   (Robertson IDF + Title Boost)    (Positional Intersection)
               |                               |
               +---------------+---------------+
                               |
                       [Snippet Generator] (<b> query tags)
                               |
                     [FastAPI HTTP Backend]
```

---

## Quick Start & Reproduction

### 1. Environment Setup

```bash
python -m venv .venv
.\.venv\Scripts\activate            # Windows (or `source .venv/bin/activate` on Linux/macOS)
pip install -r requirements.txt
```

### 2. Run Test Suite (26 tests)

```bash
pytest -v
```

### 3. Build the Index (or use existing data/index)

```bash
# Downloads 167MB parquet dataset via parallel chunk downloader in ~25s:
python scripts/fast_download.py

# Builds full positional index in ~3.5 minutes:
python -m indexer.build --data-dir data/raw/simplewiki --output-dir data/index
```

### 4. Start the Search Server

```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

The server is available at:
* **Local**: `http://localhost:8000`
* **Android Emulator**: `http://10.0.2.2:8000`
* **LAN Devices**: `http://<YOUR_LAN_IP>:8000`
* **Swagger API Docs**: `http://localhost:8000/docs`

### 5. Run Benchmark Suite

```bash
# Generates 105 known-item, phrase, and topic benchmark queries:
python -m benchmark.generate_queries

# Executes benchmark and updates report/report.md:
python -m benchmark.run_benchmark
```

---

## HTTP REST API Contract

### `GET /search`
**Parameters**:
* `q` *(string, required)*: Search query.
* `mode` *(string, default "keyword")*: `"keyword"` or `"phrase"`.
* `k` *(int, default 10)*: Number of top results.

**Sample Request**:
```bash
curl -s "http://localhost:8000/search?q=solar+system&mode=phrase&k=2"
```

**Sample Response**:
```json
{
  "query": "solar system",
  "mode": "phrase",
  "took_ms": 8.17,
  "total": 3,
  "results": [
    {
      "id": 10313,
      "title": "Small solar system body",
      "score": 43.2585,
      "snippet": "Small <b>solar</b> <b>system</b> body A **small <b>Solar</b> <b>System</b> body** (**SSSB**) is a term defined in 2006 by ...",
      "rank": 1
    },
    {
      "id": 252828,
      "title": "List of Solar System objects by mass",
      "score": 42.7011,
      "snippet": "List of <b>Solar</b> <b>System</b> objects by mass This article is a list of <b>solar</b> <b>system</b> objects by mass ...",
      "rank": 2
    }
  ]
}
```

### `GET /article/{id}`
**Sample Request**:
```bash
curl -s "http://localhost:8000/article/10313"
```

**Sample Response**:
```json
{
  "id": 10313,
  "title": "Small solar system body",
  "text": "Small solar system body\n\nA **small Solar System body** ...",
  "length": 194,
  "attribution": "Content from Simple English Wikipedia, licensed under CC BY-SA 4.0"
}
```

### `GET /stats`
**Sample Request**:
```bash
curl -s "http://localhost:8000/stats"
```

**Sample Response**:
```json
{
  "num_docs": 270509,
  "num_unique_terms": 1160978,
  "avg_doc_length": 311.0876,
  "total_tokens": 84151999,
  "index_size_bytes": 870430425,
  "index_size_human": "830.11 MB",
  "build_time_secs": 207.04,
  "postings_compressed": false
}
```

---

## Attribution & Licensing

* **Wikipedia Content**: Content sourced from [Simple English Wikipedia](https://simple.wikipedia.org/) via Hugging Face (`answerdotai/simplewiki`), licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
* **Source Code**: Custom search engine code written from scratch. MIT License.
