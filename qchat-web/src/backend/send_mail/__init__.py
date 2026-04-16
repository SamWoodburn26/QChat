import json
import smtplib

import azure.functions as func
import requests

from env_loader import load_backend_env
from mail_service import parse_recipients, send_email

load_backend_env()


def _json_response(payload: dict, status_code: int = 200) -> func.HttpResponse:
    response = func.HttpResponse(
        json.dumps(payload),
        status_code=status_code,
        mimetype="application/json",
    )
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response

def main(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return _json_response({}, status_code=200)

    try:
        body = req.get_json()
    except ValueError:
        return _json_response({"success": False, "error": "Invalid JSON body"}, status_code=400)

    to_raw = (body.get("to") or "").strip()
    subject = (body.get("subject") or "").strip()
    message_body = (body.get("body") or "").strip()
    sender_name = (body.get("sender_name") or "").strip()

    recipients = parse_recipients(to_raw)
    if not recipients:
        return _json_response({"success": False, "error": "At least one recipient is required"}, status_code=400)
    if not subject:
        return _json_response({"success": False, "error": "Subject is required"}, status_code=400)
    if not message_body:
        return _json_response({"success": False, "error": "Message body is required"}, status_code=400)

    try:
        provider = send_email(recipients, subject, message_body, sender_name)

        return _json_response(
            {"success": True, "message": f"Email sent successfully via {provider}"}
        )

    except requests.HTTPError as exc:
        return _json_response(
            {
                "success": False,
                "error": "Microsoft token request failed",
                "details": str(exc),
            },
            status_code=502,
        )
    except smtplib.SMTPException as exc:
        return _json_response(
            {
                "success": False,
                "error": "Google SMTP send failed",
                "details": str(exc),
            },
            status_code=502,
        )
    except Exception as exc:
        return _json_response(
            {
                "success": False,
                "error": "Failed to send email",
                "details": repr(exc),
            },
            status_code=500,
        )
