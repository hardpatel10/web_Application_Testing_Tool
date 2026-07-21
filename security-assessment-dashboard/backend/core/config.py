"""Application configuration loaded from environment variables.

Centralizes all runtime configuration behind a single, cached Settings
object so the rest of the application depends on an abstraction rather
than on ``os.environ`` directly.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_ROOT.parent


class Settings(BaseSettings):
    """Strongly typed application settings.

    Values are sourced from environment variables and, when present, a
    ``.env`` file at the project root. See ``.env.example`` for the full
    list of supported variables.
    """

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="Security Assessment Dashboard")
    app_version: str = Field(default="0.1.0")
    environment: str = Field(default="development")

    api_prefix: str = Field(default="/api/v1")

    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)

    log_level: str = Field(default="INFO")
    log_dir: Path = Field(default=PROJECT_ROOT / "logs")

    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/app.db",
    )

    assessment_root_dir: Path = Field(
        default=PROJECT_ROOT / "data" / "assessments",
        description="Root directory under which every assessment gets a per-assessment subdirectory tree.",
    )
    reports_dir: Path = Field(default=PROJECT_ROOT / "reports")
    exports_dir: Path = Field(default=PROJECT_ROOT / "data" / "exports")
    temp_dir: Path = Field(default=PROJECT_ROOT / "data" / "temp")
    backups_dir: Path = Field(default=PROJECT_ROOT / "data" / "backups")

    plugins_dir: Path = Field(
        default=BACKEND_ROOT / "plugins" / "plugins",
        description="Directory scanned at startup (and on manual reload) for installed plugin subdirectories.",
    )

    max_concurrent_executions: int = Field(
        default=2,
        gt=0,
        description="Upper bound on tool executions (jobs) running at once, process-wide. Pure asyncio "
        "concurrency (an asyncio.Semaphore) -- no external task queue or worker pool.",
    )

    secret_key: str = Field(default="dev-insecure-secret-key-change-me")

    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )

    @property
    def is_development(self) -> bool:
        return self.environment.lower() == "development"

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Return a cached, process-wide Settings instance."""
    return Settings()
