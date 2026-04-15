from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Catering API"
    app_env: str = "dev"
    app_port: int = 8000
    app_host: str = "127.0.0.1"
    cors_origins: str = "*"

    service_account_file: str = "service_account.json"
    table_id_file: str = "table_id"
    spreadsheet_id: str = Field(
        default="",
        validation_alias=AliasChoices("SPREADSHEET_ID", "GOOGLE_SPREADSHEET_ID", "TABLE_ID"),
    )
    cache_ttl_seconds: int = 60

    database_url: str = Field(
        default="sqlite:///./data/catering.db",
        validation_alias=AliasChoices("DATABASE_URL"),
    )

    @property
    def effective_database_url(self) -> str:
        u = self.database_url
        if u.startswith("sqlite:///./"):
            path = self.backend_dir / u.removeprefix("sqlite:///./")
            return f"sqlite:///{path.resolve().as_posix()}"
        return u
    jwt_secret: str = Field(
        default="dev-secret-change-in-production",
        validation_alias=AliasChoices("JWT_SECRET"),
    )
    jwt_expire_days: int = Field(default=30, validation_alias=AliasChoices("JWT_EXPIRE_DAYS"))
    seed_admin_login: str = Field(default="", validation_alias=AliasChoices("SEED_ADMIN_LOGIN"))
    seed_admin_password: str = Field(default="", validation_alias=AliasChoices("SEED_ADMIN_PASSWORD"))
    seed_admin_note: str = Field(default="Admin", validation_alias=AliasChoices("SEED_ADMIN_NOTE"))

    sheets_sync_token: str = Field(
        default="",
        validation_alias=AliasChoices("SHEETS_SYNC_TOKEN"),
        description="If set, POST /sync_from_sheets requires header X-Sheets-Sync-Token with this value.",
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def backend_dir(self) -> Path:
        return Path(__file__).resolve().parents[2]

    @property
    def service_account_path(self) -> Path:
        return self.backend_dir / self.service_account_file

    @property
    def table_id_path(self) -> Path:
        return self.backend_dir / self.table_id_file

    def resolve_spreadsheet_id(self) -> str:
        if self.spreadsheet_id.strip():
            return self.spreadsheet_id.strip()
        return self.table_id_path.read_text(encoding="utf-8").strip()


settings = Settings()
