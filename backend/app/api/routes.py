from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.core.cache import TTLCache
from app.core.config import settings
from app.core.deps import get_current_login, get_repository
from app.core.security import create_access_token
from app.db.session import get_db
from app.repositories.sql_repository import SqlRepository
from app.schemas.models import (
    DeleteSelectionsRequest,
    GetSelectionsRequest,
    LoginRequest,
    SaveFeedbackRequest,
    SaveSelectionsRequest,
)
from app.services.catering_service import CateringService
from app.services.sheets_import import run_sheets_import

_cache = TTLCache(ttl_seconds=settings.cache_ttl_seconds)


def get_service(repo: SqlRepository = Depends(get_repository)) -> CateringService:
    return CateringService(repo, _cache)


def build_router() -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    def health():
        return PlainTextResponse("OK", status_code=200)

    @router.post("/login")
    def login(payload: LoginRequest, repo: SqlRepository = Depends(get_repository)):
        if not payload.login.strip() or not payload.password.strip():
            raise HTTPException(
                status_code=401,
                detail={"status": "error", "message": "Неверный логин или пароль"},
            )
        result = repo.try_login(payload.login.strip(), payload.password.strip())
        if not result:
            raise HTTPException(
                status_code=401,
                detail={"status": "error", "message": "Неверный логин или пароль"},
            )
        token = create_access_token(result["login"])
        return {
            "status": "ok",
            "login": result["login"],
            "note": result["note"],
            "access_token": token,
            "token_type": "bearer",
        }

    @router.get("/me")
    def me(login: str = Depends(get_current_login), repo: SqlRepository = Depends(get_repository)):
        ok, code, msg = repo.verify_user_access(login)
        if not ok:
            raise HTTPException(status_code=code or 401, detail={"error": msg})
        return {"login": login, "note": repo.get_user_note(login)}

    @router.get("/weeks")
    def weeks(login: str = Depends(get_current_login), service: CateringService = Depends(get_service)):
        ok, code, msg = service.verify_login(login)
        if not ok:
            raise HTTPException(status_code=code or 401, detail={"error": msg})
        return service.get_weeks()

    @router.get("/menu")
    def menu(login: str = Depends(get_current_login), service: CateringService = Depends(get_service)):
        ok, code, msg = service.verify_login(login)
        if not ok:
            raise HTTPException(status_code=code or 401, detail={"error": msg})
        return service.get_menu()

    @router.get("/menu_enabled")
    def menu_enabled(login: str = Depends(get_current_login), service: CateringService = Depends(get_service)):
        try:
            ok, code, msg = service.verify_login(login)
            if not ok:
                raise HTTPException(status_code=code or 401, detail={"error": msg})
            return service.get_menu_enabled()
        except HTTPException:
            raise
        except Exception:
            return {"enabled": True}

    @router.post("/save")
    def save(
        payload: SaveSelectionsRequest,
        login: str = Depends(get_current_login),
        service: CateringService = Depends(get_service),
    ):
        ok, code, msg = service.verify_login(login)
        if not ok:
            raise HTTPException(status_code=code or 401, detail={"error": msg})
        if not payload.day:
            raise HTTPException(status_code=400, detail={"error": "Не указан день недели"})
        return service.save_selections(payload.day, payload.selections.model_dump(), login)

    @router.post("/delete")
    def delete(
        payload: DeleteSelectionsRequest,
        login: str = Depends(get_current_login),
        service: CateringService = Depends(get_service),
    ):
        ok, code, msg = service.verify_login(login)
        if not ok:
            raise HTTPException(status_code=code or 401, detail={"error": msg})
        if not payload.day:
            raise HTTPException(status_code=400, detail={"error": "Не указан день недели"})
        return service.delete_selections(payload.day, login)

    @router.post("/get_selections")
    def get_selections(
        payload: GetSelectionsRequest,
        login: str = Depends(get_current_login),
        service: CateringService = Depends(get_service),
    ):
        ok, code, msg = service.verify_login(login)
        if not ok:
            raise HTTPException(status_code=code or 401, detail={"error": msg})
        if not payload.day:
            raise HTTPException(status_code=400, detail={"error": "Не указан день недели"})
        return service.get_selections(payload.day, login)

    @router.post("/save_feedback")
    def save_feedback(
        payload: SaveFeedbackRequest,
        login: str = Depends(get_current_login),
        service: CateringService = Depends(get_service),
    ):
        ok, code, msg = service.verify_login(login)
        if not ok:
            raise HTTPException(status_code=code or 401, detail={"error": msg})
        if payload.rating < 1 or payload.rating > 5:
            raise HTTPException(status_code=400, detail={"error": "Рейтинг должен быть от 1 до 5"})
        if not payload.feedback_text.strip():
            raise HTTPException(status_code=400, detail={"error": "Текст отзыва не может быть пустым"})
        return service.save_feedback(login, payload.rating, payload.feedback_text.strip())

    @router.post("/get_feedback")
    def get_feedback(login: str = Depends(get_current_login), service: CateringService = Depends(get_service)):
        ok, code, msg = service.verify_login(login)
        if not ok:
            raise HTTPException(status_code=code or 401, detail={"error": msg})
        return service.get_feedback(login)

    @router.post("/delete_feedback")
    def delete_feedback(login: str = Depends(get_current_login), service: CateringService = Depends(get_service)):
        ok, code, msg = service.verify_login(login)
        if not ok:
            raise HTTPException(status_code=code or 401, detail={"error": msg})
        return service.delete_feedback(login)

    @router.post("/sync_from_sheets")
    def sync_from_sheets(
        db: Session = Depends(get_db),
        x_sheets_sync_token: str | None = Header(default=None, alias="X-Sheets-Sync-Token"),
    ):
        """Re-import menu/users/weeks/selections/feedback from Google Sheets into SQLite."""
        expected = settings.sheets_sync_token.strip()
        if not expected:
            raise HTTPException(
                status_code=404,
                detail={"error": "Синхронизация отключена: задайте SHEETS_SYNC_TOKEN в окружении"},
            )
        if (x_sheets_sync_token or "").strip() != expected:
            raise HTTPException(status_code=403, detail={"error": "Неверный X-Sheets-Sync-Token"})
        repo = SqlRepository(db)
        ok = run_sheets_import(db, repo)
        if ok:
            _cache.invalidate_prefix("read:")
        return {"synced": ok}

    return router
