"""Focused tests for credential and bearer-token primitives."""
from datetime import datetime, timezone
from app.identity.security import hash_password, verify_password, issue_token, token_digest, opaque_key, session_expiry


def test_argon2_password_hash_verifies_without_exposing_plaintext():
    password = "correct-horse-battery-staple"
    encoded = hash_password(password)
    assert password not in encoded
    assert verify_password(password, encoded)
    assert not verify_password("wrong-password", encoded)


def test_bearer_tokens_are_random_and_only_digests_are_persisted():
    raw_a, digest_a = issue_token()
    raw_b, digest_b = issue_token()
    assert raw_a != raw_b
    assert digest_a == token_digest(raw_a)
    assert raw_a != digest_a
    assert digest_a != digest_b
    assert opaque_key("same") == opaque_key("same")
    assert opaque_key("same") != opaque_key("other")


def test_session_expiry_is_in_the_future():
    assert session_expiry() > datetime.now(timezone.utc)
