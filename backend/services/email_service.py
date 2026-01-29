import os
import requests

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
RESET_URL = os.getenv("RESET_URL")
EMAIL_FROM = os.getenv("EMAIL_FROM", "onboarding@resend.dev")

if not RESEND_API_KEY:
    raise RuntimeError("RESEND_API_KEY not set")


def send_reset_email(email: str, token: str):
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
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=10
    )

    if response.status_code >= 400:
        print("❌ Resend error:", response.status_code, response.text)
        return

    print("✅ Password reset email sent via Resend to", email)
