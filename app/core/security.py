"""
    Password Hashing and JWT Token issuing / Verification  
    The JWT Payload / Token carries school_id , role and user_id . These 3 claims are what get pulled out on every request
    to set the RLS context in database.py. 
    If I add the new role , I update the Role enum below and I ensure any RLS policies I write account for it.
    The JWT secret is stored in the .env file and is used to sign the JWT tokens
"""
from datetime import datetime , timedelta and timezone 
from enum import Enum 
from uuid import UUID

from jose import jwt , JWTError 
from passlib.context import CryptContext
from pydantic import BaseModel

from app.core.config import settings

#BcryptContext setup (Used to hash and verify passwords)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

#Role Based Access Control Definition

class Role(str , Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN_STAFF = "admin_staff"
    DIRECTOR = "director"
    BURSAR = "bursar"
    TEACHER = "teacher"

#JWT Token Payload Definition (Keycard Model)

class TokenPayload(BaseModel):
    sub: str   #user_id 
    school_id: str | None 
    role: str
    exp: datetime

#hashing and verifying passwords

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str , hashed_password: str) -> bool:
    return pwd_context.verify(plain_password , hashed_password)

#JWT Token Creation ( Issuing the JWT)

def create_access_token(user_id: UUID , school_id: str | None , role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "school_id": str(school_id) if school_id else None,
        "role": role,
        "exp": expire
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

#JWT Token Verification (Decoding the JWT)
def verify_access_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return TokenPayload(**payload)
    except JWTError as exec:
        raise ValueError("Invalid token") from exec
    