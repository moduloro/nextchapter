# db.py
import os
from datetime import datetime, timedelta
from typing import Optional, Literal
from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, Index, text
)
from sqlalchemy import inspect
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
# Render / Heroku style URLs sometimes start with postgres://; SQLAlchemy wants postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL or "sqlite:///:memory:", future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True)  # may be None until set
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    phase = Column(String(50), default="explore", nullable=False)

    tokens = relationship("EmailToken", back_populates="user", cascade="all, delete-orphan")


class EmailToken(Base):
    __tablename__ = "email_tokens"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String(255), unique=True, index=True, nullable=False)
    purpose = Column(String(20), nullable=False)  # 'reset' or 'verify'
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="tokens")


Index("ix_email_tokens_active", EmailToken.token, EmailToken.purpose)


def init_db() -> None:
    """Create tables if they don't exist."""
    Base.metadata.create_all(engine)
    _ensure_phase_column()


def _ensure_phase_column():
    insp = inspect(engine)
    cols = [c["name"] for c in insp.get_columns("users")]
    if "phase" not in cols:
        with engine.begin() as conn:
            # Postgres + SQLite compatible syntax
            conn.execute(text("ALTER TABLE users ADD COLUMN phase VARCHAR(50) NOT NULL DEFAULT 'explore'"))


def get_session() -> Session:
    return SessionLocal()


# Convenience helpers we will use in later steps
def create_user(sess: Session, email: str, password_hash: Optional[str] = None) -> User:
    u = User(email=email.lower().strip(), password_hash=password_hash, is_verified=False)
    sess.add(u)
    sess.flush()
    return u


def find_user_by_email(sess: Session, email: str) -> Optional[User]:
    return sess.query(User).filter(User.email == email.lower().strip()).one_or_none()


def issue_token(
    sess: Session, user: User, token: str, purpose: Literal["reset", "verify"], ttl_minutes: int = 60
) -> EmailToken:
    t = EmailToken(
        user_id=user.id,
        token=token,
        purpose=purpose,
        expires_at=datetime.utcnow() + timedelta(minutes=ttl_minutes),
    )
    sess.add(t)
    sess.flush()
    return t


def validate_token(sess: Session, token: str, purpose: Literal["reset", "verify"]) -> Optional[EmailToken]:
    now = datetime.utcnow()
    t = (
        sess.query(EmailToken)
        .filter(EmailToken.token == token, EmailToken.purpose == purpose)
        .one_or_none()
    )
    if not t or t.used_at is not None or t.expires_at < now:
        return None
    return t


def mark_token_used(sess: Session, t: EmailToken) -> None:
    t.used_at = datetime.utcnow()
    sess.add(t)

