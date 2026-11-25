"""
Email Service for INDUSTRIA AI
Provides a clean abstraction for transactional emails (Password Reset, Notifications).
Supports SMTP with STARTTLS/SSL, professional HTML/text templates, and a thread-safe
in-memory outbox for local development and automated testing.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

from backend.app.config import settings

logger = logging.getLogger(__name__)

# In-memory development outbox for local testing when SMTP is not configured
_DEV_OUTBOX: List[Dict[str, Any]] = []

def get_dev_outbox() -> List[Dict[str, Any]]:
    """Returns a copy of emails captured in development mode."""
    return list(_DEV_OUTBOX)

def clear_dev_outbox() -> None:
    """Clears development outbox."""
    _DEV_OUTBOX.clear()

def get_latest_reset_link_for_email(email: str) -> Optional[str]:
    """Helper for testing: retrieves the most recent reset link sent to an email."""
    for item in reversed(_DEV_OUTBOX):
        if item.get("to_email", "").lower() == email.lower():
            return item.get("reset_url")
    return None

def build_password_reset_html(recipient_name: str, reset_url: str, expire_minutes: int) -> str:
    name_display = recipient_name if recipient_name else "Engineer"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Reset Your INDUSTRIA AI Password</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; color: #0f172a; margin: 0; padding: 0; }}
    .container {{ max-width: 560px; margin: 40px auto; background-color: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; overflow: hidden; }}
    .header {{ background-color: #0b1528; padding: 28px 32px; text-align: center; }}
    .header h1 {{ color: #ffffff; font-size: 20px; font-weight: 700; margin: 0; letter-spacing: -0.02em; }}
    .header p {{ color: #94a3b8; font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; margin: 6px 0 0; }}
    .content {{ padding: 36px 32px; }}
    .greeting {{ font-size: 16px; font-weight: 600; color: #0f172a; margin-bottom: 12px; }}
    .paragraph {{ font-size: 14px; line-height: 1.6; color: #475569; margin: 0 0 20px; }}
    .button-container {{ text-align: center; margin: 32px 0; }}
    .button {{ display: inline-block; background-color: #0284c7; color: #ffffff !important; font-size: 14px; font-weight: 600; text-decoration: none; padding: 12px 28px; border-radius: 10px; }}
    .link-alt {{ font-size: 12px; color: #64748b; line-height: 1.5; word-break: break-all; margin-top: 24px; padding: 12px; background-color: #f1f5f9; border-radius: 8px; }}
    .notice {{ background-color: #fffbeb; border: 1px solid #fef3c7; border-radius: 8px; padding: 12px 16px; margin: 24px 0 0; font-size: 12px; color: #92400e; }}
    .footer {{ background-color: #f8fafc; border-top: 1px solid #e2e8f0; padding: 20px 32px; text-align: center; font-size: 11px; color: #94a3b8; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>INDUSTRIA AI</h1>
      <p>Industrial Predictive Maintenance</p>
    </div>
    <div class="content">
      <div class="greeting">Hello {name_display},</div>
      <p class="paragraph">
        We received a request to reset the password for your INDUSTRIA AI engineering account. Click the secure button below to set a new password.
      </p>
      <div class="button-container">
        <a href="{reset_url}" target="_blank" class="button">Reset Password</a>
      </div>
      <div class="notice">
        <strong>Security Notice:</strong> This link is single-use and will expire in <strong>{expire_minutes} minutes</strong>. If you did not request a password reset, you can safely ignore this email; your existing password will remain unchanged.
      </div>
      <div class="link-alt">
        If the button does not work, copy and paste this link into your browser:<br>
        <a href="{reset_url}" style="color: #0284c7;">{reset_url}</a>
      </div>
    </div>
    <div class="footer">
      &copy; {datetime.utcnow().year} INDUSTRIA AI. All rights reserved. • Automated Security System
    </div>
  </div>
</body>
</html>"""

def build_password_reset_text(recipient_name: str, reset_url: str, expire_minutes: int) -> str:
    name_display = recipient_name if recipient_name else "Engineer"
    return f"""Hello {name_display},

We received a request to reset the password for your INDUSTRIA AI engineering account.

Please use the following secure link to set your new password:
{reset_url}

This link is single-use and will expire in {expire_minutes} minutes.

If you did not request this password reset, you can safely ignore this message. Your existing password will remain active.

--
INDUSTRIA AI Security Team
"""

def send_password_reset_email(
    to_email: str,
    reset_token: str,
    recipient_name: Optional[str] = None
) -> bool:
    """
    Sends a password reset email to the specified recipient.
    If SMTP_HOST is not configured, saves to the local dev outbox for testing/dev environments.
    """
    # Construct reset URL using configured FRONTEND_URL
    reset_url = f"{settings.FRONTEND_URL}/?reset_token={reset_token}"
    subject = "Reset your INDUSTRIA AI password"
    name_display = recipient_name or "Engineer"

    html_content = build_password_reset_html(
        recipient_name=name_display,
        reset_url=reset_url,
        expire_minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
    )
    text_content = build_password_reset_text(
        recipient_name=name_display,
        reset_url=reset_url,
        expire_minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
    )

    # Check if real SMTP provider is configured
    if settings.SMTP_HOST:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
            msg["To"] = to_email

            part1 = MIMEText(text_content, "plain")
            part2 = MIMEText(html_content, "html")
            msg.attach(part1)
            msg.attach(part2)

            if settings.SMTP_SSL:
                server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
            else:
                server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
                if settings.SMTP_TLS:
                    server.starttls()

            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)

            server.sendmail(settings.SMTP_FROM_EMAIL, [to_email], msg.as_string())
            server.quit()
            logger.info("Password reset email sent via SMTP to: %s", to_email)
            return True
        except Exception as e:
            logger.error("Failed to send password reset email via SMTP: %s", str(e))
            # In production, we don't leak SMTP errors to client to preserve enumeration resistance
            return False
    else:
        # Development / Local Testing Mode
        record = {
            "to_email": to_email,
            "recipient_name": name_display,
            "subject": subject,
            "reset_token": reset_token,
            "reset_url": reset_url,
            "sent_at": datetime.utcnow().isoformat(),
        }
        _DEV_OUTBOX.append(record)
        logger.info("Captured password reset email in local development outbox for: %s", to_email)
        return True

