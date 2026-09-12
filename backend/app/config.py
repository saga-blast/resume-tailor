from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    secret_key: str = "dev-secret-change-me"
    database_url: str = "sqlite:///./storage/app.db"
    compile_service_url: str = "http://localhost:8100"
    storage_dir: str = "./storage"

    seed_user_email: str = "user@example.com"
    seed_user_password: str = "change-me"

    access_token_expire_minutes: int = 60 * 24 * 7


@lru_cache
def get_settings() -> Settings:
    return Settings()
