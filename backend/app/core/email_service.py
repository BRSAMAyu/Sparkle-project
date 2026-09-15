"""
Email Service (SMTP)
Simple async email sender for password reset and email verification.
"""
from __future__ import annotations

from email.message import EmailMessage

from loguru import logger

from app.config import settings


class EmailService:
    def __init__(self):
        self.enabled = bool(settings.EMAIL_ENABLED)

    async def send_password_reset_email(self, to_email: str, reset_token: str, username: str | None = None) -> bool:
        subject = "重置你的 Sparkle 密码"
        html = self._build_reset_html(reset_token=reset_token, username=username or "")
        return await self._send(to_email, subject, html)

    async def send_verification_email(self, to_email: str, verify_token: str, username: str | None = None) -> bool:
        subject = "验证你的 Sparkle 邮箱"
        html = self._build_verification_html(verify_token=verify_token, username=username or "")
        return await self._send(to_email, subject, html)

    async def _send(self, to_email: str, subject: str, html: str) -> bool:
        if not self.enabled:
            logger.info(f"[EmailService] EMAIL_ENABLED=false, skip send to {to_email} (subject={subject})")
            return False

        if not settings.SMTP_HOST or not settings.EMAIL_FROM:
            logger.warning("[EmailService] SMTP_HOST or EMAIL_FROM not configured")
            return False

        try:
            import aiosmtplib
        except Exception as exc:
            logger.error(f"[EmailService] aiosmtplib import failed: {exc}")
            return False

        message = EmailMessage()
        from_name = settings.EMAIL_FROM_NAME or settings.APP_NAME or "Sparkle"
        message["From"] = f"{from_name} <{settings.EMAIL_FROM}>"
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content("请使用支持 HTML 的邮箱客户端查看此邮件。")
        message.add_alternative(html, subtype="html")

        use_tls = settings.SMTP_PORT == 465
        start_tls = settings.SMTP_PORT == 587
        try:
            client = aiosmtplib.SMTP(
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                use_tls=use_tls,
                start_tls=start_tls,
                timeout=10,
            )
            await client.connect()
            if settings.SMTP_USER:
                await client.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            await client.send_message(message)
            await client.quit()
            logger.info(f"[EmailService] Email sent to {to_email} (subject={subject})")
            return True
        except Exception as exc:
            logger.error(f"[EmailService] Failed to send email to {to_email}: {exc}")
            return False

    def _build_reset_html(self, reset_token: str, username: str) -> str:
        greeting = f"你好，{username}：" if username else "你好："
        return f"""
<html>
  <body style="font-family: Arial, sans-serif; color: #222;">
    <h2>重置你的 Sparkle 密码</h2>
    <p>{greeting}</p>
    <p>我们收到了你的密码重置请求。请使用以下重置码完成密码重置（15 分钟内有效）：</p>
    <p style="font-size: 20px; font-weight: bold; letter-spacing: 1px;">{reset_token}</p>
    <p>如果这不是你的请求，请忽略此邮件。</p>
  </body>
</html>
"""

    def _build_verification_html(self, verify_token: str, username: str) -> str:
        greeting = f"你好，{username}：" if username else "你好："
        return f"""
<html>
  <body style="font-family: Arial, sans-serif; color: #222;">
    <h2>验证你的 Sparkle 邮箱</h2>
    <p>{greeting}</p>
    <p>请使用以下验证码完成邮箱验证（24 小时内有效）：</p>
    <p style="font-size: 20px; font-weight: bold; letter-spacing: 1px;">{verify_token}</p>
    <p>如果这不是你的操作，请忽略此邮件。</p>
  </body>
</html>
"""


email_service = EmailService()
