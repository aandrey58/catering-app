from sqlalchemy import select

from app.core.config import settings
from app.db.base import Base
from app.db.models import User
from app.db.session import SessionLocal, engine
from app.repositories.sql_repository import SqlRepository
from app.services.sheets_import import run_sheets_import


def init_db() -> None:
    data_dir = settings.backend_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        repo = SqlRepository(db)
        repo.ensure_default_settings()

        run_sheets_import(db, repo)

        has_user = db.scalar(select(User.id).limit(1))
        if has_user is None and settings.seed_admin_login.strip() and settings.seed_admin_password.strip():
            repo.create_user(
                settings.seed_admin_login.strip(),
                settings.seed_admin_password,
                note=settings.seed_admin_note or "",
                active=True,
            )

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
