@echo off
REM End-to-end: download dataset, build index, start server
echo === WikiSearch Setup ===

echo [1/3] Downloading dataset...
python scripts\download_data.py

echo [2/3] Building index...
python -m indexer.build --data-dir data\raw\simplewiki --output-dir data\index

echo [3/3] Starting server...
python -m backend.main --index-dir data\index --port 8000
