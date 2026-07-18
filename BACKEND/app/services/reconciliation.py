"""
Reconciliation logic — the actual engine behind the "no more manual
M-Pesa matching" pitch.

MVP matching strategy: match on phone number against a guardian's
registered number, then apply the payment to that guardian's student(s)'
oldest unpaid invoice(s) first. This is a reasonable default, not a
perfect one — real schools will have edge cases (a relative paying from
an unregistered number, one payment meant to cover two siblings, etc).
Those unmatched cases are surfaced for manual review, not silently
dropped — that's the whole point of the leakage-visibility pitch.
"""
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import Guardian, student_guardians, Student
from app.models.finance import Transaction, Invoice, PaymentMatch, InvoiceStatus


async def match_transaction(session: AsyncSession, transaction: Transaction) -> list[PaymentMatch]:
    """
    Attempts to match one unmatched Transaction to one or more Invoices.
    Returns the list of PaymentMatch rows created (empty if no match
    found — the transaction stays `matched=False` for manual review).
    """
    guardian_stmt = select(Guardian).where(
        Guardian.school_id == transaction.school_id,
        Guardian.phone_number == transaction.phone_number,
    )
    guardian = (await session.execute(guardian_stmt)).scalar_one_or_none()

    if guardian is None:
        # No registered guardian with this phone number — flag for manual
        # review rather than guessing. This IS the leakage-visibility
        # feature: an admin sees this transaction sitting unmatched.
        return []

    student_ids_stmt = select(student_guardians.c.student_id).where(
        student_guardians.c.guardian_id == guardian.id
    )
    student_ids = [row[0] for row in (await session.execute(student_ids_stmt)).all()]
    if not student_ids:
        return []

    invoices_stmt = (
        select(Invoice)
        .where(
            Invoice.school_id == transaction.school_id,
            Invoice.student_id.in_(student_ids),
            Invoice.status.in_([InvoiceStatus.UNPAID, InvoiceStatus.PARTIALLY_PAID, InvoiceStatus.OVERDUE]),
        )
        .order_by(Invoice.due_date.asc().nulls_last())
    )
    open_invoices = (await session.execute(invoices_stmt)).scalars().all()

    remaining = Decimal(str(transaction.amount))
    matches: list[PaymentMatch] = []

    for invoice in open_invoices:
        if remaining <= 0:
            break
        outstanding = Decimal(str(invoice.amount_due)) - Decimal(str(invoice.amount_paid))
        if outstanding <= 0:
            continue

        applied = min(remaining, outstanding)
        invoice.amount_paid = float(Decimal(str(invoice.amount_paid)) + applied)
        invoice.status = (
            InvoiceStatus.PAID if invoice.amount_paid >= invoice.amount_due else InvoiceStatus.PARTIALLY_PAID
        )
        remaining -= applied

        match = PaymentMatch(
            id=uuid.uuid4(),
            school_id=transaction.school_id,
            transaction_id=transaction.id,
            invoice_id=invoice.id,
            amount_applied=float(applied),
            matched_by="auto",
        )
        session.add(match)
        matches.append(match)

    if matches:
        transaction.matched = True

    # Note: if remaining > 0 after this loop (overpayment / no more open
    # invoices), that balance is currently just left on the transaction.
    # A real v1 should decide explicitly: credit note for next term,
    # or flag for the bursar to review — don't let it silently vanish.
    return matches


async def get_unreconciled_transactions(session: AsyncSession, school_id: uuid.UUID):
    """Surfaces what the pitch calls 'unaccounted for' — payments received
    but not matched to any student invoice. This list IS your leakage
    dashboard's core data source."""
    stmt = select(Transaction).where(
        Transaction.school_id == school_id,
        Transaction.matched.is_(False),
    )
    return (await session.execute(stmt)).scalars().all()