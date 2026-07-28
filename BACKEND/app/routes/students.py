"""
Students, guardians, and classroom routes -- not one of the three pitched
modules, but core infrastructure every module depends on. You need this
to actually create test data and exercise Finance/Academics/Comms.
"""
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_roles, get_current_user, CurrentUser
from app.core.security import Role
from app.middleware.tenant import get_tenant_db
from app.models.core import ClassRoom, Student, Guardian, student_guardians, teacher_classroom_assignments
from app.schemas.students import (
    ClassRoomCreate, ClassRoomOut,
    StudentCreate, StudentOut,
    GuardianCreate, GuardianOut,
    LinkGuardianRequest, AssignTeacherRequest,
)

router = APIRouter(prefix="/students", tags=["students"])


@router.post("/classrooms", response_model=ClassRoomOut, status_code=status.HTTP_201_CREATED)
async def create_classroom(
    payload: ClassRoomCreate,
    db: AsyncSession = Depends(get_tenant_db),
    user: CurrentUser = Depends(require_roles(Role.DIRECTOR)),
):
    classroom = ClassRoom(id=uuid.uuid4(), school_id=user.school_id, name=payload.name, grade_level=payload.grade_level)
    db.add(classroom)
    await db.flush()
    await db.refresh(classroom)
    return classroom


@router.get("/classrooms", response_model=list[ClassRoomOut])
async def list_classrooms(
    db: AsyncSession = Depends(get_tenant_db),
    user: CurrentUser = Depends(get_current_user),
):
    result = await db.execute(select(ClassRoom).order_by(ClassRoom.name))
    return result.scalars().all()


@router.post("/classrooms/assign-teacher", status_code=status.HTTP_204_NO_CONTENT)
async def assign_teacher_to_classroom(
    payload: AssignTeacherRequest,
    db: AsyncSession = Depends(get_tenant_db),
    user: CurrentUser = Depends(require_roles(Role.DIRECTOR)),
):
    # ON CONFLICT DO NOTHING -- re-assigning the same teacher/classroom
    # pair should be a harmless no-op, not a 500 on a unique constraint.
    stmt = pg_insert(teacher_classroom_assignments).values(
        user_id=payload.user_id, classroom_id=payload.classroom_id
    ).on_conflict_do_nothing()
    await db.execute(stmt)


@router.post("/", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
async def create_student(
    payload: StudentCreate,
    db: AsyncSession = Depends(get_tenant_db),
    user: CurrentUser = Depends(require_roles(Role.DIRECTOR, Role.BURSAR, Role.ADMIN_STAFF)),
):
    student = Student(
        id=uuid.uuid4(),
        school_id=user.school_id,
        full_name=payload.full_name,
        admission_number=payload.admission_number,
        classroom_id=payload.classroom_id,
    )
    db.add(student)
    await db.flush()
    await db.refresh(student)
    return student


@router.get("/", response_model=list[StudentOut])
async def list_students(
    classroom_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_tenant_db),
    user: CurrentUser = Depends(get_current_user),
):
    stmt = select(Student).where(Student.is_active.is_(True))
    if classroom_id:
        stmt = stmt.where(Student.classroom_id == classroom_id)
    result = await db.execute(stmt.order_by(Student.full_name))
    return result.scalars().all()


@router.post("/guardians", response_model=GuardianOut, status_code=status.HTTP_201_CREATED)
async def create_guardian(
    payload: GuardianCreate,
    db: AsyncSession = Depends(get_tenant_db),
    user: CurrentUser = Depends(require_roles(Role.DIRECTOR, Role.BURSAR, Role.ADMIN_STAFF)),
):
    guardian = Guardian(
        id=uuid.uuid4(),
        school_id=user.school_id,
        full_name=payload.full_name,
        phone_number=payload.phone_number,
        relationship_label=payload.relationship_label,
    )
    db.add(guardian)
    await db.flush()
    await db.refresh(guardian)
    return guardian


@router.post("/link-guardian", status_code=status.HTTP_204_NO_CONTENT)
async def link_guardian_to_student(
    payload: LinkGuardianRequest,
    db: AsyncSession = Depends(get_tenant_db),
    user: CurrentUser = Depends(require_roles(Role.DIRECTOR, Role.BURSAR, Role.ADMIN_STAFF)),
):
    """A student can have multiple guardians (mother, father, grandparent)
    and a guardian can have multiple students (siblings) -- see the
    many-to-many table definition in models/core.py."""
    stmt = pg_insert(student_guardians).values(
        student_id=payload.student_id,
        guardian_id=payload.guardian_id,
        is_primary_contact=payload.is_primary_contact,
    ).on_conflict_do_update(
        index_elements=["student_id", "guardian_id"],
        set_={"is_primary_contact": payload.is_primary_contact},
    )
    await db.execute(stmt)