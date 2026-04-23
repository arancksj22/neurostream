import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base
from .utils import utc_now


def _uuid_str() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column("password_hash", String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="USER", nullable=False)
    created_at: Mapped[datetime] = mapped_column("created_at", DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column("updated_at", DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    user_id: Mapped[str] = mapped_column("user_id", String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    object_key: Mapped[str] = mapped_column("object_key", String(1024), nullable=False)
    file_name: Mapped[str] = mapped_column("file_name", String(255), nullable=False)
    file_size: Mapped[int] = mapped_column("file_size", BigInteger, nullable=False)
    content_type: Mapped[str] = mapped_column("content_type", String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True, nullable=False)
    duration: Mapped[float | None] = mapped_column(Float)
    thumbnail_key: Mapped[str | None] = mapped_column("thumbnail_key", String(1024))
    created_at: Mapped[datetime] = mapped_column("created_at", DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column("updated_at", DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    deleted_at: Mapped[datetime | None] = mapped_column("deleted_at", DateTime(timezone=True))


class WorkflowStatusLog(Base):
    __tablename__ = "workflow_status_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    video_id: Mapped[str] = mapped_column("video_id", String(36), ForeignKey("videos.id", ondelete="CASCADE"), index=True)
    service_name: Mapped[str] = mapped_column("service_name", String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column("created_at", DateTime(timezone=True), default=utc_now)

class CallbackEvent(Base):
    __tablename__ = "callback_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    video_id: Mapped[str] = mapped_column("video_id", String(36), ForeignKey("videos.id", ondelete="CASCADE"), index=True)
    service_name: Mapped[str] = mapped_column("service_name", String(120), nullable=False)
    event_type: Mapped[str] = mapped_column("event_type", String(60), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB)
    received_at: Mapped[datetime] = mapped_column("received_at", DateTime(timezone=True), default=utc_now)


class DeletedVideoCleanupLog(Base):
    __tablename__ = "deleted_video_cleanup_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    video_id: Mapped[str] = mapped_column("video_id", String(36), ForeignKey("videos.id", ondelete="CASCADE"), index=True)
    object_key: Mapped[str] = mapped_column("object_key", String(1024), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column("created_at", DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column("updated_at", DateTime(timezone=True), default=utc_now, onupdate=utc_now)
