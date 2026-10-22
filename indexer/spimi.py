"""
SPIMI (Single-Pass In-Memory Indexing) Block Builder.

Accumulates (term, doc_id, position) postings in RAM and flushes them to disk
as sorted block files when memory/postings threshold is reached.
Never loads the whole corpus into RAM, fulfilling streaming indexing requirements.
"""
from pathlib import Path
import struct
from typing import Dict, Generator, List, Optional, Tuple, Union


class SPIMIBlockBuilder:
    """
    SPIMI block accumulator and flusher.
    
    Structure of in-memory postings:
        Dict[term, List[ [doc_id, List[int]] ]]
    """
    
    def __init__(
        self,
        block_dir: Union[str, Path] = "data/blocks",
        max_postings_per_block: int = 1_000_000,
    ):
        self.block_dir = Path(block_dir)
        self.block_dir.mkdir(parents=True, exist_ok=True)
        self.max_postings_per_block = max_postings_per_block
        
        # In-memory dictionary: term -> list of [doc_id, positions_list]
        self.postings: Dict[str, List[List[Union[int, List[int]]]]] = {}
        self.posting_count = 0
        self.block_count = 0
        self.block_paths: List[Path] = []
        
    def add_document(self, doc_id: int, tokens: List[Tuple[str, int]]) -> None:
        """
        Adds tokens from a single document into the in-memory block.
        
        Args:
            doc_id: Unique integer identifier for document.
            tokens: List of (token_term, position) tuples.
        """
        if not tokens:
            return
            
        postings = self.postings
        for term, pos in tokens:
            doc_list = postings.get(term)
            if doc_list is None:
                postings[term] = [[doc_id, [pos]]]
            else:
                last_doc_entry = doc_list[-1]
                if last_doc_entry[0] == doc_id:
                    last_doc_entry[1].append(pos)
                else:
                    doc_list.append([doc_id, [pos]])
            
            self.posting_count += 1
            
        if self.posting_count >= self.max_postings_per_block:
            self.flush_block()
            
    def flush_block(self) -> Optional[Path]:
        """
        Sorts the terms in the in-memory dictionary and writes a binary block file.
        Clears the in-memory dictionary to free RAM.
        
        Binary layout of block file:
            Header:
                magic: b'SBLK' (4 bytes)
                version: u16 (2 bytes, = 1)
                num_terms: u32 (4 bytes)
            For each term:
                term_len: u16 (2 bytes)
                term_bytes: UTF-8 string bytes
                doc_count: u32 (4 bytes)
                For each doc:
                    doc_id: u32 (4 bytes)
                    num_positions: u32 (4 bytes)
                    positions: num_positions * u32 (4 bytes each)
        """
        if not self.postings:
            return None
            
        block_filename = self.block_dir / f"block_{self.block_count:04d}.spimi"
        sorted_terms = sorted(self.postings.keys())
        num_terms = len(sorted_terms)
        
        with open(block_filename, "wb") as f:
            # Header
            f.write(b"SBLK")
            f.write(struct.pack("<HI", 1, num_terms))
            
            for term in sorted_terms:
                term_bytes = term.encode("utf-8")
                doc_list = self.postings[term]
                doc_count = len(doc_list)
                
                # Write term info
                f.write(struct.pack("<HI", len(term_bytes), doc_count))
                f.write(term_bytes)
                
                # Write document postings
                for doc_id, positions in doc_list:
                    num_pos = len(positions)
                    f.write(struct.pack("<II", doc_id, num_pos))
                    if num_pos > 0:
                        f.write(struct.pack(f"<{num_pos}I", *positions))
                        
        self.block_paths.append(block_filename)
        self.block_count += 1
        self.postings.clear()
        self.posting_count = 0
        return block_filename

    def finalize(self) -> List[Path]:
        """Flushes any remaining in-memory postings and returns all block file paths."""
        if self.postings:
            self.flush_block()
        return self.block_paths


def read_spimi_block(
    block_path: Union[str, Path]
) -> Generator[Tuple[str, List[Tuple[int, List[int]]]], None, None]:
    """
    Sequentially reads terms and postings from a SPIMI block file.
    
    Yields:
        (term, [(doc_id, [pos1, pos2, ...]), ...]) tuples.
    """
    path = Path(block_path)
    with open(path, "rb") as f:
        magic = f.read(4)
        if magic != b"SBLK":
            raise ValueError(f"Invalid SPIMI block magic header in {path}: {magic}")
            
        version, num_terms = struct.unpack("<HI", f.read(6))
        
        for _ in range(num_terms):
            term_len, doc_count = struct.unpack("<HI", f.read(6))
            term = f.read(term_len).decode("utf-8")
            
            docs: List[Tuple[int, List[int]]] = []
            for _ in range(doc_count):
                doc_id, num_pos = struct.unpack("<II", f.read(8))
                if num_pos > 0:
                    positions = list(struct.unpack(f"<{num_pos}I", f.read(4 * num_pos)))
                else:
                    positions = []
                docs.append((doc_id, positions))
                
            yield term, docs
