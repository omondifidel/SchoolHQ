""" 
    Authentication related FASTAPI dependencies: extracting and validating the current user from JWT token in the request header
    Tenant_scoped DB Acess (get_tenant_db) resides inside app/middlewares/tenant.py because it is a middleware and not a dependency
    which in itself depends on the get_current_user dependency to extract the user from the JWT token and set the RLS context variables in the database session
"""

from uuid import UUID

from fastapi import Depends , HTTPException , status
from fastapi.security import OAuth2PasswordBearer

from app.core.security import decode_access_token , TokenPayload

#standard Gatekeeper setup

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login") #built in FastAPI dependancy that instructs FastAPI to look for a specila header in the incoming request which contain our JWT Keycard

#packing credentials after decoding the JWT token into a single object that can be used in the rest of the app

class CurrentUser:
    def __init__(self , user_id: UUID , school_id: str | None , role: str):
        self.user_id = user_id
        self.school_id = school_id
        self.role = role

# Grabbing and Decoding the cards from the request header and returning a CurrentUser object that can be used in the rest of the app

async def get_current_user(token: str = Depends(oauth2_scheme)) -> CurrentUser:
    try:
        payload = decode_access_token(token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return CurrrentUser(
        user_id=UUID(payload.sub),
        school_id=UUID(payload.school_id) if payload.school_id else None,
        role=payload.role,
    )
def require_roles(*allowed: Role):
    """
    Route-level guard, e.g.:
        @router.post("/invoices")
        async def create_invoice(..., user=Depends(require_roles(Role.BURSAR, Role.DIRECTOR))):
 
    This is a SECOND layer on top of RLS, not a replacement for it -- RLS
    protects the data even if a route guard is ever misconfigured; this
    guard gives a clean 403 instead of an empty/confusing result.
    """
    async def checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in {r.value for r in allowed}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted for this role")
        return user
 
    return checker