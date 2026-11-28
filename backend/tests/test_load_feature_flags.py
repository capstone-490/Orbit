from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.feature_flags import FeatureFlagService
from scripts import load_feature_flags as loader


def write_config(tmp_path: Path, config: dict) -> Path:
    config_path = tmp_path / "feature_flags.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    return config_path


@pytest.fixture
def mock_uow() -> MagicMock:
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)
    uow.set_tenant_context = AsyncMock()
    uow.commit = AsyncMock()
    uow.feature_flags = MagicMock(
        seed_missing=AsyncMock(side_effect=lambda flags: len(flags))
    )
    return uow


class TestSeedFeatureFlags:
    @pytest.mark.asyncio
    async def test_seeds_single_and_multiple_flags_and_commits(
        self, tmp_path: Path, mock_uow: MagicMock
    ):
        flags = [
            {"name": "use_v2_workspace", "enabled": False, "description": "v2 switch"},
            {"name": "new_dashboard", "enabled": True},
        ]
        config_path = write_config(tmp_path, {"flags": flags})

        inserted = await FeatureFlagService(mock_uow).seed_from_config(config_path)

        assert inserted == 2
        mock_uow.set_tenant_context.assert_awaited_once_with(
            None, bypass_rls=True, actor_type="system"
        )
        mock_uow.feature_flags.seed_missing.assert_awaited_once_with(flags)
        mock_uow.commit.assert_awaited_once()
        mock_uow.__aexit__.assert_awaited_once()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "payload", [{}, {"flags": []}], ids=["missing_key", "empty_list"]
    )
    async def test_empty_configuration_skips_db_transaction(
        self, tmp_path: Path, mock_uow: MagicMock, payload: dict
    ):
        config_path = write_config(tmp_path, payload)

        inserted = await FeatureFlagService(mock_uow).seed_from_config(config_path)

        assert inserted == 0
        mock_uow.__aenter__.assert_not_awaited()
        mock_uow.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_missing_config_file_returns_zero_without_opening_db(
        self, tmp_path: Path, mock_uow: MagicMock
    ):
        missing_path = tmp_path / "missing.json"

        inserted = await FeatureFlagService(mock_uow).seed_from_config(missing_path)

        assert inserted == 0
        mock_uow.__aenter__.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_invalid_json_raises_before_opening_db(
        self, tmp_path: Path, mock_uow: MagicMock
    ):
        config_path = tmp_path / "feature_flags.json"
        config_path.write_text("{invalid json", encoding="utf-8")

        with pytest.raises(json.JSONDecodeError):
            await FeatureFlagService(mock_uow).seed_from_config(config_path)

        mock_uow.__aenter__.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_database_seed_failure_propagates_and_exits_uow(
        self, tmp_path: Path, mock_uow: MagicMock
    ):
        config_path = write_config(
            tmp_path, {"flags": [{"name": "broken_flag", "enabled": True}]}
        )
        mock_uow.feature_flags.seed_missing.side_effect = RuntimeError("insert failed")

        with pytest.raises(RuntimeError, match="insert failed"):
            await FeatureFlagService(mock_uow).seed_from_config(config_path)

        mock_uow.commit.assert_not_awaited()
        mock_uow.__aexit__.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_database_commit_failure_propagates(
        self, tmp_path: Path, mock_uow: MagicMock
    ):
        config_path = write_config(
            tmp_path, {"flags": [{"name": "commit_flag", "enabled": True}]}
        )
        mock_uow.commit.side_effect = RuntimeError("commit failed")

        with pytest.raises(RuntimeError, match="commit failed"):
            await FeatureFlagService(mock_uow).seed_from_config(config_path)

        mock_uow.commit.assert_awaited_once()
        mock_uow.__aexit__.assert_awaited_once()


class TestLoadFeatureFlagsScript:
    def test_main_runs_seed_disposes_engine_and_prints_count(
        self, capsys: pytest.CaptureFixture[str]
    ):
        fake_engine = MagicMock(dispose=AsyncMock())
        fake_service = MagicMock(seed_from_config=AsyncMock(return_value=2))

        with (
            patch.object(loader, "build_async_engine", return_value=fake_engine),
            patch.object(loader, "build_session_factory", return_value=MagicMock()),
            patch.object(loader, "SqlAlchemyUnitOfWork", return_value=MagicMock()),
            patch.object(loader, "FeatureFlagService", return_value=fake_service),
        ):
            loader.main()

        fake_service.seed_from_config.assert_awaited_once()
        fake_engine.dispose.assert_awaited_once()
        assert "2 new flag(s) added" in capsys.readouterr().out

    def test_main_disposes_engine_even_when_seeding_fails(self):
        fake_engine = MagicMock(dispose=AsyncMock())
        fake_service = MagicMock(
            seed_from_config=AsyncMock(side_effect=RuntimeError("db down"))
        )

        with (
            patch.object(loader, "build_async_engine", return_value=fake_engine),
            patch.object(loader, "build_session_factory", return_value=MagicMock()),
            patch.object(loader, "SqlAlchemyUnitOfWork", return_value=MagicMock()),
            patch.object(loader, "FeatureFlagService", return_value=fake_service),
            pytest.raises(RuntimeError, match="db down"),
        ):
            loader.main()

        fake_engine.dispose.assert_awaited_once()
