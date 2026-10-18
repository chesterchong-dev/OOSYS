"""Exercise SMTP adapter success, authentication and configuration failures."""
from email.message import EmailMessage
import pytest
from pydantic import SecretStr
from app.core.config import Settings
from app.identity import delivery


class FakeSMTP:
    instances = []
    def __init__(self, host, port, timeout):
        self.host, self.port, self.timeout = host, port, timeout
        self.started = self.logged_in = self.sent = False
        self.__class__.instances.append(self)
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def starttls(self): self.started = True
    def login(self, username, password): self.logged_in = (username, password)
    def send_message(self, message): self.sent = message


def test_smtp_delivery_sends_messages_and_authenticates(monkeypatch):
    FakeSMTP.instances.clear()
    monkeypatch.setattr(delivery.smtplib, "SMTP", FakeSMTP)
    settings = Settings(_env_file=None, smtp_host="smtp.example.test", smtp_port=2525,
        smtp_username="mailer", smtp_password=SecretStr("mail-secret"), email_from="noreply@example.test",
        password_reset_url="https://app.example.test/reset?source=email",
        invitation_accept_url="https://app.example.test/accept")
    delivery.send_password_reset(settings, "user@example.test", "raw-reset-token")
    delivery.send_invitation(settings, "user@example.test", "raw-invite-token", "org-123")
    assert len(FakeSMTP.instances) == 2
    first, second = FakeSMTP.instances
    assert first.started and first.logged_in == ("mailer", "mail-secret")
    assert first.sent["To"] == "user@example.test"
    assert "token=raw-reset-token" in first.sent.get_content()
    assert second.sent["Subject"] == "OOSYS organisation invitation"
    assert "org-123" in second.sent.get_content()


def test_smtp_delivery_rejects_missing_configuration_and_credentials(monkeypatch):
    monkeypatch.setattr(delivery.smtplib, "SMTP", FakeSMTP)
    with pytest.raises(RuntimeError):
        delivery.send_password_reset(Settings(_env_file=None), "user@example.test", "token")
    settings = Settings(_env_file=None, smtp_host="smtp.example.test", email_from="noreply@example.test",
        smtp_username="mailer", password_reset_url="https://app.example.test/reset")
    with pytest.raises(RuntimeError):
        delivery.send_password_reset(settings, "user@example.test", "token")
    with pytest.raises(RuntimeError):
        delivery.send_invitation(settings, "user@example.test", "token", "org")
