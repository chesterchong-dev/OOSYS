"""SMTP adapter for credential recovery and organisation invitations."""
import smtplib
from email.message import EmailMessage
from urllib.parse import urlencode
from app.core.config import Settings


def _send(settings: Settings, recipient: str, subject: str, body: str) -> None:
    if not settings.smtp_host or not settings.email_from:
        raise RuntimeError("SMTP delivery is not configured")
    message = EmailMessage()
    message["From"], message["To"], message["Subject"] = settings.email_from, recipient, subject
    message.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as client:
        client.starttls()
        if settings.smtp_username:
            if not settings.smtp_password:
                raise RuntimeError("SMTP password is required when SMTP username is configured")
            client.login(settings.smtp_username, settings.smtp_password.get_secret_value())
        client.send_message(message)


def send_password_reset(settings: Settings, recipient: str, token: str) -> None:
    if not settings.password_reset_url:
        raise RuntimeError("Password reset URL is not configured")
    sep = "&" if "?" in settings.password_reset_url else "?"
    link = settings.password_reset_url + sep + urlencode({"token": token})
    _send(settings, recipient, "OOSYS password reset",
        f"Use this one-time link within 30 minutes to reset your password:\n{link}\n\nIgnore this message if you did not request it.")


def send_invitation(settings: Settings, recipient: str, token: str, organization_id: str) -> None:
    if not settings.invitation_accept_url:
        raise RuntimeError("Invitation URL is not configured")
    sep = "&" if "?" in settings.invitation_accept_url else "?"
    link = settings.invitation_accept_url + sep + urlencode({"token": token})
    _send(settings, recipient, "OOSYS organisation invitation",
        f"You have been invited to join an OOSYS organisation. Sign in with this email and accept within 7 days:\n{link}\n\nOrganisation reference: {organization_id}")
