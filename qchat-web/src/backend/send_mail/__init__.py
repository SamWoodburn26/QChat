import os
import json
from typing import List

import azure.functions as func
import requests

from env_loader import load_backend_env

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


def _parse_recipients(raw: str) -> List[str]:
    parts = []
    for token in raw.replace("\n", ",").replace(";", ",").split(","):
        email = token.strip()
        if email:
            parts.append(email)
    return parts


def _get_graph_token(tenant_id: str, client_id: str, client_secret: str) -> str:
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    token_resp = requests.post(
        token_url,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
            "scope": "https://graph.microsoft.com/.default",
        },
        timeout=20,
    )
    token_resp.raise_for_status()
    token_data = token_resp.json()
    token = token_data.get("access_token")
    if not token:
        raise RuntimeError("No access token returned by Microsoft token endpoint")
    return token


def main(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return _json_response({}, status_code=200)

    tenant_id = os.getenv("MICROSOFT_TENANT_ID", "").strip()
    client_id = os.getenv("MICROSOFT_CLIENT_ID", "").strip()
    client_secret = os.getenv("MICROSOFT_CLIENT_SECRET", "").strip()
    sender_upn = os.getenv("MICROSOFT_SENDER_UPN", "").strip()

    if not tenant_id or not client_id or not client_secret or not sender_upn:
        return _json_response(
            {
                "success": False,
                "error": "Microsoft email is not configured. Set MICROSOFT_TENANT_ID, MICROSOFT_CLIENT_ID, MICROSOFT_CLIENT_SECRET, and MICROSOFT_SENDER_UPN.",
            },
            status_code=500,
        )

    try:
        body = req.get_json()
    except ValueError:
        return _json_response({"success": False, "error": "Invalid JSON body"}, status_code=400)

    to_raw = (body.get("to") or "").strip()
    subject = (body.get("subject") or "").strip()
    message_body = (body.get("body") or "").strip()

    recipients = _parse_recipients(to_raw)
    if not recipients:
        return _json_response({"success": False, "error": "At least one recipient is required"}, status_code=400)
    if not subject:
        return _json_response({"success": False, "error": "Subject is required"}, status_code=400)
    if not message_body:
        return _json_response({"success": False, "error": "Message body is required"}, status_code=400)

    try:
        token = _get_graph_token(tenant_id, client_id, client_secret)

        mail_payload = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "Text",
                    "content": message_body,
                },
                "toRecipients": [
                    {"emailAddress": {"address": addr}} for addr in recipients
                ],
            },
            "saveToSentItems": True,
        }

        send_url = f"https://graph.microsoft.com/v1.0/users/{sender_upn}/sendMail"
        send_resp = requests.post(
            send_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=mail_payload,
            timeout=20,
        )

        if send_resp.status_code not in (200, 202):
            return _json_response(
                {
                    "success": False,
                    "error": f"Graph sendMail failed ({send_resp.status_code})",
                    "details": send_resp.text,
                },
                status_code=502,
            )

        return _json_response({"success": True, "message": "Email sent successfully"})

    except requests.HTTPError as exc:
        return _json_response(
            {
                "success": False,
                "error": "Microsoft token request failed",
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
