""" 
    Authentication related FASTAPI dependencies: extracting and validating the current user from JWT token in the request header
    Tenant_scoped DB Acess (get_tenant_db) resides inside app/middlewares/tenant.py because it is a middleware and not a dependency
    which in itself depends on the get_current_user dependency to extract the user from the JWT token and set the RLS context variables in the database session
"""

from uuid import UUID
from fastapi import Depends , HTTPException , status
from fastapi.security import OAuth2PasswordBearer

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
    from app.core.security import verify_access_token

    try:
        payload = verify_access_token(token)
        user_id = UUID(payload.sub)
        school_id = payload.school_id
        role = payload.role
        return CurrentUser(user_id=user_id, school_id=school_id, role=role)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    