"""
Full Index Build Pipeline for WikiSearch.

Orchestrates:
1. Document Ingestion: Streaming read of SimpleWiki Parquet dataset.
2. DocStore Generation: docs.bin, titles.bin, zstd-compressed textstore.bin.
3. SPIMI Inverted Indexing: Bounded-memory block generation with token positions.
4. External K-Way Merge: Priority-queue merge of block streams into final postings.bin and positions.bin.
5. Lexicon & Hash Index: lexicon.bin and lexicon_index.bin for O(1) term resolution.
6. Metadata Generation: meta.json with corpus invariants and build statistics.
"""
import argparse
from pathlib import Path
import shutil
import sys
import time
from typing import Optional

from indexer.reader_parquet import count_documents, read_documents
from indexer.spimi import SPIMIBlockBuilder
from indexer.merger import merge_spimi_blocks
from indexer.tokenizer import tokenize
from indexer.writer import DocStoreWriter, InvertedIndexWriter, write_meta_json


def format_bytes(num_bytes: int) -> str:
    """Formats raw bytes into human-readable string (KB, MB, GB)."""
    for unit in ["B", "KB", "MB", "GB"]:
        if num_bytes < 1024.0:
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.2f} TB"


def build_index(
    data_dir: str = "data/raw/simplewiki",
    output_dir: str = "data/index",
    block_dir: str = "data/blocks",
    max_postings_per_block: int = 1_500_000,
    max_docs: Optional[int] = None,
    keep_blocks: bool = False,
) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    block_path = Path(block_dir)
    block_path.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(" " * 20 + "WIKISEARCH INDEX BUILDER")
    print("=" * 70)
    print(f"[*] Input Data Directory   : {data_dir}")
    print(f"[*] Output Index Directory : {output_path.resolve()}")
    print(f"[*] SPIMI Block Directory  : {block_path.resolve()}")
    print(f"[*] Postings per Block     : {max_postings_per_block:,}")
    if max_docs:
        print(f"[*] Max Documents Limit    : {max_docs:,}")
    print("-" * 70)

    start_total = time.time()

    # Phase 1: Ingestion, DocStore creation, and SPIMI block building
    print("[Phase 1/3] Ingestion & SPIMI Block Building...")
    t0 = time.time()
    
    doc_store = DocStoreWriter(output_path)
    spimi_builder = SPIMIBlockBuilder(
        block_dir=block_path,
        max_postings_per_block=max_postings_per_block,
    )

    doc_counter = 0
    total_raw_text_bytes = 0

    for doc_id, title, text in read_documents(data_dir, batch_size=2048, max_docs=max_docs):
        # Concatenate title and text so that title terms are indexed at doc start
        full_content = f"{title}\n\n{text}" if title else text
        total_raw_text_bytes += len(full_content.encode("utf-8"))
        
        # Tokenize with exact position tracking
        tokens = tokenize(full_content)
        token_count = len(tokens)
        
        # Write to document store
        doc_store.add_document(
            doc_id=doc_id,
            title=title,
            text=full_content,
            token_count=token_count,
        )
        
        # Add tokens to SPIMI in-memory accumulator
        spimi_builder.add_document(doc_id=doc_id, tokens=tokens)
        
        doc_counter += 1
        if doc_counter % 25000 == 0:
            elapsed = time.time() - t0
            rate = doc_counter / elapsed if elapsed > 0 else 0
            print(f"    Indexed {doc_counter:,} documents ({rate:.0f} docs/sec, {spimi_builder.block_count} blocks written)...")

    # Finalize doc store
    num_docs, total_tokens, avg_doc_length = doc_store.finalize()
    
    # Finalize SPIMI blocks
    block_files = spimi_builder.finalize()
    p1_time = time.time() - t0
    print(f"[+] Phase 1 Complete in {p1_time:.2f}s:")
    print(f"    - Documents Processed : {num_docs:,}")
    print(f"    - Total Tokens        : {total_tokens:,}")
    print(f"    - Avg Document Length : {avg_doc_length:.2f} tokens")
    print(f"    - SPIMI Blocks Emitted: {len(block_files)}")

    # Phase 2: K-Way Merge of SPIMI Blocks into Postings and Positions
    print("\n[Phase 2/3] External K-Way Merge of SPIMI Blocks...")
    t1 = time.time()
    index_writer = InvertedIndexWriter(output_path)

    merged_terms = 0
    for term, docs in merge_spimi_blocks(block_files):
        index_writer.add_term_postings(term, docs)
        merged_terms += 1
        if merged_terms % 50000 == 0:
            print(f"    Merged {merged_terms:,} unique terms into postings/positions streams...")

    # Phase 3: Writing Lexicon & Lexicon Hash Table
    print("\n[Phase 3/3] Finalizing Lexicon and Hash Index...")
    num_unique_terms = index_writer.finalize()
    p2_p3_time = time.time() - t1
    print(f"[+] Phase 2 & 3 Complete in {p2_p3_time:.2f}s:")
    print(f"    - Unique Vocabulary Terms: {num_unique_terms:,}")

    total_build_time = time.time() - start_total

    # Write meta.json
    meta_file = write_meta_json(
        index_dir=output_path,
        num_docs=num_docs,
        num_unique_terms=num_unique_terms,
        total_tokens=total_tokens,
        avg_doc_length=avg_doc_length,
        build_time_secs=total_build_time,
    )

    # Clean up temporary blocks unless asked to keep
    if not keep_blocks:
        print("[*] Cleaning up intermediate block files...")
        for b_file in block_files:
            try:
                b_file.unlink()
            except OSError:
                pass
        try:
            block_path.rmdir()
        except OSError:
            pass

    # Calculate index sizes
    print("\n" + "=" * 70)
    print(" " * 22 + "INDEX BUILD SUMMARY")
    print("=" * 70)
    index_files = [
        "meta.json",
        "lexicon.bin",
        "lexicon_index.bin",
        "postings.bin",
        "positions.bin",
        "docs.bin",
        "titles.bin",
        "textstore.bin",
    ]
    total_index_bytes = 0
    for fname in index_files:
        fpath = output_path / fname
        if fpath.exists():
            fsize = fpath.stat().st_size
            total_index_bytes += fsize
            print(f"  {fname:<20} : {format_bytes(fsize):>10} ({fsize:,} bytes)")

    size_ratio = (total_index_bytes / total_raw_text_bytes) if total_raw_text_bytes > 0 else 0.0

    print("-" * 70)
    print(f"  Total Index Size     : {format_bytes(total_index_bytes)}")
    print(f"  Raw Corpus Plaintext : {format_bytes(total_raw_text_bytes)}")
    print(f"  Index-to-Text Ratio  : {size_ratio:.2%}")
    print(f"  Total Wall-Clock Time: {total_build_time:.2f} seconds ({total_build_time/60:.2f} minutes)")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Build WikiSearch Positional Inverted Index.")
    parser.add_argument("--data-dir", default="data/raw/simplewiki", help="Path to raw parquet dataset")
    parser.add_argument("--output-dir", default="data/index", help="Output path for binary index files")
    parser.add_argument("--block-dir", default="data/blocks", help="Temporary path for SPIMI blocks")
    parser.add_argument("--max-postings", type=int, default=1_500_000, help="Max postings per SPIMI block")
    parser.add_argument("--max-docs", type=int, default=None, help="Optional max documents to index (for testing)")
    parser.add_argument("--keep-blocks", action="store_true", help="Retain intermediate SPIMI block files")
    args = parser.parse_args()

    build_index(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        block_dir=args.block_dir,
        max_postings_per_block=args.max_postings,
        max_docs=args.max_docs,
        keep_blocks=args.keep_blocks,
    )


if __name__ == "__main__":
    main()
