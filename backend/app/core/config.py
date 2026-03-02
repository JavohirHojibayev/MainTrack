from __future__ import annotations

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    PROJECT_NAME: str = "MineTrack"
    API_V1_STR: str = "/api/v1"

    DATABASE_URL: str = "postgresql+psycopg2://minetrack_user:changeme@127.0.0.1:5432/minetrack_db"

    SECRET_KEY: str = "change-this-secret"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12
    TOKEN_ALGORITHM: str = "HS256"
    DEVICE_CONTROL_PASSWORD: str = "admin"

    ESMO_OK_WINDOW_HOURS: int = 6
    TURNSTILE_DEDUP_SECONDS: int = 20

    # ESMO (read-only polling)
    ESMO_ENABLED: bool = True
    ESMO_BASE_URL: str = "https://192.168.8.10/cab/"
    ESMO_USER: str = "admin"
    ESMO_PASS: str = "QW1665gety"
    ESMO_POLL_INTERVAL: int = 30
    ESMO_REQUEST_TIMEOUT: int = 20
    ESMO_LOGIN_RETRIES: int = 2
    ESMO_EMPLOYEE_PREVIEW_PAGES: int = 1
    ESMO_EMPLOYEE_SYNC_PAGES: int = 100
    ESMO_BACKFILL_MAX_PAGES: int = 200
    ESMO_HEALTHCHECK_INTERVAL_SECONDS: int = 300
    ESMO_HEALTHCHECK_LAST_N: int = 25
    ESMO_HEALTHCHECK_MAX_PAGES: int = 2

    # Hikvision Turnstile (read-only polling)
    HIKVISION_USER: str = "admin"
    HIKVISION_PASS: str = ""
    HIKVISION_POLL_INTERVAL: int = 30
    HIKVISION_DEVICES: str = "[]"
    HIKVISION_INITIAL_LOOKBACK_HOURS: int = 24
    HIKVISION_RECOVERY_OVERLAP_SECONDS: int = 120

    BACKEND_CORS_ORIGINS: List[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, value: str | List[str]) -> List[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


settings = Settings()
