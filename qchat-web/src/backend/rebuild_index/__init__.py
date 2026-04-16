import logging
import os
from pathlib import Path

import azure.functions as func

from chat.RAG import DEFAULT_INDEX_DIR, DEFAULT_URLS_TXT, build_index


def _resolve_urls_file() -> Path:
    """
    Resolve URL list path.
    Supports:
    - absolute path in QCHAT_URLS_PATH
    - backend-relative file (e.g., qu_docs.txt)
    - chat-relative file fallback (chat/qu_docs.txt)
    """
    configured = (os.getenv("QCHAT_URLS_PATH") or "").strip()
    if not configured:
        return DEFAULT_URLS_TXT

    cfg_path = Path(configured)
    if cfg_path.is_absolute():
        return cfg_path

    backend_root = Path(__file__).resolve().parent.parent
    backend_relative = backend_root / cfg_path
    if backend_relative.exists():
        return backend_relative

    chat_relative = backend_root / "chat" / cfg_path
    if chat_relative.exists():
        return chat_relative

    # Fall back to backend-relative target to provide clearer errors in logs
    return backend_relative


def _resolve_index_dir() -> Path:
    configured = (os.getenv("QCHAT_INDEX_DIR") or "").strip()
    if not configured:
        return DEFAULT_INDEX_DIR
    cfg_path = Path(configured)
    if cfg_path.is_absolute():
        return cfg_path
    return Path(__file__).resolve().parent.parent / cfg_path


def _parse_max_urls() -> int | None:
    raw = (os.getenv("QCHAT_MAX_URLS") or "").strip()
    if not raw:
        return None
    try:
        value = int(raw)
        return value if value > 0 else None
    except ValueError:
        logging.warning("Invalid QCHAT_MAX_URLS value '%s'. Using full URL list.", raw)
        return None


def main(mytimer: func.TimerRequest) -> None:
    urls_file = _resolve_urls_file()
    index_dir = _resolve_index_dir()
    max_urls = _parse_max_urls()

    logging.info("Nightly FAISS rebuild started")
    logging.info("Using URLs file: %s", urls_file)
    logging.info("Using index dir: %s", index_dir)
    if max_urls:
        logging.info("QCHAT_MAX_URLS is set: %s", max_urls)

    if mytimer.past_due:
        logging.warning("Rebuild timer is running late")

    try:
        pages, chunks = build_index(
            urls_txt=urls_file,
            index_dir=index_dir,
            max_urls=max_urls,
        )
        logging.info(
            "Nightly FAISS rebuild complete. Pages ingested: %s, chunks: %s",
            pages,
            chunks,
        )
    except Exception as exc:
        logging.exception("Nightly FAISS rebuild failed: %r", exc)
        raise
