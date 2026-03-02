#!/usr/bin/env python3
"""
Rebuild FAISS Index - Manual script to rebuild the vector store index

This script rebuilds the FAISS index from scratch by:
1. Reading URLs from qu_docs.txt
2. Fetching content from each URL
3. Splitting into chunks
4. Creating embeddings
5. Saving the index to disk

Usage:
    python rebuild_faiss_index.py [--max-urls N]

Options:
    --max-urls N    Limit to first N URLs (useful for testing)

Environment Variables:
    QCHAT_CHUNK_SIZE       Chunk size for text splitting (default: 1000)
    QCHAT_CHUNK_OVERLAP    Chunk overlap (default: 150)
    QCHAT_EMBED_MODEL      Embedding model name (default: nomic-embed-text)
    OLLAMA_URL             Ollama server URL (default: http://127.0.0.1:11434)
"""

import sys
import argparse
from pathlib import Path

# Add the chat module to the path
sys.path.insert(0, str(Path(__file__).parent))

from chat.RAG import build_index, DEFAULT_URLS_TXT, DEFAULT_INDEX_DIR


def main():
    parser = argparse.ArgumentParser(
        description="Rebuild FAISS index for QChat RAG system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--max-urls',
        type=int,
        default=None,
        help='Limit to first N URLs (useful for testing)'
    )
    parser.add_argument(
        '--urls-file',
        type=Path,
        default=DEFAULT_URLS_TXT,
        help=f'Path to URLs file (default: {DEFAULT_URLS_TXT})'
    )
    parser.add_argument(
        '--index-dir',
        type=Path,
        default=DEFAULT_INDEX_DIR,
        help=f'Output directory for index (default: {DEFAULT_INDEX_DIR})'
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("QChat FAISS Index Rebuild")
    print("=" * 70)
    print(f"URLs file: {args.urls_file}")
    print(f"Index directory: {args.index_dir}")
    if args.max_urls:
        print(f"Max URLs: {args.max_urls}")
    print("=" * 70)
    print()
    
    try:
        pages, chunks = build_index(
            urls_txt=args.urls_file,
            index_dir=args.index_dir,
            max_urls=args.max_urls
        )
        
        print()
        print("=" * 70)
        print("✓ Index rebuild complete!")
        print(f"  Pages ingested: {pages}")
        print(f"  Total chunks: {chunks}")
        print(f"  Index location: {args.index_dir}")
        print("=" * 70)
        
        return 0
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure qu_docs.txt exists in the chat directory.")
        return 1
    except Exception as e:
        print(f"\n❌ Error during rebuild: {repr(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
