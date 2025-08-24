"""
SMTP mail helper using SendGrid's SMTP relay.
Reads all settings from environment variables so no secrets are committed.
Required env vars:
  SMTP_HOST=smtp.sendgrid.net
  SMTP_PORT=587
  SMTP_USER=apikey             # literally the word 'apikey'
  SMTP_PASS=<SENDGRID_API_KEY> # set only in .env / Render, never in code
  EMAIL_FROM=support@coro.biz
  EMAIL_REPLY_TO=support@coro.biz  (optional; defaults to EMAIL_FROM)
"""

import os, smtplib, ssl
from email.message import EmailMessage
from urllib.parse import urlencode

SMTP_HOST = os.environ["SMTP_HOST"]
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ["SMTP_USER"]
SMTP_PASS = os.environ["SMTP_PASS"]
EMAIL_FROM = os.environ["EMAIL_FROM"]
EMAIL_REPLY_TO = os.environ.get("EMAIL_REPLY_TO", EMAIL_FROM)

def send_mail(to_addr: str, subject: str, text: str, html: str | None = None):
    """Send a plain-text (and optional HTML) email via SMTP+STARTTLS."""
    msg = EmailMessage()
    msg["From"] = EMAIL_FROM
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg["Reply-To"] = EMAIL_REPLY_TO
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")

    ctx = ssl.create_default_context()
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.ehlo()
        s.starttls(context=ctx)
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)


def send_password_reset_email(to_addr: str, token: str):
    """
    Compose and send a password reset email.
    Uses APP_BASE_URL or falls back to request.host_url provided by caller.
    """
    base_url = os.getenv("APP_BASE_URL", "https://nextchapter.onrender.com")
    reset_path = "/reset"
    reset_url = f"{base_url.rstrip('/')}{reset_path}?{urlencode({'token': token})}"

    subject = "Reset your password"
    text = f"Click this link to reset your password: {reset_url}"
    html = (
        f"""<p>Click this link to reset your password:</p>
               <p><a href=\"{reset_url}\">{reset_url}</a></p>"""
    )

    # reuse existing helper
    send_mail(to_addr, subject, text, html)


def send_verification_email(to_addr: str, token: str):
    """
    Compose and send an email verification message.
    Builds a link using APP_BASE_URL (defaults to https://nextchapter.onrender.com).
    """
    base_url = os.getenv("APP_BASE_URL", "https://nextchapter.onrender.com")
    verify_path = "/verify"
    verify_url = f"{base_url.rstrip('/')}{verify_path}?{urlencode({'token': token})}"

    subject = "Confirm your email"
    text = f"Please confirm your email by clicking: {verify_url}"
    html = f"""<p>Please confirm your email by clicking the link below:</p>
               <p><a href=\"{verify_url}\">{verify_url}</a></p>"""

    send_mail(to_addr, subject, text, html)
