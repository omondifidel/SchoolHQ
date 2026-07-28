import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.academics import RubricLevel


class LearningAreaCreate(BaseModel):
    name: str


class LearningAreaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str


class RubricEntryCreate(BaseModel):
    student_id: uuid.UUID
    learning_area_id: uuid.UUID
    term: str
    strand: str | None = None
    level: RubricLevel


class RubricEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    student_id: uuid.UUID
    learning_area_id: uuid.UUID
    term: str
    strand: str | None
    level: RubricLevel
    recorded_by: uuid.UUID
    created_at: datetime


class ReportCardGenerateRequest(BaseModel):
    student_id: uuid.UUID
    term: str


class ReportCardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    student_id: uuid.UUID
    term: str
    compiled_data: dict
    generated_at: datetime