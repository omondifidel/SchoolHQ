"""
Academics module — CBC rubric tracking and report card generation.

This is intentionally a thinner stub than finance.py: build this out once
Finance is live and validated with real schools, per our MVP sequencing.
The shape below is enough to start from, not a finished design.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import String, ForeignKey, DateTime, func, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core import Base, _uuid_pk


class RubricLevel(str, enum.Enum):
    EE = "exceeding_expectation"
    ME = "meeting_expectation"
    AE = "approaching_expectation"
    BE = "below_expectation"


class LearningArea(Base):
    __tablename__ = "learning_areas"

    id: Mapped[uuid.UUID] = _uuid_pk()
    school_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("schools.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "Mathematics", "Environmental Activities"


class RubricEntry(Base):
    __tablename__ = "rubric_entries"

    id: Mapped[uuid.UUID] = _uuid_pk()
    school_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("schools.id"), nullable=False)
    student_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("students.id"), nullable=False)
    learning_area_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("learning_areas.id"), nullable=False)
    term: Mapped[str] = mapped_column(String(20), nullable=False)
    strand: Mapped[str | None] = mapped_column(String(150))
    level: Mapped[RubricLevel] = mapped_column(SAEnum(RubricLevel), nullable=False)
    recorded_by: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReportCard(Base):
    """Compiled snapshot — generated from RubricEntry rows at term end,
    not edited directly, so it stays an honest reflection of the entries."""
    __tablename__ = "report_cards"

    id: Mapped[uuid.UUID] = _uuid_pk()
    school_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("schools.id"), nullable=False)
    student_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("students.id"), nullable=False)
    term: Mapped[str] = mapped_column(String(20), nullable=False)
    compiled_data: Mapped[dict] = mapped_column(JSONB, nullable=False)  # rendered rubric summary per learning area
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())