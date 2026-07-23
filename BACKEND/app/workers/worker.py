"""
Background worker process -- run this as a SEPARATE process from the API
(this is the one deliberate exception to "modular monolith, not
microservices" we discussed: request-handling and background work should
be separate deployables sharing one codebase, not separate services).

Run locally:
    arq app.worker.WorkerSettings

In Docker Compose, add a second service using the same image as `api`
but with this as its command instead of uvicorn -- not added to
compose.yaml yet, since you don't need it until Comms is actually being
used; see README for the note on this.
"""
import uuid

from arq.connections import RedisSettings

from app.core.config import settings
from app.middleware.tenant import tenant_scoped_session
from app.services.comms import process_queued_messages


async def process_school_message_queue(ctx, school_id: str) -> dict:
    """
    The actual background job. Runs OUTSIDE any HTTP request, so there's
    no authenticated user to pull school_id/role from -- instead we open
    a session explicitly as 'super_admin' (bypasses RLS entirely, same
    mechanism the platform-ops role uses) and pass the school_id given to
    us directly. This is safe ONLY because school_id here always comes
    from a MessageLog row already written by an authenticated bursar/
    director request (see routes/comms.py) -- never from unvalidated
    external input.
    """
    async with tenant_scoped_session(school_id=uuid.UUID(school_id), role="super_admin", user_id=None) as session:
        result = await process_queued_messages(session, school_id=uuid.UUID(school_id))
        return result


class WorkerSettings:
    functions = [process_school_message_queue]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)