from app.core.cache import TTLCache
from app.repositories.sql_repository import SqlRepository


class CateringService:
    def __init__(self, repository: SqlRepository, cache: TTLCache):
        self.repository = repository
        self.cache = cache

    def verify_login(self, login: str):
        if not login or not login.strip():
            return False, 401, "Логин не указан"
        return self.repository.verify_user_access(login.strip())

    def login(self, login: str, password: str):
        result = self.repository.try_login(login.strip(), password)
        if not result:
            return {"status": "error", "message": "Неверный логин или пароль"}, 401
        return {"status": "ok", "login": result["login"], "note": result["note"]}, 200

    def get_weeks(self):
        cache_key = "read:weeks"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        value = self.repository.get_weeks()
        self.cache.set(cache_key, value)
        return value

    def get_menu(self):
        cache_key = "read:menu"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        value = self.repository.get_menu()
        self.cache.set(cache_key, value)
        return value

    def get_menu_enabled(self):
        cache_key = "read:menu_enabled"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        value = {"enabled": self.repository.get_menu_enabled()}
        self.cache.set(cache_key, value)
        return value

    def save_selections(self, day: str, selections: dict, login: str):
        self.repository.save_selections(day, selections, login)
        self.cache.invalidate_prefix("read:")
        return {"success": True, "message": "Данные успешно сохранены"}

    def delete_selections(self, day: str, login: str):
        result = self.repository.delete_selections(day, login)
        self.cache.invalidate_prefix("read:")
        return result

    def get_selections(self, day: str, login: str):
        return {"selections": self.repository.get_selections(day, login)}

    def save_feedback(self, login: str, rating: int, feedback_text: str):
        self.repository.save_feedback(login, rating, feedback_text)
        self.cache.invalidate_prefix("read:")
        return {"success": True, "message": "Фидбэк успешно сохранён"}

    def get_feedback(self, login: str):
        return {"feedback": self.repository.get_feedback(login)}

    def delete_feedback(self, login: str):
        result = self.repository.delete_feedback(login)
        self.cache.invalidate_prefix("read:")
        return result
