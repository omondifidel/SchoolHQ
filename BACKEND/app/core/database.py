"""
    Database engine and session management / Factory for the application
    Tenant-scopped session logic ( setting for RLS context variables ) livs in app/middlewares/tenant.py , not here
    This file is literally "dump plumbing code" , so its obvious where to look for the security critical part
"""

from sqlalchemy.ext.asyncio import AsyncSesssion , create_async_engine , async_sessionmaker

from app.core.config import settings

create_async_engine = create_async_engine(settings.DATABASE_URL , echo=True , pool_pre_ping=True) #this is the engine that will be used to connect to the database

SessionLocal = async_sessionmaker(engine , expire_on_commit=False ,class_ = AsyncSession) #this is the session factory that will be used to create sessions for the database