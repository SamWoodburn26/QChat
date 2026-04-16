# FAISS Index Rebuild Guide

## Overview
The QChat system uses a FAISS vector store to enable semantic search over Quinnipiac University documentation. The index needs to be built before the system can answer questions using RAG.

## Prerequisites

1. **Install dependencies:**
   ```bash
   cd /home/thomas/QChat/QChat/qchat-web/src/backend
   pip install -r requirements.txt
   ```

2. **Verify local.settings.json:**
   - The file should exist at `/home/thomas/QChat/QChat/qchat-web/src/backend/local.settings.json`
   - It should contain `OLLAMA_URL` pointing to your Ollama instance
   - The system automatically loads settings from this file!

3. **Ensure Ollama is accessible:**
   ```bash
   # Test your Ollama URL from local.settings.json
   curl https://your-ngrok-url.ngrok-free.dev/api/tags
   ```

4. **Verify qu_docs.txt exists:**
   The file `chat/qu_docs.txt` should contain one URL per line.

## How to Rebuild the Index

### Important: Configuration

The system automatically loads settings from `local.settings.json`, so no manual environment variable setup is needed! 

If you prefer to override settings, you can still set environment variables:
```bash
export OLLAMA_URL="https://your-custom-url.ngrok-free.dev"
```

### Method 1: Using the rebuild script (Recommended)

```bash
cd /home/thomas/QChat/QChat/qchat-web/src/backend
python rebuild_faiss_index.py
```

**Options:**
- `--max-urls N` - Only process first N URLs (useful for testing)
- `--urls-file PATH` - Use custom URLs file
- `--index-dir PATH` - Save index to custom location

**Examples:**
```bash
# Full rebuild
python rebuild_faiss_index.py

# Test with 5 URLs
python rebuild_faiss_index.py --max-urls 5

# Custom locations
python rebuild_faiss_index.py --urls-file /path/to/urls.txt --index-dir /path/to/index
```

### Method 2: Directly with Python

```bash
cd /home/thomas/QChat/QChat/qchat-web/src/backend
python -m chat.RAG
```

### Method 3: From Python code

```python
from chat.RAG import build_index

# Full rebuild
pages, chunks = build_index()

# With options
pages, chunks = build_index(max_urls=10)
```

## Progress Indicators

During the rebuild, you'll see:
1. **Fetching URLs** - Progress bar showing URL fetching with success/failed counts
2. **Splitting documents** - Information about chunk creation
3. **Building FAISS index** - Embedding generation (can take time)
4. **Saving index** - Writing to disk

Example output:
```
[RAG] Building index from 150 URLs...
Fetching URLs: 100%|████████████| 150/150 [05:23<00:00, 2.15s/url] success: 142, failed: 8

[RAG] Splitting 142 documents into chunks...
[RAG] Created 2847 chunks from 142 pages
[RAG] Building FAISS index with 2847 chunks (this may take a while)...
[RAG] Saving index to disk...
[RAG] ✓ Successfully saved FAISS index to: chat/faiss_index
```

## Configuration

Settings are automatically loaded from `local.settings.json` in the backend directory.

You can override any setting with environment variables:

```bash
# Ollama connection (auto-loaded from local.settings.json)
export OLLAMA_URL=https://your-ngrok-url.ngrok-free.dev

# Text splitting
export QCHAT_CHUNK_SIZE=1000          # Size of each chunk
export QCHAT_CHUNK_OVERLAP=150        # Overlap between chunks

# Embedding model
export QCHAT_EMBED_MODEL=nomic-embed-text

# Sleep settings (politeness)
export QCHAT_SLEEP_EVERY_N=25         # Sleep every N requests
export QCHAT_SLEEP_SECONDS=0.5        # Sleep duration

# Request settings
export QCHAT_REQUEST_TIMEOUT=12       # Timeout per URL
```

## Troubleshooting

### "Failed to connect to Ollama" error
- **Check local.settings.json**: Verify `OLLAMA_URL` is set correctly in `local.settings.json`
- **Test the connection**: `curl https://your-ngrok-url.ngrok-free.dev/api/tags`
- **Verify the embedding model is available**: The system needs the `nomic-embed-text` model
- Look for the startup message: `[RAG] Using Ollama at: <your-url>` to confirm it's using the right URL

### "FAISS index not found" error
- Run the rebuild script to create the index first

### Ollama connection errors
- Verify `OLLAMA_URL` in `local.settings.json` is correct
- Check that Ollama is accessible: `curl <your-ollama-url>/api/tags`
- Look for the startup message showing which URL is being used

### Import errors
- Install dependencies: `pip install -r requirements.txt`
- Make sure you're in the backend directory

### Slow rebuild
- Use `--max-urls 5` to test with fewer URLs
- Increase `QCHAT_SLEEP_EVERY_N` or decrease `QCHAT_SLEEP_SECONDS`
- Check your internet connection

### Permission errors
- Ensure write permissions to `chat/faiss_index` directory

## Automated Rebuild

The system includes an Azure Function for nightly rebuilds:
- **Location**: `rebuild_index/__init__.py`
- **Configuration**: Set `QCHAT_MAX_URLS` in `local.settings.json`
- **Trigger**: Timer-based via `rebuild_index/function.json` (default `0 0 2 * * *`, daily at 2:00 AM)
- **Enable/Disable**: `AzureWebJobs.rebuild_index.Disabled` (set to `"false"` to run)

## Index Location

Default location: `/home/thomas/QChat/QChat/qchat-web/src/backend/chat/faiss_index/`

The index consists of:
- `index.faiss` - Vector index
- `index.pkl` - Metadata pickle file

## When to Rebuild

Rebuild the index when:
- Setting up the system for the first time
- URLs in `qu_docs.txt` have changed
- Website content has been updated significantly
- Changing embedding model or chunk settings
