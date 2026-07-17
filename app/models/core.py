""" 
    Core tenant , identity and student/guardian models  - shared by all three modules ( finance , academics and comms)
    Every tenant scoped table carries school_id and relies on the RLS policy defined in migrations/001 initial_schema.sql
    to enforce isolation. 
    Adding a new tenant-scoped table later ? add school_id , then add a matching RLS policy in a new migration- dont forget
    the second half
"""
import uuid
from datetime import datetime

from sqlalchemy import String , ForeignKey , DateTime , func , Boolean , Table , Column

from sqlalchemy.dialects.postgresql import UUID as PG_UUID , JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship , DeclarativeBase
