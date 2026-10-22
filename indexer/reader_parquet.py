"""
Streaming Parquet dataset reader for WikiSearch.
Reads parquet files batch-by-batch using pyarrow to ensure low memory footprint.
Yields (doc_id, title, text) tuples.
"""
from pathlib import Path
from typing import Generator, Iterator, List, Optional, Tuple, Union
import pyarrow.parquet as pq


def find_parquet_files(data_dir: Union[str, Path]) -> List[Path]:
    """Finds all parquet files in the given directory recursively."""
    path = Path(data_dir)
    if path.is_file() and path.suffix.lower() == ".parquet":
        return [path]
    files = sorted(path.rglob("*.parquet"))
    return files


def read_documents(
    data_path: Union[str, Path],
    batch_size: int = 2048,
    max_docs: Optional[int] = None,
) -> Generator[Tuple[int, str, str], None, None]:
    """
    Streams documents from parquet file(s) one batch at a time.
    
    Assigns a dense 0-based doc_id (0, 1, ..., N-1) for direct O(1) table indexing.
    
    Args:
        data_path: Path to a parquet file or directory containing parquet files.
        batch_size: Number of rows to read per batch into memory.
        max_docs: Optional limit on total number of documents to stream.
        
    Yields:
        (doc_id, title, text) tuples.
    """
    parquet_files = find_parquet_files(data_path)
    if not parquet_files:
        raise FileNotFoundError(f"No parquet files found in: {data_path}")

    current_doc_id = 0

    for file_path in parquet_files:
        try:
            parquet_file = pq.ParquetFile(str(file_path))
        except Exception as e:
            print(f"[!] Warning: Could not open {file_path}: {e}")
            continue

        schema = parquet_file.schema.names
        # Identify title column
        title_col = "title" if "title" in schema else None
        
        # Identify text/body column ('md' for answerdotai/simplewiki, fallback to 'text', 'content')
        text_col = None
        for candidate in ["md", "text", "content", "body"]:
            if candidate in schema:
                text_col = candidate
                break

        if not text_col:
            raise ValueError(f"Could not locate text column in {file_path}. Schema columns: {schema}")

        columns_to_read = [col for col in [title_col, text_col] if col is not None]

        for batch in parquet_file.iter_batches(batch_size=batch_size, columns=columns_to_read):
            batch_dict = batch.to_pydict()
            titles = batch_dict.get(title_col, [""] * len(batch)) if title_col else [""] * len(batch)
            texts = batch_dict[text_col]

            for title_val, text_val in zip(titles, texts):
                title_str = str(title_val) if title_val is not None else ""
                text_str = str(text_val) if text_val is not None else ""

                yield current_doc_id, title_str, text_str
                current_doc_id += 1

                if max_docs is not None and current_doc_id >= max_docs:
                    return


def count_documents(data_path: Union[str, Path]) -> int:
    """Quickly counts total rows across all parquet files using metadata without reading row data."""
    parquet_files = find_parquet_files(data_path)
    total_rows = 0
    for file_path in parquet_files:
        meta = pq.read_metadata(str(file_path))
        total_rows += meta.num_rows
    return total_rows
