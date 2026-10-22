"""
K-way merge of sorted SPIMI block files.
Merges postings and positions across multiple block runs into a unified term stream
using a priority queue (min-heap), keeping memory footprint bounded by O(K).
"""
import heapq
from pathlib import Path
from typing import Generator, List, Tuple, Union
from indexer.spimi import read_spimi_block


def merge_spimi_blocks(
    block_paths: List[Union[str, Path]]
) -> Generator[Tuple[str, List[Tuple[int, List[int]]]], None, None]:
    """
    K-way merges sorted SPIMI block files into a single sorted term stream.
    
    Args:
        block_paths: List of file paths to .spimi block files.
        
    Yields:
        (term, [(doc_id, [pos1, pos2, ...]), ...]) in ascending lexicographical order.
    """
    if not block_paths:
        return

    # Min-heap elements: (term, block_idx, generator)
    heap = []
    
    for idx, path in enumerate(block_paths):
        gen = read_spimi_block(path)
        try:
            term, docs = next(gen)
            # Store in heap with block_idx as tie-breaker
            heapq.heappush(heap, (term, idx, docs, gen))
        except StopIteration:
            continue
            
    while heap:
        # Pop the smallest term
        current_term, idx, docs, gen = heapq.heappop(heap)
        combined_docs = list(docs)
        
        # Advance the generator that just yielded
        try:
            next_term, next_docs = next(gen)
            heapq.heappush(heap, (next_term, idx, next_docs, gen))
        except StopIteration:
            pass
            
        # Check if other blocks also have the same term
        while heap and heap[0][0] == current_term:
            _, other_idx, other_docs, other_gen = heapq.heappop(heap)
            combined_docs.extend(other_docs)
            try:
                nxt_term, nxt_docs = next(other_gen)
                heapq.heappush(heap, (nxt_term, other_idx, nxt_docs, other_gen))
            except StopIteration:
                pass
                
        # In SPIMI, blocks are partitioned sequentially by document batches,
        # so doc_ids in combined_docs are naturally ordered or need stable sort.
        # Ensure doc_ids are strictly sorted in case of edge interleaving:
        combined_docs.sort(key=lambda d: d[0])
        
        yield current_term, combined_docs
