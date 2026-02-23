import azure.functions as func
import json
import os

# Path to chat/qu_docs.txt (relative to this function's directory)
QU_DOCS_PATH = os.path.join(os.path.dirname(__file__), "..", "chat", "qu_docs.txt")


def _read_urls():
    if not os.path.exists(QU_DOCS_PATH):
        return []
    with open(QU_DOCS_PATH, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip().startswith(("http://", "https://"))]


def _write_urls(urls):
    with open(QU_DOCS_PATH, "w", encoding="utf-8") as f:
        for u in urls:
            f.write(u + "\n")


def main(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        response = func.HttpResponse("")
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    try:
        if req.method == "GET":
            urls = _read_urls()
            return _json_response({"urls": urls})

        if req.method == "POST":
            try:
                body = req.get_json()
            except ValueError:
                return _json_response({"error": "Invalid JSON"}, 400)
            urls = body.get("urls")
            if not isinstance(urls, list):
                return _json_response({"error": "Body must contain 'urls' array"}, 400)
            urls = [u.strip() for u in urls if isinstance(u, str) and u.strip().startswith(("http://", "https://"))]
            _write_urls(urls)
            return _json_response({"urls": urls})

        return _json_response({"error": "Method not allowed"}, 405)
    except Exception as e:
        return _json_response({"error": str(e)}, 500)


def _json_response(data, status_code=200):
    response = func.HttpResponse(
        json.dumps(data),
        status_code=status_code,
        mimetype="application/json",
    )
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response
