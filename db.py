import hashlib
from datetime import datetime, timedelta
from typing import Optional, Literal

from sqlalchemy.orm import Session

from models import User, EmailToken


def create_user(sess: Session, email: str, password_hash: Optional[str] = None) -> User:
    u = User(email=email.lower().strip(), password_hash=password_hash, is_verified=False)
    sess.add(u)
    sess.flush()
    return u


def find_user_by_email(sess: Session, email: str) -> Optional[User]:
    return sess.query(User).filter(User.email == email.lower().strip()).one_or_none()


def issue_token(
    sess: Session,
    user: User,
    token_hash: str,
    purpose: Literal["reset", "verify"],
    ttl_minutes: int = 60,
) -> EmailToken:
    now = datetime.utcnow()
    t = EmailToken(
        user_id=user.id,
        token_hash=token_hash,
        type=purpose,
        purpose=purpose,
        created_at=now,
        expires_at=now + timedelta(minutes=ttl_minutes),
        used=False,
    )
    sess.add(t)
    sess.flush()
    return t


def validate_token(sess: Session, token: str, purpose: Literal["reset", "verify"]) -> Optional[EmailToken]:
    now = datetime.utcnow()
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    t = (
        sess.query(EmailToken)
        .filter(
            EmailToken.token_hash == token_hash,
            EmailToken.type == purpose,
        )
        .one_or_none()
    )
    if not t or t.used or t.expires_at < now:
        return None
    return t


def mark_token_used(sess: Session, t: EmailToken) -> None:
    t.used = True
    t.used_at = datetime.utcnow()
    sess.add(t)


def cleanup_tokens(sess: Session) -> int:
    now = datetime.utcnow()
    deleted = sess.query(EmailToken).filter(EmailToken.expires_at <= now).delete()
    sess.commit()
    return deleted
