import smtplib
from email.message import EmailMessage
import os

RESET_URL = os.getenv("RESET_URL")
EMAIL_FROM = os.getenv("EMAIL_FROM", "no-reply@localhost")

def send_reset_email(email: str, token: str):
    if not RESET_URL:
        raise RuntimeError("RESET_URL environment variable not set")

    reset_link = f"{RESET_URL}?token={token}"

    msg = EmailMessage()
    msg["Subject"] = "Password Reset"
    msg["From"] = EMAIL_FROM
    msg["To"] = email

    msg.set_content(
        f"""
Password Reset Request

Click the link below to reset your password:

{reset_link}

This link expires in 1 hour.
If you did not request this, ignore this email.
"""
    )

    with smtplib.SMTP("localhost", 1025) as s:
        s.send_message(msg)
