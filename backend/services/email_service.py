import smtplib
import os
from email.message import EmailMessage

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
EMAIL_FROM = os.getenv("EMAIL_FROM")
RESET_URL = os.getenv("RESET_URL")

def send_reset_email(email: str, token: str):
    if not RESET_URL:
        raise RuntimeError("RESET_URL not set")

    reset_link = f"{RESET_URL}?token={token}"

    msg = EmailMessage()
    msg["Subject"] = "Password Reset – NORDX"
    msg["From"] = EMAIL_FROM
    msg["To"] = email

    msg.set_content(f"""
Password Reset Request

Click the link below to reset your password:

{reset_link}

This link expires in 1 hour.
If you did not request this, ignore this email.
""")

   
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
            print("✅ PASSWORD RESET EMAIL SENT TO:", email)
    except Exception as e:
        print("❌ SMTP ERROR:", repr(e))
        raise