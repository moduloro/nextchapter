import os
from typing import Optional, Literal
from werkzeug.security import generate_password_hash
from db import get_session, validate_token, mark_token_used
from db import SessionLocal  # if you prefer direct sessions
from db import User  # for lookups/updates

def validate_reset_token(token: str) -> Optional[dict]:
    """
    Look up a reset token in the DB and return a user dict {user_id, email}
    if valid (exists, not used, not expired). Return None if invalid.
    In DEV (or no DATABASE_URL), accept any non-empty token and return a fake user.
    """
    token = (token or "").strip()
    if not token:
        return None

    # DEV fallback
    if os.getenv("ENV", "development").lower() == "development" and not os.getenv("DATABASE_URL"):
        return {"user_id": 1, "email": "support@coro.biz"}

    sess = get_session()
    try:
        t = validate_token(sess, token, "reset")
        if not t:
            return None
        return {"user_id": t.user.id, "email": t.user.email}
    finally:
        sess.close()

def hash_password(plain: str) -> str:
    return generate_password_hash(plain)

def set_user_password(user_id: int, password_hash: str) -> None:
    """
    Update users.password_hash in the DB.
    In DEV (or no DB), log only.
    """
    if os.getenv("ENV", "development").lower() == "development" and not os.getenv("DATABASE_URL"):
        print(f"[DEV] set_user_password(user_id={user_id}, hash={password_hash[:12]}...)")
        return

    sess = get_session()
    try:
        u = sess.get(User, user_id)
        if not u:
            raise ValueError("User not found")
        u.password_hash = password_hash
        sess.add(u)
        sess.commit()
    finally:
        sess.close()


def validate_verification_token(token: str) -> Optional[dict]:
    """
    DB-backed verification token check (see validate_reset_token for details).
    """
    token = (token or "").strip()
    if not token:
        return None

    if os.getenv("ENV", "development").lower() == "development" and not os.getenv("DATABASE_URL"):
        return {"user_id": 1, "email": "support@coro.biz"}

    sess = get_session()
    try:
        t = validate_token(sess, token, "verify")
        if not t:
            return None
        return {"user_id": t.user.id, "email": t.user.email}
    finally:
        sess.close()


def mark_user_verified(user_id: int) -> None:
    """
    Set users.is_verified = True in the DB.
    In DEV (or no DB), log only.
    """
    if os.getenv("ENV", "development").lower() == "development" and not os.getenv("DATABASE_URL"):
        print(f"[DEV] mark_user_verified(user_id={user_id})")
        return

    sess = get_session()
    try:
        u = sess.get(User, user_id)
        if not u:
            raise ValueError("User not found")
        u.is_verified = True
        sess.add(u)
        sess.commit()
    finally:
        sess.close()


def consume_token(token: str, purpose: Literal["reset","verify"]) -> None:
    """
    Mark a token as used in the DB (no-op in DEV without DB).
    """
    if os.getenv("ENV", "development").lower() == "development" and not os.getenv("DATABASE_URL"):
        print(f"[DEV] consume_token({purpose}): {token[:8]}...")
        return

    sess = get_session()
    try:
        t = validate_token(sess, token, purpose)
        if t:
            mark_token_used(sess, t)
            sess.commit()
    finally:
        sess.close()
