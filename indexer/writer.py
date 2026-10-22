"""
Binary index writer for WikiSearch.
Implements exact byte layouts specified in docs/ARCHITECTURE.md:
- meta.json
- lexicon.bin
- lexicon_index.bin
- postings.bin
- positions.bin
- docs.bin
- titles.bin
- textstore.bin
"""
from pathlib import Path
import json
import struct
from typing import Dict, Iterator, List, Optional, Tuple, Union
import zstandard as zstd


def fnv1a_64(text: str) -> int:
    """Computes 64-bit FNV-1a hash of a UTF-8 string."""
    hash_val = 0xCBF29CE484222325
    prime = 0x100000001B3
    for byte in text.encode("utf-8"):
        hash_val ^= byte
        hash_val = (hash_val * prime) & 0xFFFFFFFFFFFFFFFF
    # Ensure non-zero (0 is reserved for empty slot)
    return hash_val if hash_val != 0 else 1


def is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    w = 2
    while i * i <= n:
        if n % i == 0:
            return False
        i += w
        w = 6 - w
    return True


def next_prime(n: int) -> int:
    """Finds smallest prime >= n."""
    while not is_prime(n):
        n += 1
    return n


class DocStoreWriter:
    """
    Writes docs.bin (fixed 26-byte records), titles.bin (raw UTF-8),
    and textstore.bin (individually zstd-compressed article texts).
    """
    def __init__(self, index_dir: Union[str, Path]):
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        self.titles_file = open(self.index_dir / "titles.bin", "wb")
        self.textstore_file = open(self.index_dir / "textstore.bin", "wb")
        self.docs_file = open(self.index_dir / "docs.bin", "wb")
        
        # Write docs.bin header: magic b'WDOC' (4B), version u32 (4B), num_docs u32 (4B)
        self.docs_file.write(b"WDOC")
        self.docs_file.write(struct.pack("<II", 1, 0))  # num_docs placeholder
        
        self.cctx = zstd.ZstdCompressor(level=3)
        self.title_offset = 0
        self.text_offset = 0
        self.doc_count = 0
        self.total_tokens = 0

    def add_document(self, doc_id: int, title: str, text: str, token_count: int) -> None:
        """
        Appends a single document record to the storage files.
        """
        # 1. Write title to titles.bin
        title_bytes = title.encode("utf-8")
        title_len = len(title_bytes)
        self.titles_file.write(title_bytes)
        curr_title_offset = self.title_offset
        self.title_offset += title_len
        
        # 2. Compress and write text to textstore.bin
        compressed_text = self.cctx.compress(text.encode("utf-8"))
        compressed_len = len(compressed_text)
        self.textstore_file.write(compressed_text)
        curr_text_offset = self.text_offset
        self.text_offset += compressed_len
        
        # 3. Write 26-byte fixed-width record to docs.bin
        # Layout: title_offset (u64), title_length (u16), doc_length (u32), text_offset (u64), text_length (u32)
        record = struct.pack(
            "<QHIQI",
            curr_title_offset,
            title_len,
            token_count,
            curr_text_offset,
            compressed_len,
        )
        self.docs_file.write(record)
        
        self.doc_count += 1
        self.total_tokens += token_count

    def finalize(self) -> Tuple[int, int, float]:
        """
        Closes files, patches docs.bin header with final num_docs,
        and returns (num_docs, total_tokens, avg_doc_length).
        """
        self.titles_file.close()
        self.textstore_file.close()
        
        # Update docs.bin header with actual doc_count
        self.docs_file.seek(8)
        self.docs_file.write(struct.pack("<I", self.doc_count))
        self.docs_file.close()
        
        avg_doc_length = (self.total_tokens / self.doc_count) if self.doc_count > 0 else 0.0
        return self.doc_count, self.total_tokens, avg_doc_length


class InvertedIndexWriter:
    """
    Writes postings.bin, positions.bin, lexicon.bin, and lexicon_index.bin.
    """
    def __init__(self, index_dir: Union[str, Path]):
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        # Open postings.bin
        self.postings_file = open(self.index_dir / "postings.bin", "wb")
        self.postings_file.write(b"WPOS")
        self.postings_file.write(struct.pack("<I", 1))  # version 1 (uncompressed)
        self.postings_offset = 8
        
        # Open positions.bin
        self.positions_file = open(self.index_dir / "positions.bin", "wb")
        self.positions_file.write(b"WPSN")
        self.positions_file.write(struct.pack("<I", 1))  # version 1
        self.positions_offset = 8
        
        # In-memory lexicon table to be written to lexicon.bin and lexicon_index.bin
        # Entry: (term, doc_freq, postings_offset, postings_byte_len, positions_offset, positions_byte_len)
        self.lexicon_entries: List[Tuple[str, int, int, int, int, int, int]] = []
        self.term_count = 0

    def add_term_postings(
        self,
        term: str,
        docs: List[Tuple[int, List[int]]],
    ) -> None:
        """
        Appends the postings and positions for a single term.
        docs: List of (doc_id, [pos1, pos2, ...])
        """
        doc_freq = len(docs)
        if doc_freq == 0:
            return
            
        term_postings_start = self.postings_offset
        term_positions_start = self.positions_offset
        
        # 1. Write postings.bin: pairs of (doc_id: u32 LE, term_freq: u16 LE)
        # 6 bytes per posting
        postings_bytes = bytearray()
        for doc_id, positions in docs:
            tf = len(positions)
            # Clip tf to u16 max just in case
            tf_u16 = min(tf, 65535)
            postings_bytes.extend(struct.pack("<IH", doc_id, tf_u16))
            
        self.postings_file.write(postings_bytes)
        postings_byte_len = len(postings_bytes)
        self.postings_offset += postings_byte_len
        
        # 2. Write positions.bin: for each doc: num_positions: u16 LE, positions: P * u32 LE
        positions_bytes = bytearray()
        for doc_id, positions in docs:
            p_len = len(positions)
            p_u16 = min(p_len, 65535)
            positions_bytes.extend(struct.pack("<H", p_u16))
            if p_len > 0:
                positions_bytes.extend(struct.pack(f"<{p_len}I", *positions))
                
        self.positions_file.write(positions_bytes)
        positions_byte_len = len(positions_bytes)
        self.positions_offset += positions_byte_len
        
        # Record lexicon entry
        self.lexicon_entries.append((
            term,
            doc_freq,
            term_postings_start,
            postings_byte_len,
            term_positions_start,
            positions_byte_len,
        ))
        self.term_count += 1

    def finalize(self) -> int:
        """
        Closes postings and positions files, writes lexicon.bin and lexicon_index.bin.
        Returns total number of unique terms.
        """
        self.postings_file.close()
        self.positions_file.close()
        
        # Sort lexicon entries lexicographically by term
        self.lexicon_entries.sort(key=lambda x: x[0])
        num_terms = len(self.lexicon_entries)
        
        # 1. Write lexicon.bin
        # Header: magic b'WLEX' (4B), version u32 (4B), num_terms u32 (4B) = 12B
        lexicon_path = self.index_dir / "lexicon.bin"
        term_lexicon_offsets: List[Tuple[str, int]] = []
        
        with open(lexicon_path, "wb") as f_lex:
            f_lex.write(b"WLEX")
            f_lex.write(struct.pack("<II", 1, num_terms))
            curr_lex_offset = 12
            
            for term, df, post_off, post_len, pos_off, pos_len in self.lexicon_entries:
                term_bytes = term.encode("utf-8")
                term_len = len(term_bytes)
                term_lexicon_offsets.append((term, curr_lex_offset))
                
                # Format: term_len (u16), term_bytes (variable), df (u32), post_off (u64), post_len (u32), pos_off (u64), pos_len (u32)
                entry_header = struct.pack("<H", term_len)
                entry_data = struct.pack(
                    "<IQIQI",
                    df,
                    post_off,
                    post_len,
                    pos_off,
                    pos_len,
                )
                
                f_lex.write(entry_header)
                f_lex.write(term_bytes)
                f_lex.write(entry_data)
                
                curr_lex_offset += 2 + term_len + len(entry_data)
                
        # 2. Write lexicon_index.bin (O(1) hash map with open addressing)
        # Prime capacity >= 2 * num_terms
        capacity = next_prime(max(2 * num_terms + 1, 101))
        # Hash table: array of (hash_key: u64 LE, lexicon_offset: u64 LE)
        # Header: magic b'WLXI' (4B), version u32 (4B), capacity u64 (8B) = 16B
        table = [(0, 0)] * capacity
        
        for term, lex_off in term_lexicon_offsets:
            h = fnv1a_64(term)
            slot = h % capacity
            while table[slot][0] != 0:
                slot = (slot + 1) % capacity
            table[slot] = (h, lex_off)
            
        lex_idx_path = self.index_dir / "lexicon_index.bin"
        with open(lex_idx_path, "wb") as f_idx:
            f_idx.write(b"WLXI")
            f_idx.write(struct.pack("<IQ", 1, capacity))
            for h, off in table:
                f_idx.write(struct.pack("<QQ", h, off))
                
        return num_terms


def write_meta_json(
    index_dir: Union[str, Path],
    num_docs: int,
    num_unique_terms: int,
    total_tokens: int,
    avg_doc_length: float,
    build_time_secs: float,
    index_version: int = 1,
) -> Path:
    meta_path = Path(index_dir) / "meta.json"
    meta = {
        "magic": "WMTA",
        "index_version": index_version,
        "num_docs": num_docs,
        "num_unique_terms": num_unique_terms,
        "avg_doc_length": round(avg_doc_length, 4),
        "total_tokens": total_tokens,
        "build_time_secs": round(build_time_secs, 2),
        "postings_compressed": False,
        "compression_algorithm": "none",
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    return meta_path
