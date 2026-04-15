from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import jwt
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.repositories.sql_repository import SqlRepository

security = HTTPBearer(auto_error=False)


def get_current_login(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail={"error": "Требуется авторизация"})
    try:
        return decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail={"error": "Срок действия токена истёк"})
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail={"error": "Недействительный токен"})


def get_repository(db: Session = Depends(get_db)) -> SqlRepository:
    return SqlRepository(db)
