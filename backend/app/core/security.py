import jwt
from datetime import datetime, timedelta, timezone

from app.core.config import settings


def create_access_token(subject_login: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_expire_days)
    payload = {"sub": subject_login, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> str:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    sub = payload.get("sub")
    if not sub or not isinstance(sub, str):
        raise jwt.InvalidTokenError("missing sub")
    return sub
