"""
Unit tests for SPIMI block building and block reading.
"""
from pathlib import Path
import tempfile
import pytest
from indexer.spimi import SPIMIBlockBuilder, read_spimi_block
from indexer.tokenizer import tokenize


def test_spimi_block_accumulation_and_flush():
    with tempfile.TemporaryDirectory() as tmp_dir:
        builder = SPIMIBlockBuilder(block_dir=tmp_dir, max_postings_per_block=10)
        
        doc0 = "The quick brown fox"
        doc1 = "The lazy dog"
        doc2 = "Quick fox jumps over the lazy brown dog"
        
        builder.add_document(0, tokenize(doc0))
        builder.add_document(1, tokenize(doc1))
        builder.add_document(2, tokenize(doc2))
        
        block_paths = builder.finalize()
        assert len(block_paths) >= 1
        
        # Read back blocks and verify
        all_terms_in_block = []
        for path in block_paths:
            for term, docs in read_spimi_block(path):
                all_terms_in_block.append(term)
                # Verify docs are sorted by doc_id
                doc_ids = [d[0] for d in docs]
                assert doc_ids == sorted(doc_ids)
                
                # Check specific terms
                if term == "the":
                    # 'the' appears in doc 0, 1, and 2
                    assert set(doc_ids).issubset({0, 1, 2})
                    for doc_id, pos_list in docs:
                        assert len(pos_list) > 0
                        assert all(isinstance(p, int) for p in pos_list)

        assert "quick" in all_terms_in_block
        assert "fox" in all_terms_in_block
