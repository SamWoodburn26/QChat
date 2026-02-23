import azure.functions as func
import json
import os
from pathlib import Path

# Path to qu_docs.txt (same file the RAG/chat uses)
BACKEND_DIR = Path(__file__).resolve().parent.parent
QU_DOCS_FILE = BACKEND_DIR / "chat" / "qu_docs.txt"


def _read_urls():
    """Read URLs from qu_docs.txt, one per line (http/https only)."""
    urls = []
    path = os.getenv("QCHAT_URLS_PATH")
    if path and os.path.isabs(path):
        file_path = Path(path)
    else:
        file_path = QU_DOCS_FILE
    if not file_path.exists():
        return urls
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            u = line.strip()
            if u.startswith("http://") or u.startswith("https://"):
                urls.append(u)
    return urls


def main(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        response = func.HttpResponse("")
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    if req.method != "GET":
        return func.HttpResponse(
            json.dumps({"error": "Method not allowed"}),
            status_code=405,
            mimetype="application/json",
        )

    try:
        urls = _read_urls()
        body = json.dumps({"urls": urls})
        response = func.HttpResponse(body, mimetype="application/json")
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response
    except Exception as e:
        response = func.HttpResponse(
            json.dumps({"error": str(e), "urls": []}),
            status_code=500,
            mimetype="application/json",
        )
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response
