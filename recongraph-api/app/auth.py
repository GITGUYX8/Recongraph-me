from datetime import datetime, timedelta, timezone
from functools import lru_cache
import hashlib
import hmac
import os
import secrets
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import logging

logger = logging.getLogger("recongraph-api.auth")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 hours

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

_temporary_users: dict[str, dict[str, str]] = {}


class AuthConfigurationError(RuntimeError):
    """Raised when authentication cannot safely operate."""


@lru_cache(maxsize=1)
def _auth_config() -> tuple[str, str, str, str, str]:
    secret_key = os.getenv("RECONGRAPH_AUTH_SECRET_KEY")
    admin_username = os.getenv("RECONGRAPH_DEMO_ADMIN_USERNAME")
    admin_password = os.getenv("RECONGRAPH_DEMO_ADMIN_PASSWORD")
    auditor_username = os.getenv("RECONGRAPH_DEMO_AUDITOR_USERNAME")
    auditor_password = os.getenv("RECONGRAPH_DEMO_AUDITOR_PASSWORD")

    missing = [
        name for name, value in (
            ("RECONGRAPH_AUTH_SECRET_KEY", secret_key),
            ("RECONGRAPH_DEMO_ADMIN_USERNAME", admin_username),
            ("RECONGRAPH_DEMO_ADMIN_PASSWORD", admin_password),
            ("RECONGRAPH_DEMO_AUDITOR_USERNAME", auditor_username),
            ("RECONGRAPH_DEMO_AUDITOR_PASSWORD", auditor_password),
        ) if not value
    ]
    if missing:
        raise AuthConfigurationError(
            "Authentication is not configured. Set: " + ", ".join(missing)
        )
    assert secret_key is not None
    assert admin_username is not None
    assert admin_password is not None
    assert auditor_username is not None
    assert auditor_password is not None
    return secret_key, admin_username, admin_password, auditor_username, auditor_password


def clear_auth_config_cache() -> None:
    """Clear cached settings for tests and controlled configuration reloads."""
    _auth_config.cache_clear()


def clear_temporary_users() -> None:
    """Clear process-local signup accounts for tests and local resets."""
    _temporary_users.clear()


def _password_hash(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16_384, r=8, p=1)


def _store_temporary_user(username: str, password: str, role: str) -> None:
    salt = secrets.token_bytes(16)
    _temporary_users[username] = {
        "role": role,
        "salt": salt.hex(),
        "password_hash": _password_hash(password, salt).hex(),
        "tenant_id": "tenant-001",
    }


def register_temporary_user(username: str, password: str) -> None:
    """Register an auditor until persistent user storage is introduced."""
    _auth_config()
    if username in _temporary_users:
        raise ValueError("Username is already registered")
    _, admin_username, _, auditor_username, _ = _auth_config()
    if username in {admin_username, auditor_username}:
        raise ValueError("Username is already registered")
    _store_temporary_user(username, password, "auditor")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    secret_key = _auth_config()[0]
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        secret_key = _auth_config()[0]
        payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        tenant_id: str = payload.get("tenant_id")
        if username is None or role is None or tenant_id is None:
            raise credentials_exception
        return {"username": username, "role": role, "tenant_id": tenant_id}
    except JWTError:
        raise credentials_exception

async def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

async def require_auditor(current_user: dict = Depends(get_current_user)):
    role = current_user.get("role")
    if role not in ["admin", "auditor"]:
        raise HTTPException(status_code=403, detail="Auditor access required")
    return current_user

async def require_viewer(current_user: dict = Depends(get_current_user)):
    role = current_user.get("role")
    if role not in ["admin", "auditor", "viewer"]:
        raise HTTPException(status_code=403, detail="Viewer access required")
    return current_user


def authenticate_demo_user(username: str, password: str) -> str:
    """Return the configured role for valid demo credentials."""
    _, admin_username, admin_password, auditor_username, auditor_password = _auth_config()
    if hmac.compare_digest(username, admin_username) and hmac.compare_digest(password, admin_password):
        return "admin"
    if hmac.compare_digest(username, auditor_username) and hmac.compare_digest(password, auditor_password):
        return "auditor"
    user = _temporary_users.get(username)
    if user:
        actual = _password_hash(password, bytes.fromhex(user["salt"])).hex()
        if hmac.compare_digest(actual, user["password_hash"]):
            return user["role"]
    raise HTTPException(status_code=401, detail="Incorrect username or password")
