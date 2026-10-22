# Local Wikipedia Search Engine — Report

---

## 1. Design Overview

*Brief description of the system architecture: indexer, backend, Android app. Mention SPIMI, BM25, positional index.*

[Placeholder: 3-4 sentences detailing:
- The offline indexing pipeline implementing Single-Pass In-Memory Indexing ([`indexer/spimi.py`](file:///d:/wiki/indexer/spimi.py)) and multi-way merging ([`indexer/merger.py`](file:///d:/wiki/indexer/merger.py)) to compile compact binary postings and positional tables.
- The high-throughput FastAPI backend service ([`backend/main.py`](file:///d:/wiki/backend/main.py)) executing zero-copy memory-mapped lookups, Okapi BM25 scoring with top-$k$ min-heaps ([`backend/bm25.py`](file:///d:/wiki/backend/bm25.py)), and positional phrase verification ([`backend/phrase.py`](file:///d:/wiki/backend/phrase.py)).
- The native Android client application ([`android/WikiSearch/`](file:///d:/wiki/android/WikiSearch/)) developed in Kotlin and Jetpack Compose providing instant search result streaming, term highlighting, and full-text reading.]

---

## 2. BM25 Ranking Formula

The ranking engine scores document candidates using the standard Okapi BM25 probabilistic relevance model:

$$score(D, Q) = \sum_{t \in Q} IDF(t) \cdot \frac{f(t, D) \cdot (k_1 + 1)}{f(t, D) + k_1 \cdot \left(1 - b + b \cdot \frac{|D|}{avgdl}\right)}$$

Where:
$$\text{IDF}(t) = \ln \left( \frac{N - df(t) + 0.5}{df(t) + 0.5} + 1 \right)$$

*Parameters & Rationale:*
- $k_1 = 1.2$: Calibrates term frequency saturation limit; setting $k_1 = 1.2$ prevents documents with repetitive keyword stuffing from artificially dominating concise, focused articles.
- $b = 0.75$: Controls document length penalization; setting $b = 0.75$ effectively normalizes score inflation in long Wikipedia articles while preserving proportional credit for broad topic coverage.

---

## 3. Index Build Performance

| Metric | Value |
| :--- | :--- |
| Corpus size (articles) | ___ |
| Total tokens | ___ |
| Unique terms (vocabulary size) | ___ |
| Build time | ___ sec |
| Index size (uncompressed) | ___ MB |
| Index size (compressed, Tier D) | ___ MB |
| Compression ratio | ___ |
| Size ratio (index / raw text) | ___ |

---

## 4. Query Performance

Evaluation results based on 100+ automated test queries ([`benchmark/queries.json`](file:///d:/wiki/benchmark/queries.json)) across three execution iterations:

| Metric | Keyword | Phrase | Target SLO |
| :--- | :--- | :--- | :--- |
| **Hit@10** | ___ | ___ | $> 0.90$ |
| **MRR** | ___ | ___ | $> 0.70$ |
| **p50 latency (ms)** | ___ | ___ | $< 50$ ms |
| **p95 latency (ms)** | ___ | ___ | $< 200$ ms |
| **Cold latency (ms)** | ___ | ___ | Baseline |

---

## 5. Tiers Completed

*List which tiers were completed: A, A+, D, B, C*

- [ ] **Tier A (Core Search Engine)**: End-to-end Simple Wikipedia indexer (Parquet), custom binary formats, BM25 scoring with top-k min-heap, FastAPI server, and Android client.
- [ ] **Tier A+ (Positional Index & Phrase Search)**: Word-offset positional posting index, exact phrase matching algorithm, dynamic snippet generation with `<mark>` term highlighting.
- [ ] **Tier D (Index Compression)**: Posting list delta gap encoding ($d_i - d_{i-1}$) and Variable Byte (VByte) compression/decompression routines ([`indexer/compressor.py`](file:///d:/wiki/indexer/compressor.py)).
- [ ] **Tier B (Wikitext Dump Cleaning)**: Full XML streaming parser (`reader_xml.py`) and regex/grammar-based wikitext sanitization pipeline ([`indexer/cleaner.py`](file:///d:/wiki/indexer/cleaner.py)) with cleaning metrics report.
- [ ] **Tier C (Offline Android Search Engine)**: Standalone on-device search engine implementation operating directly on Android without an external network server.

---

## 6. Limitations & Future Work

- **No Morphological Stemming / Lemmatization**: Queries and documents currently rely on exact token normalization without Porter/Snowball stemming, preventing matches across inflectional variants (e.g., "running" vs. "run").
- **No Query Expansion or Synonyms**: Synonymous terminology (e.g., "automobile" vs. "car") is unlinked without an integrated thesaurus or semantic vector expansion pass.
- **Single-Threaded Index Pipeline**: Inverted index building executes synchronously on a single CPU core; multi-threaded or multiprocess block generation would substantially accelerate build throughput.
- **Static Memory Posting Allocation**: Extremely high-frequency terms require full inverted list scans; integrating WAND (Weak AND) or Block-Max WAND dynamic pruning would accelerate tail latency.
- **Title Boosting**: Article title matches currently share uniform weighting with body text occurrences rather than receiving a dedicated BM25 field boost.

---

## 7. Attribution

Content sourced from Simple English Wikipedia (`answerdotai/simplewiki` on Hugging Face), licensed under Creative Commons Attribution-ShareAlike 4.0 International ([CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)).
