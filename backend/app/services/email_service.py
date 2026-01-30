"""
Email Service: Sends personalized ebook PDFs to users.
Supports multiple providers: SMTP, SendGrid, Resend.
Falls back gracefully if email delivery fails.
"""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import Dict, Any, Optional
from datetime import datetime

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """
    Sends personalized ebooks via email.

    Supports:
    - SMTP (Gmail, custom SMTP servers)
    - SendGrid API
    - Resend API
    - Mock mode for testing
    """

    def __init__(self):
        """Initialize email service based on available credentials."""
        self.provider = self._detect_provider()
        self.from_email = os.getenv("EMAIL_FROM", "noreply@example.com")
        self.from_name = os.getenv("EMAIL_FROM_NAME", "Your Personalized Ebook")
        logger.info(f"Email service initialized with provider: {self.provider}")

    def _detect_provider(self) -> str:
        """Detect which email provider to use based on available credentials."""
        if os.getenv("SENDGRID_API_KEY"):
            return "sendgrid"
        elif os.getenv("RESEND_API_KEY"):
            return "resend"
        elif os.getenv("SMTP_HOST"):
            return "smtp"
        else:
            return "mock"

    async def send_ebook(
        self,
        to_email: str,
        pdf_bytes: bytes,
        profile: Dict[str, Any],
        intro_hook: str,
        cta: str
    ) -> Dict[str, Any]:
        """
        Send personalized ebook PDF via email.

        Args:
            to_email: Recipient email address
            pdf_bytes: PDF file content
            profile: User profile data for personalization
            intro_hook: Personalized intro hook
            cta: Personalized CTA

        Returns:
            Dict with success status, message_id, provider
        """
        first_name = profile.get("first_name", "there")
        company = profile.get("company_name", "your company")

        subject = f"{first_name}, your personalized ebook is ready!"
        html_body = self._build_email_html(first_name, company, intro_hook, cta)
        text_body = self._build_email_text(first_name, company, intro_hook, cta)

        try:
            if self.provider == "sendgrid":
                result = await self._send_via_sendgrid(
                    to_email, subject, html_body, text_body, pdf_bytes
                )
            elif self.provider == "resend":
                result = await self._send_via_resend(
                    to_email, subject, html_body, pdf_bytes
                )
            elif self.provider == "smtp":
                result = await self._send_via_smtp(
                    to_email, subject, html_body, text_body, pdf_bytes
                )
            else:
                result = self._send_mock(to_email, subject)

            logger.info(f"Email sent to {to_email} via {self.provider}")
            return result

        except Exception as e:
            logger.error(f"Email delivery failed for {to_email}: {e}")
            return {
                "success": False,
                "provider": self.provider,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    def _build_email_html(
        self,
        first_name: str,
        company: str,
        intro_hook: str,
        cta: str
    ) -> str:
        """Build HTML email body."""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px; border-radius: 10px; text-align: center; margin-bottom: 30px;">
        <h1 style="color: white; margin: 0; font-size: 28px;">Your Personalized Ebook</h1>
        <p style="color: rgba(255,255,255,0.9); margin-top: 10px;">Tailored insights for {company}</p>
    </div>

    <p style="font-size: 18px;">Hi {first_name},</p>

    <p style="font-size: 16px;">{intro_hook}</p>

    <div style="background: #f7fafc; border-left: 4px solid #667eea; padding: 20px; margin: 30px 0; border-radius: 0 8px 8px 0;">
        <p style="margin: 0; font-weight: 600; color: #1a365d;">{cta}</p>
    </div>

    <p style="font-size: 16px;">Your personalized ebook is attached to this email. We've customized it based on your role and industry to deliver maximum value.</p>

    <p style="font-size: 16px; margin-top: 30px;">
        Best regards,<br>
        <strong>The Team</strong>
    </p>

    <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 40px 0;">

    <p style="font-size: 12px; color: #718096; text-align: center;">
        This email was sent because you requested a personalized ebook.<br>
        &copy; {datetime.utcnow().year} All rights reserved.
    </p>
</body>
</html>
"""

    def _build_email_text(
        self,
        first_name: str,
        company: str,
        intro_hook: str,
        cta: str
    ) -> str:
        """Build plain text email body."""
        return f"""
Your Personalized Ebook - Tailored for {company}

Hi {first_name},

{intro_hook}

{cta}

Your personalized ebook is attached to this email. We've customized it based on your role and industry to deliver maximum value.

Best regards,
The Team

---
This email was sent because you requested a personalized ebook.
"""

    async def _send_via_sendgrid(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
        pdf_bytes: bytes
    ) -> Dict[str, Any]:
        """Send email via SendGrid API."""
        import base64

        api_key = os.getenv("SENDGRID_API_KEY")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "personalizations": [{"to": [{"email": to_email}]}],
                    "from": {"email": self.from_email, "name": self.from_name},
                    "subject": subject,
                    "content": [
                        {"type": "text/plain", "value": text_body},
                        {"type": "text/html", "value": html_body}
                    ],
                    "attachments": [{
                        "content": base64.b64encode(pdf_bytes).decode(),
                        "filename": "your-personalized-ebook.pdf",
                        "type": "application/pdf",
                        "disposition": "attachment"
                    }]
                },
                timeout=30.0
            )

        if response.status_code in (200, 202):
            return {
                "success": True,
                "provider": "sendgrid",
                "message_id": response.headers.get("X-Message-Id", "unknown"),
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise Exception(f"SendGrid API error: {response.status_code} - {response.text}")

    async def _send_via_resend(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        pdf_bytes: bytes
    ) -> Dict[str, Any]:
        """Send email via Resend API."""
        import base64

        api_key = os.getenv("RESEND_API_KEY")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "from": f"{self.from_name} <{self.from_email}>",
                    "to": [to_email],
                    "subject": subject,
                    "html": html_body,
                    "attachments": [{
                        "content": base64.b64encode(pdf_bytes).decode(),
                        "filename": "your-personalized-ebook.pdf"
                    }]
                },
                timeout=30.0
            )

        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "provider": "resend",
                "message_id": data.get("id", "unknown"),
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise Exception(f"Resend API error: {response.status_code} - {response.text}")

    async def _send_via_smtp(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
        pdf_bytes: bytes
    ) -> Dict[str, Any]:
        """Send email via SMTP."""
        smtp_host = os.getenv("SMTP_HOST")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_pass = os.getenv("SMTP_PASS", "")
        use_tls = os.getenv("SMTP_TLS", "true").lower() == "true"

        msg = MIMEMultipart("mixed")
        msg["From"] = f"{self.from_name} <{self.from_email}>"
        msg["To"] = to_email
        msg["Subject"] = subject

        # Create alternative part for text/html
        alt_part = MIMEMultipart("alternative")
        alt_part.attach(MIMEText(text_body, "plain"))
        alt_part.attach(MIMEText(html_body, "html"))
        msg.attach(alt_part)

        # Attach PDF
        pdf_attachment = MIMEApplication(pdf_bytes, _subtype="pdf")
        pdf_attachment.add_header(
            "Content-Disposition",
            "attachment",
            filename="your-personalized-ebook.pdf"
        )
        msg.attach(pdf_attachment)

        # Send via SMTP
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            if use_tls:
                server.starttls()
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        return {
            "success": True,
            "provider": "smtp",
            "message_id": f"smtp-{datetime.utcnow().timestamp()}",
            "timestamp": datetime.utcnow().isoformat()
        }

    def _send_mock(self, to_email: str, subject: str) -> Dict[str, Any]:
        """Mock email send for testing."""
        logger.info(f"[MOCK] Would send email to {to_email}: {subject}")
        return {
            "success": True,
            "provider": "mock",
            "message_id": f"mock-{datetime.utcnow().timestamp()}",
            "timestamp": datetime.utcnow().isoformat(),
            "note": "Email delivery simulated (no email provider configured)"
        }
