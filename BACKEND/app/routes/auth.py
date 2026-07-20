import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Import your database session engine (adjust path based on database.py location)
from app.core.database import get_db  
# Import security functions for checking passwords and creating JWTs
from app.core.security import verify_password, create_access_token  
# Import the Data Access Layer (DAL) User model
from app.models.core import User  
# Import the Application Layer Pydantic schemas
from app.schemas.auth import LoginRequest, TokenResponse  

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    payload: LoginRequest, 
    session: AsyncSession = Depends(get_db)
):
    """
    Verifies user credentials and returns an encrypted JWT access token.
    As per MVP strategy, users are created via seed scripts/admin panel.
    """
    # 1. Look up the user by email in the database
    stmt = select(User).where(User.email == payload.email)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    # 2. Guardrail: If user doesn't exist, fail gracefully
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Guardrail: Verify if the submitted text password matches the hashed DB password
    # (Assuming you have a verify_password utility function inside app.core.security)
    is_password_correct = verify_password(payload.password, user.hashed_password)
    if not is_password_correct:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 4. Generate the JWT token payload, embedding the vital multi-tenancy IDs
    token_data = {
        "sub": str(user.id),          # The user's specific ID
        "school_id": str(user.school_id),  # CRITICAL: Embedded tenant boundary!
        "role": user.role.value if hasattr(user.role, "value") else str(user.role)
    }
    
    # Create the token (typically expires in 1 day / 1440 minutes)
    access_token = create_access_token(
        data=token_data, 
        expires_delta=timedelta(days=1)
    )

    # 5. Return the validated response payload matching TokenResponse schema
    return TokenResponse(
        access_token=access_token,
        token_type="bearer"
    )