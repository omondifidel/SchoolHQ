"""
Communications module — targeted SMS to guardians with an actual
outstanding balance, or other trigger events.

Stub, same reasoning as academics.py — build out once Finance has proven
itself with real schools.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import String, ForeignKey, DateTime, Text, func, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core import Base, _uuid_pk


class MessageStatus(str, enum.Enum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"


class MessageTemplate(Base):
    __tablename__ = "message_templates"

    id: Mapped[uuid.UUID] = _uuid_pk()
    school_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("schools.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "Balance reminder"
    body: Mapped[str] = mapped_column(Text, nullable=False)  # supports {student_name}, {balance}, {school_name}


class MessageLog(Base):
    __tablename__ = "message_log"

    id: Mapped[uuid.UUID] = _uuid_pk()
    school_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("schools.id"), nullable=False)
    guardian_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("guardians.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    trigger_reason: Mapped[str | None] = mapped_column(String(100))  # e.g. "balance_reminder", "manual"
    status: Mapped[MessageStatus] = mapped_column(SAEnum(MessageStatus), default=MessageStatus.QUEUED)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())