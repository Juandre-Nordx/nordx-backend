import os
import resend

resend.api_key = os.getenv("RESEND_API_KEY")

EMAIL_FROM = os.getenv("EMAIL_FROM")
RESET_URL = os.getenv("RESET_URL")
API_BASE_URL = os.getenv("API_BASE_URL", "").rstrip("/")
ENV = os.getenv("ENVIRONMENT", "production")


def send_jobcard_email(to_email: str, company_name: str, job_number: str, jobcard_id: int):
    download_link = f"{API_BASE_URL}/jobcards/{jobcard_id}/pdf"

    resend.Emails.send({
        "from": f"NORDX <{EMAIL_FROM}>",
        "to": [to_email],
        "subject": f"Job Card {job_number} — NORDX",
        "html": f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #333;">
                <h2 style="color: #1a1a1a;">Job Card {job_number}</h2>
                <p>Hello {company_name},</p>
                <p>
                    Your job card <strong>{job_number}</strong> has been completed and is ready for download.
                </p>
                <p style="margin: 24px 0;">
                    <a href="{download_link}"
                       style="background-color: #0057ff; color: #ffffff; padding: 12px 24px;
                              text-decoration: none; border-radius: 4px; font-weight: bold;">
                        Download Job Card PDF
                    </a>
                </p>
                <p style="color: #666; font-size: 13px;">
                    This link is available for 7 days. If you have trouble with the button above,
                    copy and paste the following URL into your browser:<br>
                    <a href="{download_link}" style="color: #0057ff;">{download_link}</a>
                </p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 32px 0;">
                <p style="color: #999; font-size: 12px;">
                    Regards,<br>
                    <strong>NORDX</strong>
                </p>
            </div>
        """,
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
