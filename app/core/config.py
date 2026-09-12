import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _csv(name: str, default: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in os.getenv(name, default).split(",") if item.strip())


def _integer(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError as error:
        raise ValueError(f"{name} must be an integer") from error


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development").lower()
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5")
    supabase_url: str | None = os.getenv("SUPABASE_URL")
    supabase_key: str | None = os.getenv("SUPABASE_KEY")
    redis_url: str | None = os.getenv("REDIS_URL")
    allowed_origins: tuple[str, ...] = _csv("ALLOWED_ORIGINS", "http://127.0.0.1:8001,http://localhost:8001")
    trusted_hosts: tuple[str, ...] = _csv("TRUSTED_HOSTS", "127.0.0.1,localhost,testserver")
    rate_limit_requests: int = _integer("RATE_LIMIT_REQUESTS", 120)
    rate_limit_window_seconds: int = _integer("RATE_LIMIT_WINDOW_SECONDS", 60)
    max_page_size: int = _integer("MAX_PAGE_SIZE", 200)


settings = Settings()
if not settings.openai_api_key:
    raise ValueError("OPENAI_API_KEY is missing")
if not settings.supabase_url:
    raise ValueError("SUPABASE_URL is missing")
if not settings.supabase_key:
    raise ValueError("SUPABASE_KEY is missing")
if settings.app_env == "production" and settings.supabase_key.startswith("sb_publishable_"):
    raise ValueError("SUPABASE_KEY must be a server secret in production")
if settings.app_env == "production" and not settings.redis_url:
    raise ValueError("REDIS_URL is required for distributed production rate limiting")

OPENAI_API_KEY = settings.openai_api_key
OPENAI_MODEL = settings.openai_model
SUPABASE_URL = settings.supabase_url
SUPABASE_KEY = settings.supabase_key
APP_ENV = settings.app_env
