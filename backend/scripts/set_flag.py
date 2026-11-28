from __future__ import annotations

import argparse
import asyncio

from app.core.config import settings
from app.infrastructure.database import build_async_engine, build_session_factory
from app.infrastructure.uow import SqlAlchemyUnitOfWork
from app.services.feature_flags import FeatureFlagService


async def _run(args: argparse.Namespace) -> None:
    engine = build_async_engine(settings.sqlalchemy_database_uri)
    try:
        service = FeatureFlagService(
            SqlAlchemyUnitOfWork(build_session_factory(engine))
        )
        await service.set_flag(
            args.flag_name,
            args.enabled == "true",
            description=args.description,
            changed_by=args.changed_by,
        )
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Toggle a feature flag in Postgres.")
    parser.add_argument("flag_name")
    parser.add_argument("enabled", choices=["true", "false"])
    parser.add_argument("--description", default=None)
    parser.add_argument("--changed-by", dest="changed_by", default="dev")
    args = parser.parse_args(argv)
    asyncio.run(_run(args))
    print(f"Flag '{args.flag_name}' -> enabled={args.enabled}")


if __name__ == "__main__":
    main()
