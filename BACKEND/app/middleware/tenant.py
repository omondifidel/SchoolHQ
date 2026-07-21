"""
Tenant isolation gate.

This is the single most important file in the codebase from a security
standpoint: every authenticated request passes through get_tenant_db,
which opens a transaction and sets three Postgres session variables
(app.current_school_id, app.current_role, app.current_user_id) that the
RLS policies in init.sql read to decide what a query can see or write.

If you ever add a new tenant-scoped table, you MUST add a matching RLS
policy in init.sql referencing these same session variables — this file
sets the context, init.sql enforces it. Neither half works alone.
"""
from contextlib import asynccontextmanager
from typing import AsyncIterator
from uuid import UUID

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal
from app.core.deps import get_current_user, CurrentUser


@asynccontextmanager
async def tenant_scoped_session(
    school_id: UUID | None,
    role: str | None,
    user_id: UUID | None,
) -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        async with session.begin():
            # SET LOCAL scopes each variable to this transaction only, so
            # it can never leak across requests sharing a pooled connection.
            await session.execute(text("SET LOCAL app.current_school_id = :sid"),
                                   {"sid": str(school_id) if school_id else ""})
            await session.execute(text("SET LOCAL app.current_role = :role"),
                                   {"role": role or ""})
            await session.execute(text("SET LOCAL app.current_user_id = :uid"),
                                   {"uid": str(user_id) if user_id else ""})
            yield session
        # commits on clean exit / rolls back automatically on exception


async def get_tenant_db(user: CurrentUser = Depends(get_current_user)) -> AsyncIterator[AsyncSession]:
    """
    The dependency routes should use for any tenant-scoped query:

        @router.get("/invoices")
        async def list_invoices(db: AsyncSession = Depends(get_tenant_db)):
            ...

    Every query run on this session is automatically filtered by Postgres
    RLS to the caller's school (and further restricted by role-specific
    policies, e.g. teachers only seeing their assigned classes).
    """
    async with tenant_scoped_session(school_id=user.school_id, role=user.role, user_id=user.user_id) as session:
        yield session