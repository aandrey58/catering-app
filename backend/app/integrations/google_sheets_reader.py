"""Read-only Google Sheets access mirroring legacy server.py layout."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

SHEET_MENU = "Меню"
SHEET_USERS = "Логины/Пароли"
SHEET_WEEKS = "Недели"
SHEET_FEEDBACK = "Обратная связь"

DAY_TO_SHEET = {
    "mon": "ПН",
    "tue": "ВТ",
    "wed": "СР",
    "thu": "ЧТ",
    "fri": "ПТ",
}

COL_TO_CATEGORY = {
    1: "breakfast",
    2: "soup",
    3: "hot",
    4: "side",
    5: "salad",
    6: "dessert",
}


@dataclass
class SheetsSnapshot:
    menu: list[list[str]]
    menu_enabled: bool
    weeks: dict
    users: list[tuple[str, str, str, bool]]
    selections: list[tuple[str, str, dict]]
    feedback: list[tuple[str, int, str]]


def _cell_str(v: object) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _normalize_grid(values: list[list]) -> list[list[str]]:
    out: list[list[str]] = []
    for row in values:
        out.append([_cell_str(c) for c in row])
    return out


class GoogleSheetsReader:
    def __init__(self, service_account_path: Path, spreadsheet_id: str) -> None:
        self._spreadsheet_id = spreadsheet_id
        creds = service_account.Credentials.from_service_account_file(
            str(service_account_path),
            scopes=SCOPES,
        )
        self._service = build("sheets", "v4", credentials=creds, cache_discovery=False)

    def _find_sheet_props(self, sheet_name: str) -> dict | None:
        try:
            spreadsheet = (
                self._service.spreadsheets().get(spreadsheetId=self._spreadsheet_id).execute()
            )
            for sheet in spreadsheet.get("sheets", []):
                props = sheet.get("properties") or {}
                if props.get("title") == sheet_name:
                    return props
        except HttpError as e:
            logger.warning("Sheets API get spreadsheet failed: %s", e)
        return None

    def _values(self, range_a1: str) -> list[list]:
        try:
            result = (
                self._service.spreadsheets()
                .values()
                .get(spreadsheetId=self._spreadsheet_id, range=range_a1)
                .execute()
            )
            return result.get("values") or []
        except HttpError as e:
            logger.warning("Sheets read %s failed: %s", range_a1, e)
            return []

    def read_menu_and_enabled(self) -> tuple[list[list[str]], bool] | None:
        if not self._find_sheet_props(SHEET_MENU):
            logger.error("Sheet '%s' not found", SHEET_MENU)
            return None
        raw = self._values(f"'{SHEET_MENU}'!A:Z")
        grid = _normalize_grid(raw)
        enabled = True
        if raw and len(raw) > 0 and len(raw[0]) > 0:
            enabled = _cell_str(raw[0][0]) == "1"
        return grid, enabled

    def read_weeks(self) -> dict:
        if not self._find_sheet_props(SHEET_WEEKS):
            logger.warning("Sheet '%s' not found, using default weeks", SHEET_WEEKS)
            return {
                "current": "",
                "next": "",
                "week1_enabled": True,
                "week2_enabled": True,
            }
        values = self._values(f"'{SHEET_WEEKS}'!B1:C2")
        current_week = _cell_str(values[0][0]) if len(values) > 0 and len(values[0]) > 0 else ""
        next_week = _cell_str(values[1][0]) if len(values) > 1 and len(values[1]) > 0 else ""
        week1_enabled = True
        week2_enabled = True
        if len(values) > 0 and len(values[0]) > 1:
            week1_enabled = _cell_str(values[0][1]) == "1"
        if len(values) > 1 and len(values[1]) > 1:
            week2_enabled = _cell_str(values[1][1]) == "1"
        return {
            "current": current_week,
            "next": next_week,
            "week1_enabled": week1_enabled,
            "week2_enabled": week2_enabled,
        }

    def read_users(self) -> list[tuple[str, str, str, bool]]:
        if not self._find_sheet_props(SHEET_USERS):
            logger.error("Sheet '%s' not found", SHEET_USERS)
            return []
        values = self._values(f"'{SHEET_USERS}'!B:D")
        by_login: dict[str, tuple[str, str, bool]] = {}
        start_row = 1 if len(values) > 0 and values[0] else 0
        for i in range(start_row, len(values)):
            row = values[i]
            login = _cell_str(row[0]) if len(row) >= 1 else ""
            if not login:
                continue
            password = _cell_str(row[1]) if len(row) > 1 else ""
            note = _cell_str(row[2]) if len(row) > 2 else ""
            active = bool(login and password)
            by_login[login] = (password, note, active)
        return [(login, p, n, a) for login, (p, n, a) in by_login.items()]

    def _parse_day_selections(self, sheet_title: str) -> dict[str, dict]:
        """Last row per login wins (same as legacy get_user_selections)."""
        if not self._find_sheet_props(sheet_title):
            return {}
        values = self._values(f"'{sheet_title}'!B:H")
        by_login: dict[str, dict] = {}
        for i in range(1, len(values)):
            row = values[i]
            if not row or not _cell_str(row[0]):
                continue
            login = _cell_str(row[0])
            sel: dict[str, str] = {}
            for col_index, category in COL_TO_CATEGORY.items():
                if col_index < len(row):
                    sel[category] = _cell_str(row[col_index])
                else:
                    sel[category] = ""
            by_login[login] = sel
        return by_login

    def read_all_day_selections(self) -> list[tuple[str, str, dict]]:
        out: list[tuple[str, str, dict]] = []
        for day, title in DAY_TO_SHEET.items():
            by_login = self._parse_day_selections(title)
            for login, sel in by_login.items():
                out.append((day, login, sel))
        return out

    def read_feedback(self) -> list[tuple[str, int, str]]:
        if not self._find_sheet_props(SHEET_FEEDBACK):
            logger.warning("Sheet '%s' not found", SHEET_FEEDBACK)
            return []
        values = self._values(f"'{SHEET_FEEDBACK}'!A:C")
        by_login: dict[str, tuple[int, str]] = {}
        for i in range(1, len(values)):
            row = values[i]
            login = _cell_str(row[0]) if row else ""
            if not login:
                continue
            rating = 0
            if len(row) > 1 and row[1] not in (None, ""):
                try:
                    rating = int(_cell_str(row[1]))
                except ValueError:
                    rating = 0
            text = _cell_str(row[2]) if len(row) > 2 else ""
            by_login[login] = (rating, text)
        return [(login, r, t) for login, (r, t) in by_login.items()]

    def fetch_snapshot(self) -> SheetsSnapshot | None:
        try:
            menu_block = self.read_menu_and_enabled()
            if menu_block is None:
                return None
            menu_grid, menu_enabled = menu_block
            users = self.read_users()
            if not users:
                logger.warning("No users parsed from sheet '%s'", SHEET_USERS)
                return None
            weeks = self.read_weeks()
            selections = self.read_all_day_selections()
            feedback = self.read_feedback()
            return SheetsSnapshot(
                menu=menu_grid,
                menu_enabled=menu_enabled,
                weeks=weeks,
                users=users,
                selections=selections,
                feedback=feedback,
            )
        except Exception:
            logger.exception("fetch_snapshot failed")
            return None
