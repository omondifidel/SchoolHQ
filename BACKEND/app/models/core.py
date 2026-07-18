"""
Core tenant, identity, and student/guardian models — shared by all three
modules (finance, academics, comms).

Every tenant-scoped table carries school_id and relies on the RLS policy
defined in migrations/001_initial_schema.sql to enforce isolation. Adding
a new tenant-scoped table later? Add school_id, then add a matching
RLS policy in a new migration — don't forget the second half.
"""
import uuid
from datetime import datetime

from sqlalchemy import String, ForeignKey, DateTime, func, Boolean, Table, Column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase


class Base(DeclarativeBase):
    pass


def _uuid_pk():
    return mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class School(Base):
    """The tenant root. Every other tenant-scoped row points back here."""
    __tablename__ = "schools"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    county: Mapped[str | None] = mapped_column(String(100))
    curriculum: Mapped[str] = mapped_column(String(20), default="CBC")  # CBC / 8-4-4 / IGCSE

    # Per-school customization without touching code — e.g.
    # {"modules_enabled": ["finance", "comms"], "sms_sender_name": "Green Valley School",
    #  "report_card_template": "standard"}
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ClassRoom(Base):
    """A class/stream, e.g. 'Grade 7 Blue'. Used for teacher scoping."""
    __tablename__ = "classrooms"

    id: Mapped[uuid.UUID] = _uuid_pk()
    school_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("schools.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    grade_level: Mapped[str | None] = mapped_column(String(50))


class User(Base):
    """Staff account: director, bursar, teacher, admin_staff."""
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _uuid_pk()
    school_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("schools.id"))
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False)  # see Role enum in core/security.py
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# A teacher can be assigned to more than one class; a class can have more
# than one teacher (e.g. subject teachers). Plain many-to-many.
teacher_classroom_assignments = Table(
    "teacher_classroom_assignments",
    Base.metadata,
    Column("user_id", PG_UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True),
    Column("classroom_id", PG_UUID(as_uuid=True), ForeignKey("classrooms.id"), primary_key=True),
)


class Student(Base):
    __tablename__ = "students"

    id: Mapped[uuid.UUID] = _uuid_pk()
    school_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("schools.id"), nullable=False)
    classroom_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("classrooms.id"))
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    admission_number: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Guardian(Base):
    """A parent/guardian contact. Deliberately NOT school-scoped alone —
    a guardian could in theory have children at more than one school —
    but we still carry school_id for simple RLS scoping since in practice
    almost all guardians relate to one school. Revisit if that changes."""
    __tablename__ = "guardians"

    id: Mapped[uuid.UUID] = _uuid_pk()
    school_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("schools.id"), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)  # E.164 format, e.g. +2547...
    relationship_label: Mapped[str | None] = mapped_column(String(50))  # "Mother", "Guardian", "Grandparent"


# Many-to-many: a student can have multiple guardians (mother, father,
# grandparent), and one guardian can have multiple students (siblings).
student_guardians = Table(
    "student_guardians",
    Base.metadata,
    Column("student_id", PG_UUID(as_uuid=True), ForeignKey("students.id"), primary_key=True),
    Column("guardian_id", PG_UUID(as_uuid=True), ForeignKey("guardians.id"), primary_key=True),
    Column("is_primary_contact", Boolean, default=False),
)