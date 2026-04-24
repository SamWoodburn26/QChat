import os
import smtplib
from email.message import EmailMessage
from typing import List

import requests


def parse_recipients(raw: str) -> List[str]:
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


def resolve_mail_provider() -> str:
    configured = os.getenv("MAIL_PROVIDER", "").strip().lower()
    if configured in {"google", "gmail"}:
        return "google"
    if configured in {"microsoft", "msgraph", "graph"}:
        return "microsoft"

    google_sender = os.getenv("GOOGLE_EMAIL_SENDER", "").strip()
    google_password = os.getenv("GOOGLE_APP_PASSWORD", "").strip()
    if google_sender and google_password:
        return "google"

    return "microsoft"


def _send_via_microsoft(
    recipients: List[str], subject: str, message_body: str, sender_name: str = ""
) -> None:
    tenant_id = os.getenv("MICROSOFT_TENANT_ID", "").strip()
    client_id = os.getenv("MICROSOFT_CLIENT_ID", "").strip()
    client_secret = os.getenv("MICROSOFT_CLIENT_SECRET", "").strip()
    sender_upn = os.getenv("MICROSOFT_SENDER_UPN", "").strip()

    if not tenant_id or not client_id or not client_secret or not sender_upn:
        raise RuntimeError(
            "Microsoft email is not configured. Set MICROSOFT_TENANT_ID, MICROSOFT_CLIENT_ID, MICROSOFT_CLIENT_SECRET, and MICROSOFT_SENDER_UPN."
        )

    token = _get_graph_token(tenant_id, client_id, client_secret)

    from_field = {"address": sender_upn}
    if sender_name:
        from_field["name"] = sender_name

    mail_payload = {
        "message": {
            "subject": subject,
            "from": {"emailAddress": from_field},
            "body": {
                "contentType": "Text",
                "content": message_body,
            },
            "toRecipients": [{"emailAddress": {"address": addr}} for addr in recipients],
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
        raise RuntimeError(f"Graph sendMail failed ({send_resp.status_code}): {send_resp.text}")


def _send_via_google(
    recipients: List[str], subject: str, message_body: str, sender_name: str = ""
) -> None:
    sender_email = os.getenv("GOOGLE_EMAIL_SENDER", "").strip()
    app_password = "".join(os.getenv("GOOGLE_APP_PASSWORD", "").split())
    smtp_host = os.getenv("GOOGLE_SMTP_HOST", "smtp.gmail.com").strip() or "smtp.gmail.com"
    smtp_port_raw = os.getenv("GOOGLE_SMTP_PORT", "465").strip() or "465"

    if not sender_email or not app_password:
        raise RuntimeError(
            "Google email is not configured. Set GOOGLE_EMAIL_SENDER and GOOGLE_APP_PASSWORD in .env."
        )

    try:
        smtp_port = int(smtp_port_raw)
    except ValueError as exc:
        raise RuntimeError("GOOGLE_SMTP_PORT must be a number.") from exc

    message = EmailMessage()
    message["From"] = f'"{sender_name}" <{sender_email}>' if sender_name else sender_email
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message.set_content(message_body)

    if smtp_port == 465:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=20) as server:
            server.login(sender_email, app_password)
            server.send_message(message)
        return

    with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(message)


def send_email(
    recipients: List[str], subject: str, message_body: str, sender_name: str = ""
) -> str:
    provider = resolve_mail_provider()
    if provider == "google":
        _send_via_google(recipients, subject, message_body, sender_name)
    else:
        _send_via_microsoft(recipients, subject, message_body, sender_name)
    return provider