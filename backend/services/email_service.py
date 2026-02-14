import os
import base64
import resend

resend.api_key = os.getenv("RESEND_API_KEY")

EMAIL_FROM = os.getenv("EMAIL_FROM")
RESET_URL = os.getenv("RESET_URL")
ENV = os.getenv("ENVIRONMENT", "production")


def send_jobcard_email(to_email: str, company_name: str, job_number: str, pdf_path: str):
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    encoded_pdf = base64.b64encode(pdf_bytes).decode()

    resend.Emails.send({
        "from": f"NORDX <{EMAIL_FROM}>",
        "to": [to_email],
        "subject": f"Job Card {job_number}",
        "html": f"""
            <p>Hello {company_name},</p>
            <p>Please find attached Job Card <strong>{job_number}</strong>.</p>
            <p>Regards,<br>NORDX</p>
        """,
        "attachments": [
            {
                "filename": f"{job_number}.pdf",
                "content": encoded_pdf
            }
        ]
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
