"""
Comms service logic.

Design: sending SMS is split into two steps, not done inline in a
request handler:
  1. queue_balance_reminders -- fast, synchronous, just writes MessageLog
     rows with status=queued. Safe to call from a route directly.
  2. process_queued_messages -- the slow part (actual HTTP calls to the
     SMS gateway). This runs in the arq background worker (see
     app/worker.py), NOT inline in the request/response cycle, so a slow
     or flaky gateway never makes an API call hang.

Gateway integration below is written for Africa's Talking' shape (a
common Kenyan SMS gateway), since that's what most schools' bulk SMS
budgets already assume. If you use a different provider, this is the
one function to change -- send_sms_via_gateway -- everything else in
this file is provider-agnostic.
"""
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.core import Guardian, student_guardians, Student
from app.models.finance import Invoice, InvoiceStatus
from app.models.comms import MessageLog, MessageStatus, MessageTemplate

AFRICAS_TALKING_SEND_URL = "https://api.africastalking.com/version1/messaging"


def render_template(body: str, *, student_name: str, balance: float, school_name: str) -> str:
    return (
        body.replace("{student_name}", student_name)
        .replace("{balance}", f"KES {balance:,.0f}")
        .replace("{school_name}", school_name)
    )


async def find_outstanding_invoices_with_guardians(session: AsyncSession, school_id: uuid.UUID):
    """
    Returns (invoice, student, guardian) tuples for every invoice with a
    real outstanding balance, joined to that student's primary guardian
    (falling back to any guardian if no primary is flagged).
    """
    stmt = (
        select(Invoice, Student, Guardian)
        .join(Student, Student.id == Invoice.student_id)
        .join(student_guardians, student_guardians.c.student_id == Student.id)
        .join(Guardian, Guardian.id == student_guardians.c.guardian_id)
        .where(
            Invoice.school_id == school_id,
            Invoice.status.in_([InvoiceStatus.UNPAID, InvoiceStatus.PARTIALLY_PAID, InvoiceStatus.OVERDUE]),
        )
        .order_by(student_guardians.c.is_primary_contact.desc())
    )
    rows = (await session.execute(stmt)).all()

    # Collapse to one guardian per invoice (the first row per invoice_id,
    # which thanks to the ORDER BY above will be the primary contact if
    # one exists).
    seen_invoice_ids: set[uuid.UUID] = set()
    deduped = []
    for invoice, student, guardian in rows:
        if invoice.id in seen_invoice_ids:
            continue
        seen_invoice_ids.add(invoice.id)
        deduped.append((invoice, student, guardian))
    return deduped


async def queue_balance_reminders(
    session: AsyncSession,
    *,
    school_id: uuid.UUID,
    school_name: str,
    template: MessageTemplate,
) -> int:
    """Writes one queued MessageLog row per outstanding invoice's guardian.
    Returns the count queued. Does NOT send anything -- that's the
    worker's job (see process_queued_messages below)."""
    rows = await find_outstanding_invoices_with_guardians(session, school_id)

    count = 0
    for invoice, student, guardian in rows:
        outstanding = float(invoice.amount_due) - float(invoice.amount_paid)
        if outstanding <= 0:
            continue

        message_body = render_template(
            template.body,
            student_name=student.full_name,
            balance=outstanding,
            school_name=school_name,
        )
        log_row = MessageLog(
            id=uuid.uuid4(),
            school_id=school_id,
            guardian_id=guardian.id,
            body=message_body,
            trigger_reason="balance_reminder",
            status=MessageStatus.QUEUED,
        )
        session.add(log_row)
        count += 1

    await session.flush()
    return count


async def send_sms_via_gateway(phone_number: str, message: str) -> tuple[bool, str]:
    """
    Sends one SMS via Africa's Talking. Returns (success, provider_detail).

    NOT tested against a live account in this environment (no network
    access when this was written) -- verify the exact request shape
    against Africa's Talking's current docs before relying on this in
    production, especially the sandbox vs. live username/base URL
    differences.
    """
    if not settings.sms_api_key or not settings.sms_username:
        return False, "SMS gateway credentials not configured (check .env)"

    headers = {
        "apiKey": settings.sms_api_key,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }
    data = {
        "username": settings.sms_username,
        "to": phone_number,
        "message": message,
    }
    if settings.sms_sender_id:
        data["from"] = settings.sms_sender_id

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(AFRICAS_TALKING_SEND_URL, headers=headers, data=data)
            response.raise_for_status()
            return True, response.text
    except httpx.HTTPError as exc:
        return False, str(exc)


async def process_queued_messages(session: AsyncSession, school_id: uuid.UUID) -> dict:
    """
    Called by the arq worker (app/worker.py), NOT by a request handler.
    Sends every queued message for a school and updates its status.
    """
    stmt = (
        select(MessageLog, Guardian.phone_number)
        .join(Guardian, Guardian.id == MessageLog.guardian_id)
        .where(MessageLog.school_id == school_id, MessageLog.status == MessageStatus.QUEUED)
    )
    rows = (await session.execute(stmt)).all()

    sent, failed = 0, 0
    for log_row, phone_number in rows:
        success, detail = await send_sms_via_gateway(phone_number, log_row.body)
        log_row.status = MessageStatus.SENT if success else MessageStatus.FAILED
        log_row.sent_at = datetime.now(timezone.utc) if success else None
        sent += int(success)
        failed += int(not success)

    await session.flush()
    return {"sent": sent, "failed": failed, "total": len(rows)}