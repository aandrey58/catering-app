import json

from passlib.context import CryptContext
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import AppSetting, DaySelection, FeedbackRow, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_INACTIVE_PLACEHOLDER_PASSWORD = "__sheet_inactive_no_password__"

KEY_MENU = "menu_json"
KEY_WEEKS = "weeks_json"
KEY_MENU_ENABLED = "menu_enabled"

DEFAULT_MENU: list[list[str]] = [
    ["Day", "Col1", "Col2", "Col3", "Col4", "Col5", "Col6"],
    ["Monday", "", "", "", "", "", ""],
    ["Tuesday", "", "", "", "", "", ""],
    ["Wednesday", "", "", "", "", "", ""],
    ["Thursday", "", "", "", "", "", ""],
    ["Friday", "", "", "", "", "", ""],
]

DEFAULT_WEEKS = {
    "current": "",
    "next": "",
    "week1_enabled": True,
    "week2_enabled": True,
}


class SqlRepository:
    def __init__(self, db: Session):
        self.db = db

    def _get_setting(self, key: str) -> str | None:
        row = self.db.scalar(select(AppSetting).where(AppSetting.key == key))
        return row.value if row else None

    def _set_setting(self, key: str, value: str) -> None:
        row = self.db.scalar(select(AppSetting).where(AppSetting.key == key))
        if row:
            row.value = value
        else:
            self.db.add(AppSetting(key=key, value=value))

    def get_users(self) -> dict:
        """Совместимость с прежним контрактом: пароль не отдаём наружу."""
        users = {}
        for u in self.db.scalars(select(User)).all():
            users[u.login] = {"password": "", "note": u.note or "", "active": u.active}
        return users

    def try_login(self, login: str, password: str) -> dict | None:
        user = self.db.scalar(select(User).where(User.login == login))
        if not user or not user.active:
            return None
        if not pwd_context.verify(password, user.password_hash):
            return None
        return {"login": user.login, "note": user.note or ""}

    def user_is_active(self, login: str) -> bool:
        user = self.db.scalar(select(User).where(User.login == login))
        return user is not None and user.active

    def verify_user_access(self, login: str) -> tuple[bool, int | None, str | None]:
        user = self.db.scalar(select(User).where(User.login == login))
        if not user:
            return False, 401, "Логин не найден в системе"
        if not user.active:
            return False, 403, "Пользователь неактивен"
        return True, None, None

    def get_user_note(self, login: str) -> str:
        user = self.db.scalar(select(User).where(User.login == login))
        return (user.note or "") if user else ""

    def get_weeks(self) -> dict:
        raw = self._get_setting(KEY_WEEKS)
        if not raw:
            return DEFAULT_WEEKS.copy()
        try:
            data = json.loads(raw)
            return {
                "current": str(data.get("current", "")),
                "next": str(data.get("next", "")),
                "week1_enabled": bool(data.get("week1_enabled", True)),
                "week2_enabled": bool(data.get("week2_enabled", True)),
            }
        except (json.JSONDecodeError, TypeError):
            return DEFAULT_WEEKS.copy()

    def get_menu(self) -> list:
        raw = self._get_setting(KEY_MENU)
        if not raw:
            return DEFAULT_MENU
        try:
            data = json.loads(raw)
            return data if isinstance(data, list) else DEFAULT_MENU
        except json.JSONDecodeError:
            return DEFAULT_MENU

    def get_menu_enabled(self) -> bool:
        raw = self._get_setting(KEY_MENU_ENABLED)
        if raw is None or raw == "":
            return True
        return raw.strip() == "1"

    def get_selections(self, day: str, login: str) -> dict | None:
        row = self.db.scalar(
            select(DaySelection).where(DaySelection.login == login, DaySelection.day == day)
        )
        if not row:
            return None
        return {
            "breakfast": row.breakfast or "",
            "soup": row.soup or "",
            "hot": row.hot or "",
            "side": row.side or "",
            "salad": row.salad or "",
            "dessert": row.dessert or "",
        }

    def save_selections(self, day: str, selections: dict, login: str) -> None:
        row = self.db.scalar(
            select(DaySelection).where(DaySelection.login == login, DaySelection.day == day)
        )
        if row:
            row.breakfast = selections.get("breakfast", "") or ""
            row.soup = selections.get("soup", "") or ""
            row.hot = selections.get("hot", "") or ""
            row.side = selections.get("side", "") or ""
            row.salad = selections.get("salad", "") or ""
            row.dessert = selections.get("dessert", "") or ""
        else:
            self.db.add(
                DaySelection(
                    login=login,
                    day=day,
                    breakfast=selections.get("breakfast", "") or "",
                    soup=selections.get("soup", "") or "",
                    hot=selections.get("hot", "") or "",
                    side=selections.get("side", "") or "",
                    salad=selections.get("salad", "") or "",
                    dessert=selections.get("dessert", "") or "",
                )
            )

    def delete_selections(self, day: str, login: str) -> dict:
        row = self.db.scalar(
            select(DaySelection).where(DaySelection.login == login, DaySelection.day == day)
        )
        if not row:
            return {"deleted": False, "message": "Строка с указанным логином не найдена"}
        self.db.delete(row)
        return {"deleted": True, "row": row.id}

    def get_feedback(self, login: str) -> dict | None:
        row = self.db.scalar(select(FeedbackRow).where(FeedbackRow.login == login))
        if not row:
            return None
        return {"rating": row.rating, "feedback_text": row.feedback_text or ""}

    def save_feedback(self, login: str, rating: int, feedback_text: str) -> None:
        row = self.db.scalar(select(FeedbackRow).where(FeedbackRow.login == login))
        if row:
            row.rating = rating
            row.feedback_text = feedback_text
        else:
            self.db.add(FeedbackRow(login=login, rating=rating, feedback_text=feedback_text))

    def delete_feedback(self, login: str) -> dict:
        row = self.db.scalar(select(FeedbackRow).where(FeedbackRow.login == login))
        if not row:
            return {"deleted": False, "message": "Фидбэк не найден"}
        rid = row.id
        self.db.delete(row)
        return {"deleted": True, "row": rid}

    @staticmethod
    def hash_password(plain: str) -> str:
        return pwd_context.hash(plain)

    def create_user(self, login: str, password_plain: str, note: str = "", active: bool = True) -> User:
        user = User(
            login=login,
            password_hash=pwd_context.hash(password_plain),
            note=note,
            active=active,
        )
        self.db.add(user)
        return user

    def ensure_default_settings(self) -> None:
        if self._get_setting(KEY_MENU) is None:
            self._set_setting(KEY_MENU, json.dumps(DEFAULT_MENU, ensure_ascii=False))
        if self._get_setting(KEY_WEEKS) is None:
            self._set_setting(KEY_WEEKS, json.dumps(DEFAULT_WEEKS, ensure_ascii=False))
        if self._get_setting(KEY_MENU_ENABLED) is None:
            self._set_setting(KEY_MENU_ENABLED, "1")

    def replace_data_from_sheets_snapshot(
        self,
        menu_grid: list[list[str]],
        weeks: dict,
        menu_enabled: bool,
        users: list[tuple[str, str, str, bool]],
        selections: list[tuple[str, str, dict]],
        feedback: list[tuple[str, int, str]],
    ) -> None:
        """Replace mirrored tables and settings from a Google Sheets snapshot (one transaction)."""
        self.db.execute(delete(FeedbackRow))
        self.db.execute(delete(DaySelection))
        self.db.execute(delete(User))

        self._set_setting(KEY_MENU, json.dumps(menu_grid, ensure_ascii=False))
        self._set_setting(KEY_WEEKS, json.dumps(weeks, ensure_ascii=False))
        self._set_setting(KEY_MENU_ENABLED, "1" if menu_enabled else "0")

        for login, password_plain, note, active in users:
            if not login:
                continue
            if active and password_plain:
                password_hash = pwd_context.hash(password_plain)
            else:
                password_hash = pwd_context.hash(_INACTIVE_PLACEHOLDER_PASSWORD)
            self.db.add(
                User(
                    login=login,
                    password_hash=password_hash,
                    note=note or "",
                    active=active,
                )
            )

        for day, login, sel in selections:
            if not login:
                continue
            self.db.add(
                DaySelection(
                    login=login,
                    day=day,
                    breakfast=str(sel.get("breakfast", "") or ""),
                    soup=str(sel.get("soup", "") or ""),
                    hot=str(sel.get("hot", "") or ""),
                    side=str(sel.get("side", "") or ""),
                    salad=str(sel.get("salad", "") or ""),
                    dessert=str(sel.get("dessert", "") or ""),
                )
            )

        for login, rating, text in feedback:
            if not login:
                continue
            self.db.add(FeedbackRow(login=login, rating=int(rating), feedback_text=text or ""))
