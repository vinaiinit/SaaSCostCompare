import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


def send_password_reset_email(to_email: str, token: str) -> bool:
    """Send a password reset email. Returns True on success, False on failure."""
    reset_link = f"{FRONTEND_URL}/reset-password?token={token}"

    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto; padding: 30px;">
        <div style="text-align: center; margin-bottom: 30px;">
            <div style="display: inline-block; background: #003366; color: white; font-weight: bold;
                        padding: 8px 12px; border-radius: 6px; font-size: 14px;">SC</div>
            <span style="font-size: 20px; font-weight: bold; color: #003366; margin-left: 8px;">SaaSCostCompare</span>
        </div>
        <h2 style="color: #003366; margin-bottom: 10px;">Reset Your Password</h2>
        <p style="color: #555; line-height: 1.6;">
            We received a request to reset your password. Click the button below to choose a new password.
            This link will expire in 1 hour.
        </p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{reset_link}"
               style="background: #003366; color: white; padding: 12px 30px; text-decoration: none;
                      border-radius: 6px; font-weight: bold; display: inline-block;">
                Reset Password
            </a>
        </div>
        <p style="color: #999; font-size: 13px; line-height: 1.5;">
            If you didn't request this, you can safely ignore this email. Your password will not change.
        </p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;" />
        <p style="color: #bbb; font-size: 11px; text-align: center;">SaaSCostCompare — Independent SaaS Benchmarking</p>
    </div>
    """

    if not SMTP_HOST or not SMTP_USER:
        # No email configured — log the reset link for development
        print(f"[PASSWORD RESET] No SMTP configured. Reset link for {to_email}: {reset_link}")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Reset your SaaSCostCompare password"
        msg["From"] = SMTP_FROM
        msg["To"] = to_email
        msg.attach(MIMEText(f"Reset your password: {reset_link}", "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, to_email, msg.as_string())

        return True
    except Exception as e:
        print(f"[PASSWORD RESET] Failed to send email to {to_email}: {e}")
        return False
