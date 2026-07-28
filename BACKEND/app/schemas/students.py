import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ClassRoomCreate(BaseModel):
    name: str
    grade_level: str | None = None


class ClassRoomOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    grade_level: str | None


class StudentCreate(BaseModel):
    full_name: str
    admission_number: str
    classroom_id: uuid.UUID | None = None


class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    full_name: str
    admission_number: str
    classroom_id: uuid.UUID | None
    is_active: bool
    created_at: datetime


class GuardianCreate(BaseModel):
    full_name: str
    phone_number: str  # E.164 format, e.g. +2547XXXXXXXX
    relationship_label: str | None = None


class GuardianOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    full_name: str
    phone_number: str
    relationship_label: str | None


class LinkGuardianRequest(BaseModel):
    student_id: uuid.UUID
    guardian_id: uuid.UUID
    is_primary_contact: bool = False


class AssignTeacherRequest(BaseModel):
    user_id: uuid.UUID
    classroom_id: uuid.UUID