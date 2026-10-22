"""
Unit tests for Tier D posting-list compression (Delta + VByte).
"""
import pytest
from indexer.compressor import (
    vbyte_encode_number,
    vbyte_encode,
    vbyte_decode,
    delta_encode,
    delta_decode,
    compress_postings,
    decompress_postings,
)


def test_vbyte_single_numbers():
    for n in [0, 1, 42, 127, 128, 255, 300, 16383, 16384, 1_000_000]:
        encoded = vbyte_encode_number(n)
        decoded = vbyte_decode(encoded)
        assert decoded == [n]


def test_vbyte_list():
    nums = [0, 1, 5, 128, 256, 1024, 65535, 1000000]
    encoded = vbyte_encode(nums)
    decoded = vbyte_decode(encoded)
    assert decoded == nums


def test_delta_encoding_roundtrip():
    doc_ids = [4, 10, 15, 23, 24, 1000, 1005, 50000]
    deltas = delta_encode(doc_ids)
    assert deltas[0] == 4
    assert deltas[1] == 6
    recovered = delta_decode(deltas)
    assert recovered == doc_ids


def test_compress_postings_roundtrip():
    doc_ids = [10, 25, 30, 105, 200, 350, 10000]
    term_freqs = [1, 3, 2, 5, 1, 4, 2]
    
    compressed = compress_postings(doc_ids, term_freqs)
    
    # Original uncompressed 6-byte entries: 7 * 6 = 42 bytes
    uncompressed_size = len(doc_ids) * 6
    assert len(compressed) < uncompressed_size
    
    recovered_ids, recovered_tfs = decompress_postings(compressed)
    assert recovered_ids == doc_ids
    assert recovered_tfs == term_freqs
