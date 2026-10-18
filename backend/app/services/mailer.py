"""Transactional email through Resend. To change provider, only `send` needs to change."""
from __future__ import annotations

import html
import logging

import httpx

from ..config import settings

log = logging.getLogger(__name__)


class MailError(Exception):
    pass


def configured() -> bool:
    return settings.has_email


def send(to: str, subject: str, text: str, body_html: str) -> None:
    try:
        r = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json={"from": settings.email_from, "to": [to], "subject": subject, "text": text, "html": body_html},
            timeout=10,
        )
    except httpx.HTTPError as exc:
        raise MailError("Email service unreachable.") from exc
    if r.status_code >= 300:
        log.error("Resend rejected the email: HTTP %s %s", r.status_code, r.text[:300])  # never includes the code
        raise MailError("Email service rejected the message.")


def send_reset_code(to: str, code: str, minutes: int) -> None:
    subject = "Your DeepSearch AI password reset code"
    text = (f"Your DeepSearch AI password reset code is {code}.\n\n"
            f"It expires in {minutes} minutes and works once. If you did not ask to reset your password, "
            "you can ignore this email; your password has not changed.")
    body = (
        '<div style="font-family:-apple-system,Segoe UI,Arial,sans-serif;max-width:420px;margin:auto;padding:24px">'
        '<h2 style="margin:0 0 12px">Reset your password</h2>'
        '<p>Enter this code in the DeepSearch AI app:</p>'
        f'<p style="font-size:32px;letter-spacing:8px;font-weight:700;margin:16px 0">{html.escape(code)}</p>'
        f'<p style="color:#555">It expires in {minutes} minutes and works once. If you did not ask to reset your '
        'password, you can ignore this email; your password has not changed.</p></div>'
    )
    send(to, subject, text, body)
