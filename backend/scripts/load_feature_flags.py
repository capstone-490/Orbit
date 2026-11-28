from __future__ import annotations

import asyncio

from app.core.config import settings
from app.infrastructure.database import build_async_engine, build_session_factory
from app.infrastructure.uow import SqlAlchemyUnitOfWork
from app.services.feature_flags import FeatureFlagService


async def _run() -> int:
    engine = build_async_engine(settings.sqlalchemy_database_uri)
    try:
        service = FeatureFlagService(
            SqlAlchemyUnitOfWork(build_session_factory(engine))
        )
        return await service.seed_from_config()
    finally:
        await engine.dispose()


def main() -> None:
    inserted = asyncio.run(_run())
    print(f"Feature flags synced ({inserted} new flag(s) added).")


if __name__ == "__main__":
    main()
