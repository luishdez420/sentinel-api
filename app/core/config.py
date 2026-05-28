import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


class ConfigurationError(RuntimeError):
    """Raised when required application configuration is missing or unsafe."""


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ConfigurationError(f"{name} must be set")
    return value


def _database_url() -> str:
    value = _required_env("DATABASE_URL")
    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql+psycopg2://", 1)
    return value


def _int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        return int(raw_value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc


@dataclass(frozen=True)
class Settings:
    app_env: str
    database_url: str
    redis_url: str
    jwt_secret: str
    rate_limit_per_minute: int = 20
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    def validate(self) -> None:
        if len(self.jwt_secret) < 32:
            raise ConfigurationError("JWT_SECRET must be at least 32 characters long")

        unsafe_values = {
            "dev_only_change_me",
            "change_me",
            "changeme",
            "replace-with-at-least-32-random-characters",
            "secret",
            "your-secret-here",
        }
        if self.jwt_secret.lower() in unsafe_values:
            raise ConfigurationError("JWT_SECRET must not use a default placeholder")

        if self.access_token_expire_minutes <= 0:
            raise ConfigurationError("ACCESS_TOKEN_EXPIRE_MINUTES must be positive")

        if self.rate_limit_per_minute <= 0:
            raise ConfigurationError("RATE_LIMIT_PER_MINUTE must be positive")


def get_settings() -> Settings:
    settings = Settings(
        app_env=os.getenv("APP_ENV", "development"),
        database_url=_database_url(),
        redis_url=os.getenv("REDIS_URL", "redis://redis:6379/0"),
        jwt_secret=_required_env("JWT_SECRET"),
        rate_limit_per_minute=_int_env(
            "RATE_LIMIT_PER_MINUTE",
            _int_env("RATE_LIMIT", 20),
        ),
        access_token_expire_minutes=_int_env("ACCESS_TOKEN_EXPIRE_MINUTES", 30),
    )
    settings.validate()
    return settings


settings = get_settings()
