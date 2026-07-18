"""
Finance module — the flagship pitch: fee invoicing, M-Pesa transaction
capture, and automated reconciliation.

Schema is deliberately generalized to multiple revenue categories
(tuition, uniforms, feeding programme, transport, etc.) from day one —
per our discussion, this is cheap to build in now and avoids a painful
migration later, even though the MVP pitch/launch only surfaces tuition.
"""
import enum
import uuid
from datetime import datetime, date

from sqlalchemy import String, ForeignKey, DateTime, Numeric, Date, func, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core import Base, _uuid_pk


class RevenueCategory(str, enum.Enum):
    TUITION = "tuition"
    UNIFORM = "uniform"
    FEEDING_PROGRAMME = "feeding_programme"
    TRANSPORT = "transport"
    OTHER = "other"


class InvoiceStatus(str, enum.Enum):
    UNPAID = "unpaid"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    OVERDUE = "overdue"


class FeeStructure(Base):
    """The expected charge per category per term, per class/grade level."""
    __tablename__ = "fee_structures"

    id: Mapped[uuid.UUID] = _uuid_pk()
    school_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("schools.id"), nullable=False)
    grade_level: Mapped[str | None] = mapped_column(String(50))
    category: Mapped[RevenueCategory] = mapped_column(SAEnum(RevenueCategory), nullable=False)
    term: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g. "2026-T2"
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)


class Invoice(Base):
    """What a specific student owes for a specific category + term."""
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = _uuid_pk()
    school_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("schools.id"), nullable=False)
    student_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("students.id"), nullable=False)
    category: Mapped[RevenueCategory] = mapped_column(SAEnum(RevenueCategory), nullable=False)
    term: Mapped[str] = mapped_column(String(20), nullable=False)
    amount_due: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    amount_paid: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    status: Mapped[InvoiceStatus] = mapped_column(SAEnum(InvoiceStatus), default=InvoiceStatus.UNPAID)
    due_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Transaction(Base):
    """
    Raw M-Pesa payment as received from the Daraja API callback — stored
    exactly as received, BEFORE any matching logic runs. Keeping the raw
    record separate from the matched result means you can always re-run
    reconciliation later without losing the source data, and it gives you
    an audit trail if a parent disputes a payment.
    """
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    school_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("schools.id"), nullable=False)
    mpesa_receipt_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # full Daraja callback, for audit
    matched: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PaymentMatch(Base):
    """
    Links a raw Transaction to the Invoice(s) it pays off. This table is
    where your 'leakage visibility' actually lives: any Transaction with
    no PaymentMatch row is an unreconciled payment, and any Invoice that's
    overdue with no matching Transaction is a real, chased-down arrear —
    not a guess.
    """
    __tablename__ = "payment_matches"

    id: Mapped[uuid.UUID] = _uuid_pk()
    school_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("schools.id"), nullable=False)
    transaction_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False)
    invoice_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False)
    amount_applied: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    matched_by: Mapped[str] = mapped_column(String(20), default="auto")  # "auto" or "manual"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())