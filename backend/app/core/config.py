from functools import lru_cache
from typing import Literal

from pydantic import PostgresDsn, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_DEFAULT_SECRET = "local-and-ci-test-only-secret-key"
INSECURE_DEFAULT_ANONYMIZATION_SECRET = "Supercalifragilisticexpialidocious"
<<<<<<< HEAD
from pathlib import Path
=======
>>>>>>> 87fe284 (add makefile to make testing locally easier, break up compose for prod and local deployment, partly dockerize frontend, prep move to new schema)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[3] / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    ENVIRONMENT: Literal["local", "dev", "test", "staging", "production"] = "local"
    DEBUG: bool = False
    SECRET_KEY: str = INSECURE_DEFAULT_SECRET
    ORBIT_ANONYMIZATION_SECRET: str = INSECURE_DEFAULT_ANONYMIZATION_SECRET
    VITE_API_URL: str = "http://localhost:8001"

    # Frontend
    FRONTEND_URL: str = "http://localhost:5173"

    # Email configuration
    RESEND_API_KEY: str | None = None
    RESEND_FROM_EMAIL: str = "Orbit <onboarding@resend.dev>"

    # SMTP configuration
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_FROM: str = "no-reply@orbit.local"
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None

    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 5432
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    DB_DRIVER: str = "postgresql+psycopg"

    # Database administrator credentials
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str

    # Connection Pool Tuning
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    @model_validator(mode="after")
    def enforce_production_secrets(self) -> Settings:
        if self.ENVIRONMENT in ("staging", "production") and (
            self.SECRET_KEY == INSECURE_DEFAULT_SECRET
            or self.ORBIT_ANONYMIZATION_SECRET == INSECURE_DEFAULT_ANONYMIZATION_SECRET
            or self.VITE_API_URL == "http://localhost:8001"
        ):
            raise ValueError("Environment variables must be set in staging/production")

        if (
            self.ENVIRONMENT in ("staging", "production")
            and self.POSTGRES_PASSWORD == ""
        ):
            raise ValueError("POSTGRES_PASSWORD must be configured")

        return self

    def _build_database_uri(
        self,
        username: str,
        password: str,
        driver: str,
    ) -> str:
        return str(
            PostgresDsn.build(
                scheme=driver,
                username=username,
                password=password,
                host=self.DB_HOST,
                port=self.DB_PORT,
                path=self.DB_NAME,
            )
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sqlalchemy_database_uri(self) -> str:
        return (
            f"{self.DB_DRIVER}://"
            f"{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def admin_database_uri(self) -> str:
        return (
            f"{self.DB_DRIVER}://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def psycopg_database_uri(self) -> str:
        """Application psycopg connection URL (orbit_app)."""
        return self._build_database_uri(self.DB_USER, self.DB_PASSWORD, "postgresql")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def admin_psycopg_database_uri(self) -> str:
        """Privileged psycopg connection URL (postgres)."""
        return self._build_database_uri(
            self.POSTGRES_USER, self.POSTGRES_PASSWORD, "postgresql"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
