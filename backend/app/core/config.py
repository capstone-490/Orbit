from functools import lru_cache
from typing import Literal

from pydantic import PostgresDsn, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_DEFAULT_SECRET = "local-and-ci-test-only-secret-key"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    ENVIRONMENT: Literal["local", "dev", "test", "staging", "production"] = "local"
    DEBUG: bool = False
    SECRET_KEY: str = INSECURE_DEFAULT_SECRET

    DB_HOST: str
    DB_PORT: int = 5432
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    DB_DRIVER: str = "postgresql+psycopg"

    # Connection Pool Tuning
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    @model_validator(mode="after")
    def EnforceProductionSecret(self) -> Settings:
        if (
            self.ENVIRONMENT in ("staging", "production")
            and self.SECRET_KEY == INSECURE_DEFAULT_SECRET
        ):
            raise ValueError(
                "SECRET_KEY must be set in staging/production environments"
            )
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sqlalchemy_database_uri(self) -> str:
        return str(
            PostgresDsn.build(
                scheme=self.DB_DRIVER,
                username=self.DB_USER,
                password=self.DB_PASSWORD,
                host=self.DB_HOST,
                port=self.DB_PORT,
                path=self.DB_NAME,
            )
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
