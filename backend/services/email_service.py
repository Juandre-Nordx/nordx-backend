import os
import smtplib
from email.message import EmailMessage

ENV = os.getenv("ENVIRONMENT", "production")

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 465))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")

EMAIL_FROM = os.getenv("EMAIL_FROM")
RESET_URL = os.getenv("RESET_URL")  # base URL, no token yet


def send_jobcard_email(to_email: str, company_name: str, job_number: str, pdf_path: str):
    msg = EmailMessage()
    msg["From"] = f"NORDX <{EMAIL_FROM}>"
    msg["To"] = to_email
    msg["Subject"] = f"Job Card {job_number}"

    msg.set_content(f"""
Hello {company_name},

Please find attached Job Card {job_number}.

Regards,
NORDX
""")

    with open(pdf_path, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="application",
            subtype="pdf",
            filename=f"{job_number}.pdf"
        )

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)


def send_reset_email(to_email: str, token: str):
    if not SMTP_HOST or not SMTP_PASS or not EMAIL_FROM or not RESET_URL:
        raise RuntimeError("Email environment variables not configured")

    reset_link = f"{RESET_URL}?token={token}"

    subject_prefix = "[BETA] " if ENV == "beta" else ""
    subject = f"{subject_prefix}Reset your NORDX password"

    msg = EmailMessage()
    msg["From"] = f"NORDX <{EMAIL_FROM}>"
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.set_content(f"""
Hello,

You requested a password reset for your NORDX account.

Click the link below to reset your password:
{reset_link}

This link will expire in 1 hour.

If you did not request this, you can safely ignore this email.

Regards,
NORDX Team
""")

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
