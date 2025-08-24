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
