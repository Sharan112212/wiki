"""
Okapi BM25 Scorer with Top-K Min-Heap Ranking.

Formula:
  IDF(t) = ln((N - df(t) + 0.5) / (df(t) + 0.5) + 1)
  Score(D, Q) = sum_{t in Q} IDF(t) * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (|D| / avgdl)))

Default parameters:
  k1 = 1.2
  b = 0.75
  title_boost = 2.0
"""
from collections import defaultdict
import heapq
import math
from typing import Dict, List, Optional, Set, Tuple

from backend.index_reader import IndexReader
from indexer.tokenizer import tokenize_terms


def compute_robertson_idf(doc_freq: int, num_docs: int) -> float:
    """
    Computes smoothed Robertson-Spärck Jones IDF:
    IDF(t) = ln((N - df(t) + 0.5) / (df(t) + 0.5) + 1.0)
    Always >= 0.
    """
    numerator = num_docs - doc_freq + 0.5
    denominator = doc_freq + 0.5
    return math.log(numerator / denominator + 1.0)


class BM25Scorer:
    def __init__(
        self,
        reader: IndexReader,
        k1: float = 1.2,
        b: float = 0.75,
        title_boost: float = 2.0,
    ):
        self.reader = reader
        self.k1 = k1
        self.b = b
        self.title_boost = title_boost
        
        self.num_docs = reader.num_docs
        self.avgdl = reader.avg_doc_length

    def score_keyword_query(
        self,
        query_terms: List[str],
        top_k: int = 10,
    ) -> List[Tuple[int, float]]:
        """
        Executes BM25 keyword scoring over query terms.
        
        Returns:
            List of (doc_id, score) sorted descending by score.
        """
        if not query_terms or self.num_docs == 0:
            return []

        # Accumulator: doc_id -> score
        doc_scores: Dict[int, float] = defaultdict(float)
        query_term_set = set(query_terms)

        for term in query_term_set:
            term_info = self.reader.lookup_term(term)
            if term_info is None:
                continue
                
            df, post_off, post_len, _, _ = term_info
            if df == 0:
                continue
                
            idf = compute_robertson_idf(df, self.num_docs)
            postings = self.reader.get_postings(post_off, df)
            
            # Score each doc containing this term
            k1 = self.k1
            b = self.b
            avgdl = self.avgdl
            
            for doc_id, tf in postings:
                doc_len = self.reader.get_doc_length(doc_id)
                len_norm = 1.0 - b + b * (doc_len / avgdl) if avgdl > 0 else 1.0
                term_score = idf * (tf * (k1 + 1.0)) / (tf + k1 * len_norm)
                doc_scores[doc_id] += term_score

        if not doc_scores:
            return []

        # Optional Title Boost: add score bonus if query terms appear in article title
        if self.title_boost > 0:
            query_joined = " ".join(query_terms).lower()
            for doc_id in doc_scores:
                title, _, _, _ = self.reader.get_doc_metadata(doc_id)
                title_terms = tokenize_terms(title)
                title_term_set = set(title_terms)
                matches = query_term_set.intersection(title_term_set)
                if matches:
                    doc_scores[doc_id] += self.title_boost * len(matches)
                # Exact title match bonus
                if " ".join(title_terms) == query_joined:
                    doc_scores[doc_id] += 15.0

        # Top-K bounded min-heap: (score, doc_id)
        heap: List[Tuple[float, int]] = []
        for doc_id, score in doc_scores.items():
            if len(heap) < top_k:
                heapq.heappush(heap, (score, doc_id))
            else:
                if score > heap[0][0]:
                    heapq.heappushpop(heap, (score, doc_id))

        # Sort descending by score
        ranked = sorted(heap, key=lambda x: x[0], reverse=True)
        return [(doc_id, round(score, 4)) for score, doc_id in ranked]
