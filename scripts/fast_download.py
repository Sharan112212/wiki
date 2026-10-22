"""
High-throughput parallel chunk downloader for SimpleWiki dataset.
Uses HTTP Range requests across parallel threads to bypass single-connection CDN throttling.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import sys
import time
import pyarrow.parquet as pq
import requests

DATASET_URL = "https://huggingface.co/datasets/answerdotai/simplewiki/resolve/main/data/articles/train-00000.parquet"
EXPECTED_SIZE = 175967358
CHUNK_SIZE = 4 * 1024 * 1024  # 4 MB per chunk
NUM_WORKERS = 24  # 24 parallel streams


def download_chunk(url: str, chunk_idx: int, start: int, end: int, part_path: Path, max_retries: int = 5):
    headers = {
        "Range": f"bytes={start}-{end}",
        "User-Agent": f"WikiFastDownloader/1.0 worker-{chunk_idx}"
    }
    for attempt in range(max_retries):
        try:
            r = requests.get(url, headers=headers, timeout=40)
            if r.status_code in (200, 206):
                content = r.content
                expected_len = end - start + 1
                if len(content) == expected_len:
                    part_path.write_bytes(content)
                    return chunk_idx, len(content)
                else:
                    time.sleep(1)
            else:
                time.sleep(1)
        except Exception:
            time.sleep(1 + attempt)
            
    raise RuntimeError(f"Failed to download chunk {chunk_idx} [{start}-{end}] after {max_retries} retries")


def fast_download(output_file: Path):
    output_file.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = output_file.parent / ".parts"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"[*] Starting parallel download of {EXPECTED_SIZE / (1024*1024):.2f} MB")
    print(f"[*] Parallel workers: {NUM_WORKERS}, Chunk size: {CHUNK_SIZE / (1024*1024):.1f} MB")
    
    # Calculate chunk ranges
    ranges = []
    chunk_idx = 0
    start = 0
    while start < EXPECTED_SIZE:
        end = min(start + CHUNK_SIZE - 1, EXPECTED_SIZE - 1)
        part_path = temp_dir / f"part_{chunk_idx:04d}.tmp"
        ranges.append((chunk_idx, start, end, part_path))
        start = end + 1
        chunk_idx += 1
        
    num_chunks = len(ranges)
    print(f"[*] Total chunks: {num_chunks}")
    
    start_time = time.time()
    completed_bytes = 0
    completed_chunks = 0
    
    # Check already downloaded parts
    tasks_to_run = []
    for c_idx, s, e, p_path in ranges:
        expected_len = e - s + 1
        if p_path.exists() and p_path.stat().st_size == expected_len:
            completed_bytes += expected_len
            completed_chunks += 1
        else:
            tasks_to_run.append((c_idx, s, e, p_path))
            
    print(f"[*] Resume check: {completed_chunks}/{num_chunks} chunks already present.")
    
    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = {
            executor.submit(download_chunk, DATASET_URL, c_idx, s, e, p_path): (c_idx, e - s + 1)
            for c_idx, s, e, p_path in tasks_to_run
        }
        
        for future in as_completed(futures):
            c_idx, chunk_bytes = future.result()
            completed_bytes += chunk_bytes
            completed_chunks += 1
            now = time.time()
            elapsed = now - start_time
            mb = completed_bytes / (1024 * 1024)
            total_mb = EXPECTED_SIZE / (1024 * 1024)
            pct = completed_bytes / EXPECTED_SIZE * 100
            speed = mb / elapsed if elapsed > 0 else 0
            print(f"    Progress: {mb:.1f}/{total_mb:.1f} MB ({pct:.1f}%) [{completed_chunks}/{num_chunks} chunks] @ {speed:.2f} MB/s", end="\r", flush=True)
            
    print()
    print(f"[*] Assembling {num_chunks} chunks into {output_file}...")
    temp_final = output_file.with_suffix(".assembling")
    with open(temp_final, "wb") as outfile:
        for c_idx, s, e, p_path in ranges:
            with open(p_path, "rb") as infile:
                outfile.write(infile.read())
            p_path.unlink()
            
    temp_dir.rmdir()
    temp_final.replace(output_file)
    total_time = time.time() - start_time
    print(f"[+] Download and assembly complete in {total_time:.1f}s!")


def verify(parquet_path: Path):
    print(f"[*] Verifying dataset: {parquet_path}")
    pf = pq.ParquetFile(str(parquet_path))
    num_rows = pf.metadata.num_rows
    print(f"[+] Verified successfully! Article count: {num_rows:,}")
    return num_rows


if __name__ == "__main__":
    target = Path("data/raw/simplewiki/train-00000.parquet")
    if target.exists() and target.stat().st_size == EXPECTED_SIZE:
        print(f"[+] File already exists with expected size: {target}")
    else:
        fast_download(target)
    verify(target)
