import os
import base64
import zipfile
import io
import resend

resend.api_key = os.getenv("RESEND_API_KEY")

EMAIL_FROM = os.getenv("EMAIL_FROM")
RESET_URL = os.getenv("RESET_URL")
ENV = os.getenv("ENVIRONMENT", "production")


def send_jobcard_email(to_email: str, company_name: str, job_number: str, pdf_path: str):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(pdf_path, arcname=f"{job_number}.pdf")
    zip_bytes = zip_buffer.getvalue()
    zip_b64 = base64.b64encode(zip_bytes).decode("utf-8")

    html_body = f"""
    <p>Hello {company_name},</p>
    <p>Your job card <strong>{job_number}</strong> has been submitted successfully.</p>
    <p>Please find the job card PDF attached to this email as a zip file.</p>
    <br>
    <p>Regards,<br>NORDX</p>
    """

    resend.Emails.send({
        "from": f"NORDX <{EMAIL_FROM}>",
        "to": [to_email],
        "subject": f"Job Card {job_number} — NORDX",
        "html": html_body,
        "attachments": [
            {
                "filename": f"{job_number}.zip",
                "content": zip_b64,
            }
        ],
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
