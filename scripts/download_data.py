"""
Robust, direct streaming downloader for answerdotai/simplewiki Parquet dataset.
Downloads train-00000.parquet directly into data/raw/simplewiki/ with real-time progress.
"""
import argparse
from pathlib import Path
import sys
import time
import pyarrow.parquet as pq
import requests

DATASET_URL = "https://huggingface.co/datasets/answerdotai/simplewiki/resolve/main/data/articles/train-00000.parquet"


def download_file(url: str, dest_path: Path):
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = dest_path.with_suffix(".tmp")
    
    print(f"[*] Downloading: {url}")
    print(f"[*] Destination: {dest_path}")
    
    headers = {"User-Agent": "WikiSearch-Indexer/1.0"}
    start_time = time.time()
    
    with requests.get(url, headers=headers, stream=True, timeout=30) as r:
        r.raise_for_status()
        total_size = int(r.headers.get("content-length", 0))
        downloaded = 0
        last_print = 0
        
        with open(temp_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):  # 1MB chunks
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    now = time.time()
                    if now - last_print >= 1.0 or downloaded == total_size:
                        mb = downloaded / (1024 * 1024)
                        total_mb = total_size / (1024 * 1024)
                        pct = (downloaded / total_size * 100) if total_size > 0 else 0
                        speed = mb / (now - start_time) if (now - start_time) > 0 else 0
                        print(f"    Progress: {mb:.1f}/{total_mb:.1f} MB ({pct:.1f}%) @ {speed:.2f} MB/s", end="\r", flush=True)
                        last_print = now
                        
        print()
        
    temp_path.replace(dest_path)
    elapsed = time.time() - start_time
    print(f"[+] Download complete: {dest_path.name} ({dest_path.stat().st_size / (1024*1024):.2f} MB in {elapsed:.1f}s)")


def verify_dataset(dest_path: Path):
    print(f"[*] Verifying parquet file: {dest_path}")
    parquet_file = pq.ParquetFile(str(dest_path))
    num_rows = parquet_file.metadata.num_rows
    num_columns = parquet_file.metadata.num_columns
    schema_names = parquet_file.schema.names
    
    print(f"[+] Row count: {num_rows:,} articles")
    print(f"[+] Columns ({num_columns}): {schema_names}")
    
    # Read first row as a smoke test
    batch = next(parquet_file.iter_batches(batch_size=1))
    pydict = batch.to_pydict()
    first_title = pydict.get("title", [""])[0]
    print(f"[+] First article title sample: '{first_title}'")
    return num_rows


def main():
    parser = argparse.ArgumentParser(description="Download answerdotai/simplewiki dataset.")
    parser.add_argument("--output-dir", default="data/raw/simplewiki", help="Destination folder")
    args = parser.parse_args()
    
    dest_file = Path(args.output_dir) / "train-00000.parquet"
    if dest_file.exists() and dest_file.stat().st_size == 175967358:
        print(f"[+] File already exists and matches expected size: {dest_file}")
    else:
        download_file(DATASET_URL, dest_file)
        
    verify_dataset(dest_file)


if __name__ == "__main__":
    main()
