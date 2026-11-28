# 50% or more AI-generated code
from __future__ import annotations

import json
import os
from pathlib import Path

from app.core.config import settings
from app.domain.uow import AbstractUnitOfWork


def parse_env_overrides(raw: str | None = None) -> dict[str, bool]:
    """Optional dev override via FEATURE_FLAG_OVERRIDES='use_v2_workspace=true'."""
    value = raw if raw is not None else os.getenv("FEATURE_FLAG_OVERRIDES", "")
    overrides: dict[str, bool] = {}
    for entry in value.split(","):
        if "=" not in entry:
            continue
        name, flag_val = entry.split("=", 1)
        clean_name = name.strip()
        if clean_name:
            overrides[clean_name] = flag_val.strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
            }
    return overrides


class FeatureFlagService:
    def __init__(self, uow: AbstractUnitOfWork) -> None:
        self._uow = uow

    async def seed_from_config(self, path: Path = settings.TOGGLES_CONFIG_PATH) -> int:
        if not path.exists():
            return 0
        with path.open(encoding="utf-8") as fh:
            flags = json.load(fh).get("flags", [])
        if not flags:
            return 0
        async with self._uow as uow:
            await uow.set_tenant_context(None, bypass_rls=True, actor_type="system")
            inserted = await uow.feature_flags.seed_missing(flags)
            await uow.commit()
            return inserted

    async def get_all(self) -> dict[str, bool]:
        async with self._uow as uow:
            flags = await uow.feature_flags.get_all()
        return {**flags, **parse_env_overrides()}

    async def is_enabled(self, name: str) -> bool:
        return (await self.get_all()).get(name, False)

    async def set_flag(
        self,
        name: str,
        enabled: bool,
        *,
        description: str | None = None,
        changed_by: str | None = None,
    ) -> None:
        async with self._uow as uow:
            await uow.set_tenant_context(
                None,
                bypass_rls=True,
                actor_id=changed_by or "cli",
                actor_type="platform",
            )
            await uow.feature_flags.set_enabled(name, enabled, description=description)
            await uow.commit()
