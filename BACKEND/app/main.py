"""
SchoolHQ API entrypoint.

Run locally via Docker Compose (recommended, matches production shape):
    docker compose up --build

Or directly, if you already have Postgres/Redis running locally:
    uvicorn app.main:app --reload
"""
from fastapi import FastAPI

from app.routes import auth, finance, academics, comms

app = FastAPI(
    title="SchoolHQ API",
    description="Finance, academics, and communications platform for Kenyan schools.",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust to frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(finance.router)
app.include_router(academics.router)
app.include_router(comms.router)


@app.get("/health")
async def health_check():
    """Basic liveness check -- does NOT check DB/Redis connectivity yet.
    Extend this before relying on it for real uptime monitoring."""
    return {"status": "ok"}
