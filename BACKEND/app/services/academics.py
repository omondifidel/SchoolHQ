"""
Academics service logic.

Two responsibilities:
1. record_rubric_entry -- validates a teacher is actually assigned to the
   student's class BEFORE writing (defense-in-depth on top of the
   RESTRICTIVE RLS policy in init.sql -- don't rely on only one layer).
2. generate_report_card -- compiles all of a student's RubricEntry rows
   for a term into a single ReportCard snapshot. Deliberately a plain
   compile step, not a live view -- a report card should reflect what was
   entered as of generation time, not silently change if a rubric entry
   is edited afterwards. Re-generate explicitly if entries change.
"""
import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import Student, teacher_classroom_assignments
from app.models.academics import RubricEntry, ReportCard, LearningArea


class NotAssignedToClassError(Exception):
    """Raised when a teacher tries to record a rubric entry for a student
    outside their assigned classroom(s)."""


async def _teacher_is_assigned_to_student(session: AsyncSession, teacher_id: uuid.UUID, student_id: uuid.UUID) -> bool:
    stmt = (
        select(teacher_classroom_assignments.c.classroom_id)
        .join(Student, Student.classroom_id == teacher_classroom_assignments.c.classroom_id)
        .where(
            teacher_classroom_assignments.c.user_id == teacher_id,
            Student.id == student_id,
        )
    )
    result = (await session.execute(stmt)).first()
    return result is not None


async def record_rubric_entry(
    session: AsyncSession,
    *,
    school_id: uuid.UUID,
    student_id: uuid.UUID,
    learning_area_id: uuid.UUID,
    term: str,
    strand: str | None,
    level: str,
    recorded_by: uuid.UUID,
    recorded_by_role: str,
) -> RubricEntry:
    # RLS already blocks this at the DB level for teachers outside their
    # class, but we check explicitly here too, so a teacher gets a clear
    # 403 with a real error message instead of a confusing empty result
    # or opaque database error.
    if recorded_by_role == "teacher":
        assigned = await _teacher_is_assigned_to_student(session, recorded_by, student_id)
        if not assigned:
            raise NotAssignedToClassError(
                "You are not assigned to this student's class. "
                "Ask a director to update teacher_classroom_assignments if this is wrong."
            )

    entry = RubricEntry(
        id=uuid.uuid4(),
        school_id=school_id,
        student_id=student_id,
        learning_area_id=learning_area_id,
        term=term,
        strand=strand,
        level=level,
        recorded_by=recorded_by,
    )
    session.add(entry)
    await session.flush()
    await session.refresh(entry)
    return entry


async def generate_report_card(
    session: AsyncSession,
    *,
    school_id: uuid.UUID,
    student_id: uuid.UUID,
    term: str,
) -> ReportCard:
    entries_stmt = (
        select(RubricEntry, LearningArea.name)
        .join(LearningArea, LearningArea.id == RubricEntry.learning_area_id)
        .where(
            RubricEntry.school_id == school_id,
            RubricEntry.student_id == student_id,
            RubricEntry.term == term,
        )
    )
    rows = (await session.execute(entries_stmt)).all()

    if not rows:
        raise ValueError(f"No rubric entries found for this student in term {term} -- nothing to compile.")

    compiled: dict[str, list[dict]] = defaultdict(list)
    for entry, learning_area_name in rows:
        compiled[learning_area_name].append({
            "strand": entry.strand,
            "level": entry.level.value if hasattr(entry.level, "value") else entry.level,
        })

    # Overwrite any existing report card for this student+term rather than
    # accumulating duplicates -- generation is idempotent by design.
    existing_stmt = select(ReportCard).where(
        ReportCard.school_id == school_id,
        ReportCard.student_id == student_id,
        ReportCard.term == term,
    )
    existing = (await session.execute(existing_stmt)).scalar_one_or_none()

    if existing:
        existing.compiled_data = dict(compiled)
        await session.flush()
        await session.refresh(existing)
        return existing

    report_card = ReportCard(
        id=uuid.uuid4(),
        school_id=school_id,
        student_id=student_id,
        term=term,
        compiled_data=dict(compiled),
    )
    session.add(report_card)
    await session.flush()
    await session.refresh(report_card)
    return report_card