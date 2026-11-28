# 50% or more AI-generated code

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repositories import AbstractFeatureFlagRepository
from app.infrastructure.tables import feature_flags_table as ff


class SqlAlchemyFeatureFlagRepository(AbstractFeatureFlagRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_all(self) -> dict[str, bool]:
        rows = (
            await self._session.execute(
                select(ff.c.name, ff.c.enabled).order_by(ff.c.name.asc())
            )
        ).all()
        return {str(name): bool(enabled) for name, enabled in rows}

    async def seed_missing(self, flags: list[dict]) -> int:
        """Inserts flags from config if absent; preserves existing DB values."""
        inserted = 0
        for flag in flags:
            enabled = bool(flag.get("enabled", False))
            stmt = (
                pg_insert(ff)
                .values(
                    name=flag["name"],
                    enabled=enabled,
                    rollout_percent=100 if enabled else 0,
                    description=flag.get("description"),
                )
                .on_conflict_do_nothing(index_elements=[ff.c.name])
                .returning(ff.c.name)
            )
            if (await self._session.execute(stmt)).first() is not None:
                inserted += 1
        return inserted

    async def set_enabled(
        self,
        name: str,
        enabled: bool,
        *,
        description: str | None = None,
    ) -> None:
        update_values: dict[str, object] = {
            "enabled": enabled,
            "rollout_percent": 100 if enabled else 0,
        }
        if description is not None:
            update_values["description"] = description

        stmt = (
            pg_insert(ff)
            .values(
                name=name,
                enabled=enabled,
                rollout_percent=100 if enabled else 0,
                description=description,
            )
            .on_conflict_do_update(
                index_elements=[ff.c.name],
                set_=update_values,
            )
        )
        await self._session.execute(stmt)
