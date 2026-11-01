import json
from unittest.mock import MagicMock, patch

import pytest

from scripts import load_feature_flags as loader


class TestLoadFeatureFlags:
    @pytest.fixture
    def mock_connection(self):
        connection = MagicMock()

        with patch.object(loader, "get_connection") as mock_get_connection:
            mock_get_connection.return_value.__enter__.return_value = connection

            yield connection

            mock_get_connection.assert_called_once()

    def write_config(self, tmp_path, config):
        """Create a temporary feature flags configuration."""
        config_path = tmp_path / "feature_flags.json"
        config_path.write_text(
            json.dumps(config),
            encoding="utf-8",
        )

        return config_path

    def test_loads_single_feature_flag(self, tmp_path, mock_connection):
        """Loads one feature flag and commits."""
        config = {
            "flags": [
                {
                    "name": "new_dashboard",
                    "enabled": True,
                    "rollout_percent": 50,
                    "description": "New dashboard",
                }
            ]
        }

        config_path = self.write_config(tmp_path, config)

        with patch.object(loader, "CONFIG_PATH", config_path):
            loader.load_feature_flags()

        assert mock_connection.execute.call_count == 2

        calls = mock_connection.execute.call_args_list

        assert "SET LOCAL app.bypass_rls = 'on'" in str(calls[0])

        insert_call = calls[1]

        assert "INSERT INTO feature_flags" in str(insert_call[0][0])

        assert insert_call[0][1] == (
            "new_dashboard",
            True,
            50,
            "New dashboard",
        )

        mock_connection.commit.assert_called_once()

    def test_loads_multiple_feature_flags(self, tmp_path, mock_connection):
        """Loads multiple feature flags in one transaction."""
        config = {
            "flags": [
                {
                    "name": "flag_one",
                    "enabled": True,
                    "rollout_percent": 100,
                },
                {
                    "name": "flag_two",
                    "enabled": False,
                    "rollout_percent": 0,
                },
                {
                    "name": "flag_three",
                    "enabled": True,
                    "rollout_percent": 25,
                    "description": "Third flag",
                },
            ]
        }

        config_path = self.write_config(tmp_path, config)

        with patch.object(loader, "CONFIG_PATH", config_path):
            loader.load_feature_flags()

        # One RLS bypass + three INSERT statements.
        assert mock_connection.execute.call_count == 4

        calls = mock_connection.execute.call_args_list

        assert calls[1][0][1] == (
            "flag_one",
            True,
            100,
            None,
        )

        assert calls[2][0][1] == (
            "flag_two",
            False,
            0,
            None,
        )

        assert calls[3][0][1] == (
            "flag_three",
            True,
            25,
            "Third flag",
        )

        mock_connection.commit.assert_called_once()

    def test_missing_flags_key_loads_empty_configuration(
        self, tmp_path, mock_connection
    ):
        """Missing flags key defaults to an empty list."""
        config_path = self.write_config(tmp_path, {})

        with patch.object(loader, "CONFIG_PATH", config_path):
            loader.load_feature_flags()

        # Only the RLS bypass statement.
        mock_connection.execute.assert_called_once()

        mock_connection.commit.assert_called_once()

    def test_empty_flags_list(self, tmp_path, mock_connection):
        """Empty configuration still commits successfully."""
        config_path = self.write_config(tmp_path, {"flags": []})

        with patch.object(loader, "CONFIG_PATH", config_path):
            loader.load_feature_flags()

        mock_connection.execute.assert_called_once()

        mock_connection.commit.assert_called_once()

    def test_missing_config_file_raises(self, tmp_path):
        """Missing configuration file propagates FileNotFoundError."""
        missing_path = tmp_path / "missing.json"

        with (  # noqa: SIM117
            patch.object(loader, "CONFIG_PATH", missing_path),
            patch.object(loader, "get_connection") as mock_get_connection,
        ):
            with pytest.raises(FileNotFoundError):
                loader.load_feature_flags()

        # File loading fails before opening a database connection.
        mock_get_connection.assert_not_called()

    def test_invalid_json_raises(self, tmp_path):
        """Invalid JSON propagates JSONDecodeError."""
        config_path = tmp_path / "feature_flags.json"
        config_path.write_text("{invalid json", encoding="utf-8")

        with (  # noqa: SIM117
            patch.object(loader, "CONFIG_PATH", config_path),
            patch.object(loader, "get_connection") as mock_get_connection,
        ):
            with pytest.raises(json.JSONDecodeError):
                loader.load_feature_flags()

        mock_get_connection.assert_not_called()

    def test_missing_required_flag_field_raises(self, tmp_path, mock_connection):
        """Missing required fields propagate KeyError."""
        config = {
            "flags": [
                {
                    "name": "incomplete_flag",
                    "enabled": True,
                    # rollout_percent intentionally missing
                }
            ]
        }

        config_path = self.write_config(tmp_path, config)

        with patch.object(loader, "CONFIG_PATH", config_path):  # noqa: SIM117
            with pytest.raises(KeyError, match="rollout_percent"):
                loader.load_feature_flags()

        # Bypass was configured, but INSERT and commit never happened.
        mock_connection.execute.assert_called_once()
        mock_connection.commit.assert_not_called()

    def test_database_insert_failure_propagates(self, tmp_path, mock_connection):
        """Database errors are not swallowed."""
        config = {
            "flags": [
                {
                    "name": "broken_flag",
                    "enabled": True,
                    "rollout_percent": 50,
                }
            ]
        }

        config_path = self.write_config(tmp_path, config)

        mock_connection.execute.side_effect = [
            None,
            RuntimeError("database insert failed"),
        ]

        with patch.object(loader, "CONFIG_PATH", config_path):  # noqa: SIM117
            with pytest.raises(RuntimeError, match="database insert failed"):
                loader.load_feature_flags()

        mock_connection.commit.assert_not_called()

    def test_database_commit_failure_propagates(self, tmp_path, mock_connection):
        """Commit failures propagate to the caller."""
        config = {
            "flags": [
                {
                    "name": "commit_flag",
                    "enabled": True,
                    "rollout_percent": 100,
                }
            ]
        }

        config_path = self.write_config(tmp_path, config)

        mock_connection.commit.side_effect = RuntimeError("commit failed")

        with patch.object(loader, "CONFIG_PATH", config_path):  # noqa: SIM117
            with pytest.raises(RuntimeError, match="commit failed"):
                loader.load_feature_flags()

        mock_connection.commit.assert_called_once()

    def test_connection_context_exits_after_success(self, tmp_path, mock_connection):
        config_path = self.write_config(tmp_path, {"flags": []})

        with patch.object(loader, "CONFIG_PATH", config_path):
            loader.load_feature_flags()

        mock_connection.commit.assert_called_once()

    def test_connection_context_exits_after_insert_failure(self, tmp_path):
        config_path = self.write_config(
            tmp_path,
            {
                "flags": [
                    {
                        "name": "broken",
                        "enabled": True,
                        "rollout_percent": 50,
                    }
                ]
            },
        )

        connection = MagicMock()
        connection.execute.side_effect = [
            None,
            RuntimeError("insert failed"),
        ]

        with (
            patch.object(loader, "CONFIG_PATH", config_path),
            patch.object(loader, "get_connection") as mock_get_connection,
        ):
            mock_get_connection.return_value.__enter__.return_value = connection

            with pytest.raises(RuntimeError, match="insert failed"):
                loader.load_feature_flags()

            mock_get_connection.return_value.__exit__.assert_called_once()
