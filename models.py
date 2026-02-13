from __future__ import annotations

from datetime import UTC, datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


def utcnow() -> datetime:
    return datetime.now(UTC)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)


class UsageLog(db.Model):
    __tablename__ = "usage_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    char_count = db.Column(db.Integer, nullable=False)
    voice_name = db.Column(db.String(120), nullable=True)
    timestamp = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)


class UserVoicePin(db.Model):
    __tablename__ = "user_voice_pins"
    __table_args__ = (db.UniqueConstraint("user_id", "voice_id", name="uq_user_voice_pin"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    voice_id = db.Column(db.String(120), nullable=False, index=True)
    voice_mode = db.Column(db.String(32), nullable=False, default="standard")
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)


def log_usage(user_id: int, char_count: int, voice_name: str | None = None) -> None:
    """Persist a usage event row for successful synthesis requests."""
    entry = UsageLog(user_id=user_id, char_count=char_count, voice_name=voice_name)
    db.session.add(entry)
    db.session.commit()
