import os
import resend

resend.api_key = os.getenv("RESEND_API_KEY")

EMAIL_FROM = os.getenv("EMAIL_FROM")
RESET_URL = os.getenv("RESET_URL")
API_BASE_URL = os.getenv("API_BASE_URL", "").rstrip("/")
ENV = os.getenv("ENVIRONMENT", "production")


def send_jobcard_email(to_email: str, company_name: str, job_number: str, jobcard_id: int):
    download_url = f"{API_BASE_URL}/jobcards/{jobcard_id}/pdf"

    body = f"""Hello {company_name},

Your job card {job_number} is ready for download.

Download URL:
{download_url}

Copy and paste the URL above into your browser to download the PDF.

Regards,
NORDX"""

    resend.Emails.send({
        "from": f"NORDX <{EMAIL_FROM}>",
        "to": [to_email],
        "subject": f"Job Card {job_number} — NORDX",
        "text": body,
    })


def send_reset_email(to_email: str, token: str):
    reset_link = f"{RESET_URL}?token={token}"

    subject_prefix = "[BETA] " if ENV == "beta" else ""

    resend.Emails.send({
        "from": f"NORDX <{EMAIL_FROM}>",
        "to": [to_email],
        "subject": f"{subject_prefix}Reset your NORDX password",
        "html": f"""
            <p>Hello,</p>
            <p>You requested a password reset.</p>
            <p>
                <a href="{reset_link}">Click here to reset your password</a>
            </p>
            <p>This link expires in 1 hour.</p>
        """
    })
