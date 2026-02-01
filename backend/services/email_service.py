import os
import requests

# =========================
# ENV CONFIG
# =========================

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
RESET_URL = os.getenv("RESET_URL")

# Default sender (must be verified in Resend)
EMAIL_FROM = os.getenv("EMAIL_FROM", "onboarding@resend.dev")

if not RESEND_API_KEY:
    raise RuntimeError("RESEND_API_KEY not set")


RESEND_ENDPOINT = "https://api.resend.com/emails"


# =========================
# PASSWORD RESET EMAIL
# =========================
def send_reset_email(email: str, token: str):
    """
    Sends a password reset email using Resend
    """

    reset_link = f"{RESET_URL}?token={token}"

    payload = {
        "from": EMAIL_FROM,
        "to": email,
        "subject": "Reset your password – NORDX",
        "html": f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px;">
            <h2>Password Reset</h2>
            <p>You requested a password reset for your NORDX account.</p>
            <p>
              <a href="{reset_link}"
                 style="display:inline-block;padding:12px 18px;
                        background:#0f172a;color:#fff;
                        text-decoration:none;border-radius:6px;">
                Reset Password
              </a>
            </p>
            <p>This link expires in 1 hour.</p>
            <p>If you didn’t request this, ignore this email.</p>
        </div>
        """
    }

    response = requests.post(
        RESEND_ENDPOINT,
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=10,
    )

    if response.status_code >= 400:
        print("❌ Resend error (reset email):", response.status_code, response.text)
        return

    print("✅ Password reset email sent to", email)


# =========================
# JOB CARD PDF EMAIL
# =========================
def send_jobcard_email(
    to_email: str,
    pdf_path: str,
    job_number: str,
    company_name: str,
):
    """
    Sends a job card PDF to the company admin email
    """

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    # Read PDF as bytes
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    payload = {
        "from": EMAIL_FROM,
        "to": to_email,
        "subject": f"Job Card {job_number}",
        "html": f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px;">
            <h2>Job Card Completed</h2>
            <p>Please find attached the job card:</p>
            <p><strong>{job_number}</strong></p>
            <br>
            <p>Regards,<br>{company_name}</p>
        </div>
        """,
        "attachments": [
            {
                "filename": f"{job_number}.pdf",
                "content": pdf_bytes,
            }
        ],
    }

    response = requests.post(
        RESEND_ENDPOINT,
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=15,
    )

    if response.status_code >= 400:
        print("❌ Resend error (jobcard email):", response.status_code, response.text)
        return

    print(f"📧 Job card email sent to {to_email} ({job_number})")
