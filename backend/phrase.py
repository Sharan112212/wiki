"""
Exact Phrase Matching via Positional Intersection.

For a phrase query [w0, w1, ..., w_{m-1}]:
1. Checks that all words exist in vocabulary.
2. Intersects posting lists (starting from lowest document frequency).
3. For candidate documents, verifies consecutive positions:
   pos(w1) == pos(w0) + 1, pos(w2) == pos(w0) + 2, ...
   using binary search over position arrays.
4. Computes BM25 phrase score with top-K min-heap selection.
"""
from bisect import bisect_left
import heapq
import math
from typing import Dict, List, Optional, Tuple

from backend.index_reader import IndexReader
from backend.bm25 import compute_robertson_idf


def binary_search_contains(arr: List[int], target: int) -> bool:
    """Checks if target integer exists in sorted array using binary search."""
    idx = bisect_left(arr, target)
    return idx < len(arr) and arr[idx] == target


class PhraseMatcher:
    def __init__(
        self,
        reader: IndexReader,
        k1: float = 1.2,
        b: float = 0.75,
        title_boost: float = 3.0,
    ):
        self.reader = reader
        self.k1 = k1
        self.b = b
        self.title_boost = title_boost
        
        self.num_docs = reader.num_docs
        self.avgdl = reader.avg_doc_length

    def search_phrase(
        self,
        phrase_terms: List[str],
        top_k: int = 10,
    ) -> List[Tuple[int, float]]:
        """
        Executes exact phrase search over consecutive query terms.
        
        Returns:
            List of (doc_id, score) sorted descending by relevance score.
        """
        if not phrase_terms:
            return []
            
        m = len(phrase_terms)
        
        # 1. Lookup all terms in lexicon
        term_metas = []
        for term in phrase_terms:
            info = self.reader.lookup_term(term)
            if info is None or info[0] == 0:
                # Any missing term means 0 exact phrase matches
                return []
            term_metas.append((term, info))
            
        # 2. Retrieve posting lists and find intersection of doc_ids
        # Order by ascending df for fast set intersection
        postings_per_term: Dict[str, Dict[int, int]] = {}  # term -> {doc_id: doc_idx_in_posting}
        idfs: List[float] = []
        
        for term, info in term_metas:
            df, post_off, post_len, _, _ = info
            idf = compute_robertson_idf(df, self.num_docs)
            idfs.append(idf)
            post_list = self.reader.get_postings(post_off, df)
            postings_per_term[term] = {doc_id: idx for idx, (doc_id, tf) in enumerate(post_list)}
            
        # Candidate doc_ids must contain all phrase terms
        # Sort terms by smallest posting list
        sorted_terms_by_df = sorted(phrase_terms, key=lambda t: len(postings_per_term[t]))
        candidate_docs = set(postings_per_term[sorted_terms_by_df[0]].keys())
        
        for t in sorted_terms_by_df[1:]:
            candidate_docs.intersection_update(postings_per_term[t].keys())
            if not candidate_docs:
                return []
                
        # 3. Positional Intersection on Candidate Documents
        # Pre-load positions only for the candidate document indices
        positions_per_term: Dict[str, Dict[int, List[int]]] = {}
        for term, info in term_metas:
            df, _, _, pos_off, _ = info
            needed_indices = {postings_per_term[term][doc_id] for doc_id in candidate_docs}
            positions_per_term[term] = self.reader.get_positions_for_indices(pos_off, df, needed_indices)
            
        first_term = phrase_terms[0]
        phrase_matches: Dict[int, int] = {}  # doc_id -> phrase_tf
        
        for doc_id in candidate_docs:
            # Get positions of first term in doc
            first_term_doc_idx = postings_per_term[first_term][doc_id]
            first_positions = positions_per_term[first_term][first_term_doc_idx]
            
            # Position arrays for subsequent terms
            subsequent_pos_arrays = [
                positions_per_term[phrase_terms[offset]][postings_per_term[phrase_terms[offset]][doc_id]]
                for offset in range(1, m)
            ]
            
            phrase_tf = 0
            for start_pos in first_positions:
                match = True
                for offset, pos_arr in enumerate(subsequent_pos_arrays, start=1):
                    target_pos = start_pos + offset
                    if not binary_search_contains(pos_arr, target_pos):
                        match = False
                        break
                if match:
                    phrase_tf += 1
                    
            if phrase_tf > 0:
                phrase_matches[doc_id] = phrase_tf
                
        if not phrase_matches:
            return []
            
        # 4. BM25 Scoring on Phrase Matches
        # Aggregated IDF of phrase
        phrase_idf = sum(idfs)
        k1 = self.k1
        b = self.b
        avgdl = self.avgdl
        
        scores: Dict[int, float] = {}
        exact_phrase_str = " ".join(phrase_terms).lower()
        
        for doc_id, phrase_tf in phrase_matches.items():
            doc_len = self.reader.get_doc_length(doc_id)
            len_norm = 1.0 - b + b * (doc_len / avgdl) if avgdl > 0 else 1.0
            score = phrase_idf * (phrase_tf * (k1 + 1.0)) / (phrase_tf + k1 * len_norm)
            
            # Check title for exact phrase bonus
            title, _, _, _ = self.reader.get_doc_metadata(doc_id)
            if exact_phrase_str in title.lower():
                score += self.title_boost * phrase_idf
                
            scores[doc_id] = score
            
        # Top-K bounded min-heap
        heap: List[Tuple[float, int]] = []
        for doc_id, score in scores.items():
            if len(heap) < top_k:
                heapq.heappush(heap, (score, doc_id))
            else:
                if score > heap[0][0]:
                    heapq.heappushpop(heap, (score, doc_id))
                    
        ranked = sorted(heap, key=lambda x: x[0], reverse=True)
        return [(doc_id, round(score, 4)) for score, doc_id in ranked]
