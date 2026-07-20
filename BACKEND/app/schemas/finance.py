import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.finance import RevenueCategory, InvoiceStatus


class InvoiceCreate(BaseModel):
    student_id: uuid.UUID
    category: RevenueCategory
    term: str
    amount_due: float
    due_date: date | None = None


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    category: RevenueCategory
    term: str
    amount_due: float
    amount_paid: float
    status: InvoiceStatus
    due_date: date | None
    created_at: datetime


class DarajaCallback(BaseModel):
    """
    Minimal shape of a Safaricom Daraja C2B/STK confirmation callback.
    Adjust field names to match the actual payload once you're wired up
    to a real Paybill/Till in the Safaricom developer portal — the
    sandbox and production payload shapes should match, but always
    verify against Safaricom's current docs before going live.
    """
    TransID: str
    TransAmount: float
    MSISDN: str  # payer phone number
    TransTime: str  # format: YYYYMMDDHHmmss


class UnreconciledTransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    mpesa_receipt_number: str
    phone_number: str
    amount: float
    paid_at: datetime