from fastapi import HTTPException, Header
from jose import jwt, JWTError
from config import settings


def get_current_user_id(authorization: str = Header(...)) -> int:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid auth header")
    token = authorization.removeprefix("Bearer ")
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(401, "Invalid token")
        return int(user_id)
    except JWTError:
        raise HTTPException(401, "Invalid or expired token")


def create_token(user_id: int) -> str:
    from datetime import datetime, timedelta, timezone
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
