"""Import authoritative data from Google Sheets into the local SQLite DB."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.integrations.google_sheets_reader import GoogleSheetsReader
from app.repositories.sql_repository import SqlRepository

logger = logging.getLogger(__name__)


def sheets_import_configured() -> bool:
    if not settings.service_account_path.is_file():
        return False
    try:
        return bool(settings.resolve_spreadsheet_id().strip())
    except OSError:
        return False


def run_sheets_import(db: Session, repo: SqlRepository) -> bool:
    """
    Pull users, menu, weeks, menu flag, day selections, feedback from Sheets into DB.
    Returns True if a full snapshot was applied.
    """
    if not sheets_import_configured():
        logger.info("Sheets import skipped: missing service_account.json or spreadsheet id")
        return False
    try:
        spreadsheet_id = settings.resolve_spreadsheet_id().strip()
    except OSError as e:
        logger.warning("Sheets import skipped: %s", e)
        return False

    try:
        reader = GoogleSheetsReader(settings.service_account_path, spreadsheet_id)
        snap = reader.fetch_snapshot()
    except Exception:
        logger.exception("Sheets import: failed reading snapshot")
        return False

    if snap is None:
        logger.warning("Sheets import failed: empty or invalid snapshot")
        return False

    try:
        with db.begin_nested():
            repo.replace_data_from_sheets_snapshot(
                menu_grid=snap.menu,
                weeks=snap.weeks,
                menu_enabled=snap.menu_enabled,
                users=snap.users,
                selections=snap.selections,
                feedback=snap.feedback,
            )
    except Exception:
        logger.exception("Sheets import: failed writing to database (savepoint rolled back)")
        return False

    logger.info(
        "Sheets import applied: users=%s selections=%s feedback=%s",
        len(snap.users),
        len(snap.selections),
        len(snap.feedback),
    )
    return True
