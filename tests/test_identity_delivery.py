"""Unit tests for configured SMTP delivery and safe failure paths."""
from pydantic import SecretStr
import pytest
from app.core.config import Settings
from app.identity import delivery


def test_smtp_delivery_sends_reset_and_invitation(monkeypatch):
    sent = []
    class FakeSMTP:
        def __init__(self, host, port, timeout):
            assert (host, port, timeout) == ("smtp.example.test", 587, 10)
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def starttls(self): sent.append("tls")
        def login(self, username, password): sent.append(("login", username, password))
        def send_message(self, message): sent.append((message["To"], message["Subject"], message.get_content()))
    monkeypatch.setattr(delivery.smtplib, "SMTP", FakeSMTP)
    settings = Settings(_env_file=None, smtp_host="smtp.example.test", smtp_port=587,
        smtp_username="mailer", smtp_password=SecretStr("smtp-secret"), email_from="noreply@example.test",
        password_reset_url="https://app.example.test/reset", invitation_accept_url="https://app.example.test/invite")
    delivery.send_password_reset(settings, "user@example.test", "reset-token")
    delivery.send_invitation(settings, "user@example.test", "invite-token", "org-123")
    assert sent.count("tls") == 2
    assert ("login", "mailer", "smtp-secret") in sent
    messages = [item for item in sent if isinstance(item, tuple) and len(item) == 3 and item[0] == "user@example.test"]
    assert len(messages) == 2
    assert "reset-token" in messages[0][2] and "invite-token" in messages[1][2]


def test_smtp_delivery_rejects_missing_configuration():
    with pytest.raises(RuntimeError, match="SMTP delivery is not configured"):
        delivery._send(Settings(_env_file=None), "user@example.test", "Subject", "Body")
    settings = Settings(_env_file=None, smtp_host="smtp.example.test", email_from="noreply@example.test",
        smtp_username="mailer", smtp_password=None)
    class FakeSMTP:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def starttls(self): pass
    original = delivery.smtplib.SMTP
    delivery.smtplib.SMTP = FakeSMTP
    try:
        with pytest.raises(RuntimeError, match="SMTP password is required"):
            delivery._send(settings, "user@example.test", "Subject", "Body")
    finally:
        delivery.smtplib.SMTP = original


def test_reset_and_invitation_require_frontend_urls():
    settings = Settings(_env_file=None, smtp_host="smtp.example.test", email_from="noreply@example.test")
    with pytest.raises(RuntimeError, match="Password reset URL"):
        delivery.send_password_reset(settings, "user@example.test", "token")
    with pytest.raises(RuntimeError, match="Invitation URL"):
        delivery.send_invitation(settings, "user@example.test", "token", "org-123")
