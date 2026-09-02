import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).parent.parent / "recongraph-api"))

from app import auth


@pytest.fixture(autouse=True)
def reset_auth_cache(monkeypatch):
    monkeypatch.setenv("RECONGRAPH_AUTH_SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("RECONGRAPH_DEMO_ADMIN_USERNAME", "demo-admin")
    monkeypatch.setenv("RECONGRAPH_DEMO_ADMIN_PASSWORD", "correct-password")
    monkeypatch.setenv("RECONGRAPH_DEMO_AUDITOR_USERNAME", "demo-auditor")
    monkeypatch.setenv("RECONGRAPH_DEMO_AUDITOR_PASSWORD", "auditor-password")
    auth.clear_auth_config_cache()
    auth.clear_temporary_users()
    yield
    auth.clear_auth_config_cache()
    auth.clear_temporary_users()


def test_demo_credentials_are_configured_and_role_is_admin():
    assert auth.authenticate_demo_user("demo-admin", "correct-password") == "admin"


def test_invalid_demo_credentials_are_rejected():
    with pytest.raises(HTTPException) as exc_info:
        auth.authenticate_demo_user("demo-admin", "wrong-password")

    assert exc_info.value.status_code == 401


def test_signup_hashes_password_and_creates_auditor():
    auth.register_temporary_user("new-auditor", "new-password")
    assert auth.authenticate_demo_user("new-auditor", "new-password") == "auditor"
    assert auth._temporary_users["new-auditor"]["password_hash"] != "new-password"


def test_duplicate_signup_is_rejected():
    auth.register_temporary_user("new-auditor", "new-password")
    with pytest.raises(ValueError, match="already registered"):
        auth.register_temporary_user("new-auditor", "another-password")


def test_authentication_fails_closed_when_configuration_is_missing(monkeypatch):
    monkeypatch.delenv("RECONGRAPH_AUTH_SECRET_KEY")
    auth.clear_auth_config_cache()

    with pytest.raises(auth.AuthConfigurationError):
        auth.authenticate_demo_user("demo-admin", "correct-password")


def test_tokens_require_the_configured_secret(monkeypatch):
    token = auth.create_access_token({"sub": "demo-admin", "role": "admin", "tenant_id": "tenant-001"})
    assert token

    monkeypatch_secret = "another-secret"
    # A token signed with a different secret must not validate.
    monkeypatch.setenv("RECONGRAPH_AUTH_SECRET_KEY", monkeypatch_secret)
    auth.clear_auth_config_cache()

    with pytest.raises(HTTPException) as exc_info:
        import asyncio
        asyncio.run(auth.get_current_user(token))
    assert exc_info.value.status_code == 401
