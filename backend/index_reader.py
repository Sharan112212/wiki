"""
Memory-mapped Index Reader for WikiSearch.
Provides zero-copy, zero-latency access to binary index files:
- meta.json: corpus statistics
- lexicon_index.bin + lexicon.bin: O(1) hash map term lookups
- postings.bin: mmap posting list slices
- positions.bin: mmap token positions
- docs.bin: O(1) fixed-width document records
- titles.bin: mmap title slices
- textstore.bin: on-demand zstd decompression
"""
import json
import mmap
from pathlib import Path
import struct
from typing import Dict, List, Optional, Set, Tuple, Union
import zstandard as zstd

from indexer.writer import fnv1a_64


class IndexReader:
    def __init__(self, index_dir: Union[str, Path]):
        self.index_dir = Path(index_dir)
        
        # 1. Load meta.json
        meta_path = self.index_dir / "meta.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"Missing meta.json in {self.index_dir}")
        with open(meta_path, "r", encoding="utf-8") as f:
            self.meta = json.load(f)
            
        self.num_docs: int = self.meta["num_docs"]
        self.num_unique_terms: int = self.meta["num_unique_terms"]
        self.avg_doc_length: float = self.meta["avg_doc_length"]
        self.total_tokens: int = self.meta["total_tokens"]
        
        # 2. Open and memory-map all binary files
        self._open_files = []
        self._mmaps = []
        
        self.f_lexicon, self.m_lexicon = self._mmap_file("lexicon.bin")
        self.f_lex_idx, self.m_lex_idx = self._mmap_file("lexicon_index.bin")
        self.f_postings, self.m_postings = self._mmap_file("postings.bin")
        self.f_positions, self.m_positions = self._mmap_file("positions.bin")
        self.f_docs, self.m_docs = self._mmap_file("docs.bin")
        self.f_titles, self.m_titles = self._mmap_file("titles.bin")
        self.f_textstore, self.m_textstore = self._mmap_file("textstore.bin")
        
        # 3. Read lexicon hash index capacity
        # Header: magic b'WLXI' (4B), version u32 (4B), capacity u64 (8B)
        magic, ver, self.hash_capacity = struct.unpack("<4sIQ", self.m_lex_idx[:16])
        if magic != b"WLXI":
            raise ValueError(f"Invalid lexicon index header: {magic}")
            
        # 4. Zstd decompressor
        self.dctx = zstd.ZstdDecompressor()

    def _mmap_file(self, filename: str) -> Tuple[object, mmap.mmap]:
        path = self.index_dir / filename
        f = open(path, "rb")
        size = path.stat().st_size
        m = mmap.mmap(f.fileno(), length=0, access=mmap.ACCESS_READ)
        self._open_files.append(f)
        self._mmaps.append(m)
        return f, m

    def lookup_term(self, term: str) -> Optional[Tuple[int, int, int, int, int]]:
        """
        O(1) hash lookup for a term.
        Returns:
            (doc_freq, postings_offset, postings_byte_len, positions_offset, positions_byte_len)
            or None if term does not exist.
        """
        term_bytes = term.encode("utf-8")
        h = fnv1a_64(term)
        slot = h % self.hash_capacity
        
        # Each slot in lexicon_index.bin is 16 bytes: hash_key (u64 LE), lexicon_offset (u64 LE)
        # Table starts at byte offset 16
        m_idx = self.m_lex_idx
        m_lex = self.m_lexicon
        cap = self.hash_capacity
        
        while True:
            offset = 16 + slot * 16
            slot_h, lex_off = struct.unpack_from("<QQ", m_idx, offset)
            if slot_h == 0:
                # Empty slot => term not in index
                return None
            if slot_h == h:
                # Hash match: verify actual term string in lexicon.bin to handle any collision
                term_len = struct.unpack_from("<H", m_lex, lex_off)[0]
                stored_term_bytes = m_lex[lex_off + 2 : lex_off + 2 + term_len]
                if stored_term_bytes == term_bytes:
                    # Match confirmed! Read entry data
                    # Layout: df (u32), post_off (u64), post_len (u32), pos_off (u64), pos_len (u32)
                    data_off = lex_off + 2 + term_len
                    df, post_off, post_len, pos_off, pos_len = struct.unpack_from("<IQIQI", m_lex, data_off)
                    return df, post_off, post_len, pos_off, pos_len
                    
            slot = (slot + 1) % cap

    def get_postings(self, postings_offset: int, doc_freq: int) -> List[Tuple[int, int]]:
        """
        Reads posting list for a term directly from postings.bin mmap slice.
        Returns list of (doc_id, term_freq).
        """
        # Each posting is 6 bytes: doc_id (u32 LE, 4B) + term_freq (u16 LE, 2B)
        data = self.m_postings[postings_offset : postings_offset + doc_freq * 6]
        postings = []
        for i in range(doc_freq):
            doc_id, tf = struct.unpack_from("<IH", data, i * 6)
            postings.append((doc_id, tf))
        return postings

    def get_positions(self, positions_offset: int, doc_freq: int) -> Dict[int, List[int]]:
        """
        Reads token positions for all documents in a term's posting list.
        Returns dict: { doc_id_index: [pos1, pos2, ...] }
        """
        curr = positions_offset
        m_pos = self.m_positions
        doc_positions = {}
        
        for doc_idx in range(doc_freq):
            num_pos = struct.unpack_from("<H", m_pos, curr)[0]
            curr += 2
            if num_pos > 0:
                pos_list = list(struct.unpack_from(f"<{num_pos}I", m_pos, curr))
                curr += 4 * num_pos
            else:
                pos_list = []
            doc_positions[doc_idx] = pos_list
            
        return doc_positions

    def get_positions_for_indices(
        self,
        positions_offset: int,
        doc_freq: int,
        needed_indices: Set[int],
    ) -> Dict[int, List[int]]:
        """
        Optimized reader: skips unpacking positions for non-candidate document indices.
        Reduces deserialization overhead from O(df) to O(|needed_indices|).
        """
        curr = positions_offset
        m_pos = self.m_positions
        doc_positions = {}
        remaining = len(needed_indices)
        
        for doc_idx in range(doc_freq):
            num_pos = struct.unpack_from("<H", m_pos, curr)[0]
            curr += 2
            if doc_idx in needed_indices:
                if num_pos > 0:
                    pos_list = list(struct.unpack_from(f"<{num_pos}I", m_pos, curr))
                else:
                    pos_list = []
                doc_positions[doc_idx] = pos_list
                remaining -= 1
                if remaining == 0:
                    break
            curr += 4 * num_pos
            
        return doc_positions

    def get_doc_metadata(self, doc_id: int) -> Tuple[str, int, int, int]:
        """
        O(1) lookup of document record in docs.bin.
        Returns:
            (title, doc_length, text_offset, text_length)
        """
        if doc_id < 0 or doc_id >= self.num_docs:
            raise IndexError(f"doc_id {doc_id} out of range [0, {self.num_docs})")
            
        record_offset = 12 + doc_id * 26
        # Layout: title_offset (u64), title_length (u16), doc_length (u32), text_offset (u64), text_length (u32)
        title_off, title_len, doc_len, text_off, text_len = struct.unpack_from(
            "<QHIQI", self.m_docs, record_offset
        )
        
        title_bytes = self.m_titles[title_off : title_off + title_len]
        title = title_bytes.decode("utf-8", errors="replace")
        return title, doc_len, text_off, text_len

    def get_doc_length(self, doc_id: int) -> int:
        """Fast lookup of just doc_length (for BM25 denominator)."""
        offset = 12 + doc_id * 26 + 10  # skip title_offset (8B) and title_len (2B)
        return struct.unpack_from("<I", self.m_docs, offset)[0]

    def get_article_text(self, doc_id: int) -> Tuple[str, str, int]:
        """
        Retrieves full decompressed article text and title.
        Returns:
            (title, text, doc_length)
        """
        title, doc_len, text_off, text_len = self.get_doc_metadata(doc_id)
        compressed_bytes = self.m_textstore[text_off : text_off + text_len]
        text = self.dctx.decompress(compressed_bytes).decode("utf-8", errors="replace")
        return title, text, doc_len

    def close(self):
        for m in self._mmaps:
            m.close()
        for f in self._open_files:
            f.close()
