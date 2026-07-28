"""
Comms routes -- full implementation.

Endpoint summary:
  POST /comms/templates                  create a reusable SMS template
  GET  /comms/templates                   list templates
  POST /comms/balance-reminders/send      queue reminders + enqueue background send job
  GET  /comms/message-log                 delivery status view
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_roles, get_current_user, CurrentUser
from app.core.security import Role
from app.core.queue import get_arq_pool
from app.middleware.tenant import get_tenant_db
from app.models.core import School
from app.models.comms import MessageTemplate, MessageLog
from app.schemas.comms import (
    MessageTemplateCreate, MessageTemplateOut,
    BalanceReminderRequest, BalanceReminderResponse,
    MessageLogOut,
)
from app.services.comms import queue_balance_reminders

router = APIRouter(prefix="/comms", tags=["comms"])


@router.post("/templates", response_model=MessageTemplateOut, status_code=status.HTTP_201_CREATED)
async def create_template(
    payload: MessageTemplateCreate,
    db: AsyncSession = Depends(get_tenant_db),
    user: CurrentUser = Depends(require_roles(Role.DIRECTOR, Role.ADMIN_STAFF, Role.BURSAR)),
):
    template = MessageTemplate(id=uuid.uuid4(), school_id=user.school_id, name=payload.name, body=payload.body)
    db.add(template)
    await db.flush()
    await db.refresh(template)
    return template


@router.get("/templates", response_model=list[MessageTemplateOut])
async def list_templates(
    db: AsyncSession = Depends(get_tenant_db),
    user: CurrentUser = Depends(get_current_user),
):
    result = await db.execute(select(MessageTemplate).order_by(MessageTemplate.name))
    return result.scalars().all()


@router.post("/balance-reminders/send", response_model=BalanceReminderResponse)
async def send_balance_reminders(
    payload: BalanceReminderRequest,
    db: AsyncSession = Depends(get_tenant_db),
    user: CurrentUser = Depends(require_roles(Role.BURSAR, Role.DIRECTOR)),
):
    template = await db.get(MessageTemplate, payload.template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    school = await db.get(School, user.school_id)
    school_name = school.name if school else "Your school"

    queued_count = await queue_balance_reminders(
        db, school_id=user.school_id, school_name=school_name, template=template
    )

    if queued_count > 0:
        # Actual sending happens in the background worker, not here --
        # this route returns immediately instead of blocking on however
        # many SMS gateway calls that would take.
        pool = await get_arq_pool()
        await pool.enqueue_job("process_school_message_queue", str(user.school_id))
        detail = f"Queued {queued_count} reminder(s) and started background sending."
    else:
        detail = "No outstanding balances found -- nothing queued."

    return BalanceReminderResponse(queued=queued_count, detail=detail)


@router.get("/message-log", response_model=list[MessageLogOut])
async def list_message_log(
    db: AsyncSession = Depends(get_tenant_db),
    user: CurrentUser = Depends(require_roles(Role.BURSAR, Role.DIRECTOR, Role.ADMIN_STAFF)),
):
    result = await db.execute(select(MessageLog).order_by(MessageLog.created_at.desc()))
    return result.scalars().all()
