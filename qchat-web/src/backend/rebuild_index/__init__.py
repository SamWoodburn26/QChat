import azure.functions as func
import datetime
import os

# Import build_index from the chat function folder
from ..chat.RAG import build_index

def main(mytimer: func.TimerRequest) -> None:
    now = datetime.datetime.now().isoformat()
    print(f"[INDEX] Nightly rebuild started at {now}")

    try:
        # set QCHAT_MAX_URLS in local.settings.json
        max_urls = os.getenv("QCHAT_MAX_URLS")
        max_urls = int(max_urls) if max_urls else None

        pages, chunks = build_index(max_urls=max_urls)
        print(f"[INDEX] Rebuild complete. Pages={pages}, Chunks={chunks}")
    except Exception as e:
        print("[INDEX] Rebuild failed:", repr(e))
