import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent / "recongraph-api"))

from app.main import app
from app import auth

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_auth_state(monkeypatch):
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


def _login(username: str, password: str) -> str:
    res = client.post("/token", data={"username": username, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


def test_reconcile_requires_authentication():
    res = client.post("/reconcile", files={"purchases": ("p.csv", b"a", "text/csv"), "gsts": ("g.csv", b"b", "text/csv")})
    assert res.status_code == 401


def test_reconcile_allows_authenticated_auditor():
    token = _login("demo-auditor", "auditor-password")
    res = client.post(
        "/reconcile",
        headers={"Authorization": f"Bearer {token}"},
        files={"purchases": ("p.csv", b"a", "text/csv"), "gsts": ("g.csv", b"b", "text/csv")},
    )
    assert res.status_code == 200
    assert res.json()["run_id"]


def test_reconcile_allows_authenticated_admin():
    token = _login("demo-admin", "correct-password")
    res = client.post(
        "/reconcile",
        headers={"Authorization": f"Bearer {token}"},
        files={"purchases": ("p.csv", b"a", "text/csv"), "gsts": ("g.csv", b"b", "text/csv")},
    )
    assert res.status_code == 200


def test_demo_remains_public_without_token():
    res = client.get("/demo")
    assert res.status_code == 200