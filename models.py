from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    text,
)
from sqlalchemy.orm import declarative_base, relationship
import datetime


Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=True)
    is_verified = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.datetime.utcnow)
    phase = Column(String, nullable=False, default="explore")

class EmailToken(Base):
    __tablename__ = "email_tokens"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String, nullable=False)
    type = Column(String, nullable=False)  # 'reset' or 'verify'
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, nullable=False, default=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    user = relationship("User")


Index("idx_email_tokens_hash", EmailToken.token_hash)
Index("idx_email_tokens_user_type_used", EmailToken.user_id, EmailToken.type, EmailToken.used)


def create_tables(engine):
    """Create users and email_tokens tables if they do not exist."""
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT,
                    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    phase TEXT NOT NULL DEFAULT 'explore'
                );
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS email_tokens (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    token_hash TEXT NOT NULL,
                    type TEXT NOT NULL CHECK (type IN ('reset','verify')),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    expires_at TIMESTAMPTZ NOT NULL,
                    used BOOLEAN NOT NULL DEFAULT FALSE,
                    used_at TIMESTAMPTZ NULL
                );
                """
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_email_tokens_hash ON email_tokens(token_hash);"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_email_tokens_user_type_used ON email_tokens(user_id, type, used);"
            )
        )


def safe_migrate(engine):
    """Perform idempotent schema migrations for email_tokens."""
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE email_tokens DROP COLUMN IF EXISTS token;"))
        conn.execute(text("ALTER TABLE email_tokens ALTER COLUMN token_hash SET NOT NULL;"))
        conn.execute(
            text(
                """
                DO $$ BEGIN
                BEGIN
                    ALTER TABLE email_tokens ADD COLUMN used_at TIMESTAMPTZ NULL;
                EXCEPTION WHEN duplicate_column THEN
                    -- ignore
                END;
                END $$;
                """
            )
        )
