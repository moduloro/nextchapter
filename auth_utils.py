import os
from typing import Optional
from werkzeug.security import generate_password_hash

def validate_reset_token(token: str) -> Optional[dict]:
    """
    Return a dict with user info (at least user_id and email) if token is valid.
    Return None if invalid/expired.
    DEV MODE: accept any non-empty token and map to a fake user.
    """
    token = (token or "").strip()
    if not token:
        return None
    if os.getenv("ENV", "development").lower() == "development":
        # Dev-only fake user; replace with real lookup later
        return {"user_id": 1, "email": "support@coro.biz"}
    # TODO: implement real token lookup/expiry
    return None

def hash_password(plain: str) -> str:
    """Hash a password with werkzeug (PBKDF2)."""
    return generate_password_hash(plain)

def set_user_password(user_id: int, password_hash: str) -> None:
    """
    Persist the new password hash for the user in your data store.
    DEV MODE: no-op (just print to logs). Replace with real DB write later.
    """
    # TODO: implement DB update
    print(f"[DEV] set_user_password(user_id={user_id}, hash={password_hash[:12]}...)")


def validate_verification_token(token: str) -> Optional[dict]:
    """
    Return a dict with user info (at least user_id and email) if token is valid,
    else None. DEV MODE: accept any non-empty token and map to a fake user.
    """
    token = (token or "").strip()
    if not token:
        return None
    if os.getenv("ENV", "development").lower() == "development":
        return {"user_id": 1, "email": "support@coro.biz"}
    # TODO: implement real verification token lookup and expiry
    return None


def mark_user_verified(user_id: int) -> None:
    """
    Persist 'email verified' for the user in your data store.
    DEV MODE: no-op (just print). Replace with real DB write later.
    """
    # TODO: implement DB update to mark verified_at / is_verified
    print(f"[DEV] mark_user_verified(user_id={user_id})")
