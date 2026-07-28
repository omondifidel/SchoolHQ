"""
Academics routes -- full implementation.

Endpoint summary:
  POST /academics/learning-areas          director defines subjects/strands
  GET  /academics/learning-areas           list them
  POST /academics/rubric-entries          teacher records a rubric score
  GET  /academics/rubric-entries           list (RLS scopes teachers to their classes)
  POST /academics/report-cards/generate    compile a student's term into a report card
  GET  /academics/report-cards             list generated report cards
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_roles, get_current_user, CurrentUser
from app.core.security import Role
from app.middleware.tenant import get_tenant_db
from app.models.academics import LearningArea, RubricEntry, ReportCard
from app.schemas.academics import (
    LearningAreaCreate, LearningAreaOut,
    RubricEntryCreate, RubricEntryOut,
    ReportCardGenerateRequest, ReportCardOut,
)
from app.services.academics import record_rubric_entry, generate_report_card, NotAssignedToClassError

router = APIRouter(prefix="/academics", tags=["academics"])


@router.post("/learning-areas", response_model=LearningAreaOut, status_code=status.HTTP_201_CREATED)
async def create_learning_area(
    payload: LearningAreaCreate,
    db: AsyncSession = Depends(get_tenant_db),
    user: CurrentUser = Depends(require_roles(Role.DIRECTOR)),
):
    area = LearningArea(id=uuid.uuid4(), school_id=user.school_id, name=payload.name)
    db.add(area)
    await db.flush()
    await db.refresh(area)
    return area


@router.get("/learning-areas", response_model=list[LearningAreaOut])
async def list_learning_areas(
    db: AsyncSession = Depends(get_tenant_db),
    user: CurrentUser = Depends(get_current_user),
):
    result = await db.execute(select(LearningArea).order_by(LearningArea.name))
    return result.scalars().all()


@router.post("/rubric-entries", response_model=RubricEntryOut, status_code=status.HTTP_201_CREATED)
async def create_rubric_entry(
    payload: RubricEntryCreate,
    db: AsyncSession = Depends(get_tenant_db),
    user: CurrentUser = Depends(require_roles(Role.TEACHER, Role.DIRECTOR)),
):
    try:
        entry = await record_rubric_entry(
            db,
            school_id=user.school_id,
            student_id=payload.student_id,
            learning_area_id=payload.learning_area_id,
            term=payload.term,
            strand=payload.strand,
            level=payload.level.value,
            recorded_by=user.user_id,
            recorded_by_role=user.role,
        )
    except NotAssignedToClassError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    return entry


@router.get("/rubric-entries", response_model=list[RubricEntryOut])
async def list_rubric_entries(
    student_id: uuid.UUID | None = None,
    term: str | None = None,
    db: AsyncSession = Depends(get_tenant_db),
    user: CurrentUser = Depends(get_current_user),
):
    """
    No manual role-based filtering here beyond the optional query params --
    RLS (including the RESTRICTIVE teacher-class-scope policy in init.sql)
    already ensures a teacher only ever sees rows for their assigned
    classes. That's deliberate: it proves the DB-level enforcement works
    rather than papering over a missing policy with an app-side filter.
    """
    stmt = select(RubricEntry)
    if student_id:
        stmt = stmt.where(RubricEntry.student_id == student_id)
    if term:
        stmt = stmt.where(RubricEntry.term == term)
    result = await db.execute(stmt.order_by(RubricEntry.created_at.desc()))
    return result.scalars().all()


@router.post("/report-cards/generate", response_model=ReportCardOut)
async def generate_report_card_endpoint(
    payload: ReportCardGenerateRequest,
    db: AsyncSession = Depends(get_tenant_db),
    user: CurrentUser = Depends(require_roles(Role.TEACHER, Role.DIRECTOR)),
):
    try:
        report_card = await generate_report_card(
            db, school_id=user.school_id, student_id=payload.student_id, term=payload.term
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return report_card


@router.get("/report-cards", response_model=list[ReportCardOut])
async def list_report_cards(
    student_id: uuid.UUID | None = None,
    term: str | None = None,
    db: AsyncSession = Depends(get_tenant_db),
    user: CurrentUser = Depends(get_current_user),
):
    stmt = select(ReportCard)
    if student_id:
        stmt = stmt.where(ReportCard.student_id == student_id)
    if term:
        stmt = stmt.where(ReportCard.term == term)
    result = await db.execute(stmt.order_by(ReportCard.generated_at.desc()))
    return result.scalars().all()