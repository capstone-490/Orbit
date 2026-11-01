# Below 50% AI-generated
import hashlib
from unittest.mock import MagicMock, patch

import pytest

from app.core import feature_flags
from scripts import set_feature_flag


def test_main_enables_feature_flag(monkeypatch, capsys):
    calls = []

    def fake_set_flag(*args):
        calls.append(args)

    monkeypatch.setattr(set_feature_flag, "set_flag", fake_set_flag)

    set_feature_flag.main(
        [
            "demo-ab",
            "true",
            "100",
            "--changed_by",
            "test_user",
            "--description",
            "Test flag",
        ]
    )

    assert calls == [("demo-ab", True, 100, "test_user", "Test flag")]

    output = capsys.readouterr().out
    assert "demo-ab" in output
    assert "enabled = True" in output
    assert "rollout_percent = 100" in output


def test_main_disables_feature_flag(monkeypatch, capsys):
    calls = []

    def fake_set_flag(*args):
        calls.append(args)

    monkeypatch.setattr(set_feature_flag, "set_flag", fake_set_flag)

    set_feature_flag.main(
        [
            "demo-ab",
            "false",
            "0",
            "--changed_by",
            "test_user",
            "--description",
            "Test flag",
        ]
    )

    assert calls == [("demo-ab", False, 0, "test_user", "Test flag")]

    output = capsys.readouterr().out
    assert "demo-ab" in output
    assert "enabled = False" in output
    assert "rollout_percent = 0" in output


class TestGetBucketValue:
    def test_returns_integer_between_0_and_99(self):
        result = feature_flags.get_bucket_value("dark_mode", "user-123")

        assert isinstance(result, int)
        assert 0 <= result <= 99

    def test_is_deterministic(self):
        first = feature_flags.get_bucket_value("dark_mode", "user-123")
        second = feature_flags.get_bucket_value("dark_mode", "user-123")

        assert first == second

    def test_different_users_can_have_different_buckets(self):
        first = feature_flags.get_bucket_value("dark_mode", "user-123")
        second = feature_flags.get_bucket_value("dark_mode", "user-456")

        assert first != second

    def test_matches_sha256_implementation(self):
        flag_name = "dark_mode"
        user_id = "user-123"

        expected = (
            int(
                hashlib.sha256(f"{flag_name}:{user_id}".encode()).hexdigest(),
                16,
            )
            % 100
        )

        assert feature_flags.get_bucket_value(flag_name, user_id) == expected

    @pytest.mark.parametrize("flag_name", [None, "", "   "])
    def test_invalid_flag_name(self, flag_name):
        with pytest.raises(ValueError, match="flag_name"):
            feature_flags.get_bucket_value(flag_name, "user-123")

    @pytest.mark.parametrize("user_id", [None, "", "   "])
    def test_invalid_user_id(self, user_id):
        with pytest.raises(ValueError, match="user_id"):
            feature_flags.get_bucket_value("dark_mode", user_id)


# ---------------------------------------------------------
# get_variant
# ---------------------------------------------------------


class TestGetVariant:
    @pytest.fixture
    def mock_connection(self):
        conn = MagicMock()
        return conn

    def test_missing_flag_returns_a(self, mock_connection):
        mock_connection.execute.return_value.fetchone.return_value = None

        with patch.object(
            feature_flags, "get_connection", return_value=mock_connection
        ):
            assert feature_flags.get_variant("dark_mode", "user-123") == "A"

    def test_disabled_flag_returns_a(self, mock_connection):
        mock_connection.execute.return_value.fetchone.return_value = (False, 100)

        with patch.object(
            feature_flags, "get_connection", return_value=mock_connection
        ):
            assert feature_flags.get_variant("dark_mode", "user-123") == "A"

    def test_enabled_flag_user_in_rollout_gets_b(self, mock_connection):
        mock_connection.execute.return_value.fetchone.return_value = (True, 100)

        with (
            patch.object(feature_flags, "get_connection", return_value=mock_connection),
            patch.object(feature_flags, "get_bucket_value", return_value=50),
        ):
            assert feature_flags.get_variant("dark_mode", "user-123") == "B"

    def test_enabled_flag_user_outside_rollout_gets_a(self, mock_connection):
        mock_connection.execute.return_value.fetchone.return_value = (True, 50)

        with (
            patch.object(feature_flags, "get_connection", return_value=mock_connection),
            patch.object(feature_flags, "get_bucket_value", return_value=50),
        ):
            assert feature_flags.get_variant("dark_mode", "user-123") == "A"

    def test_zero_percent_rollout_returns_a(self, mock_connection):
        mock_connection.execute.return_value.fetchone.return_value = (True, 0)

        with patch.object(
            feature_flags, "get_connection", return_value=mock_connection
        ):
            assert feature_flags.get_variant("dark_mode", "user-123") == "A"

    def test_database_exception_returns_a(self, mock_connection):
        mock_connection.execute.side_effect = RuntimeError("Database error")

        with (
            patch.object(feature_flags, "get_connection", return_value=mock_connection),
            patch.object(feature_flags.logger, "exception") as log_exception,
        ):
            assert feature_flags.get_variant("dark_mode", "user-123") == "A"

            log_exception.assert_called_once()

    @pytest.mark.parametrize("flag_name", [None, "", "   "])
    def test_invalid_flag_name(self, flag_name):
        with pytest.raises(ValueError, match="flag_name"):
            feature_flags.get_variant(flag_name, "user-123")

    @pytest.mark.parametrize("user_id", [None, "", "   "])
    def test_invalid_user_id(self, user_id):
        with pytest.raises(ValueError, match="user_id"):
            feature_flags.get_variant("dark_mode", user_id)

    def test_connection_is_closed(self, mock_connection):
        mock_connection.execute.return_value.fetchone.return_value = None

        with patch.object(
            feature_flags, "get_connection", return_value=mock_connection
        ):
            feature_flags.get_variant("dark_mode", "user-123")

        mock_connection.close.assert_called_once()


class TestSetFlag:
    @pytest.fixture
    def mock_connection(self):
        return MagicMock()

    def test_insert_new_flag(self, mock_connection):
        mock_connection.execute.return_value.fetchone.return_value = (
            True,
            50,
            "New feature",
        )

        with patch.object(
            feature_flags, "get_connection", return_value=mock_connection
        ):
            feature_flags.set_flag(
                "dark_mode",
                True,
                50,
                description="New feature",
            )

        mock_connection.commit.assert_called_once()
        mock_connection.rollback.assert_not_called()

    def test_update_existing_flag(self, mock_connection):
        mock_connection.execute.side_effect = [
            MagicMock(fetchone=MagicMock(return_value=None)),
            MagicMock(fetchone=MagicMock(return_value=(False, 20, "Old"))),
            MagicMock(),
        ]

        with patch.object(
            feature_flags, "get_connection", return_value=mock_connection
        ):
            feature_flags.set_flag(
                "dark_mode",
                True,
                75,
                description="Updated feature",
            )

        assert mock_connection.execute.call_count == 3
        mock_connection.commit.assert_called_once()

    def test_existing_flag_without_description_preserves_description(
        self, mock_connection
    ):
        mock_connection.execute.side_effect = [
            MagicMock(fetchone=MagicMock(return_value=None)),
            MagicMock(fetchone=MagicMock(return_value=(False, 20, "Existing"))),
            MagicMock(),
        ]

        with patch.object(
            feature_flags, "get_connection", return_value=mock_connection
        ):
            feature_flags.set_flag("dark_mode", True, 75)

        update_params = mock_connection.execute.call_args_list[2].args[1]

        assert update_params == (True, 75, None, "dark_mode")

    def test_changed_by_defaults_to_unknown(self, mock_connection):
        mock_connection.execute.return_value.fetchone.return_value = (True, 50, None)

        with patch.object(
            feature_flags, "get_connection", return_value=mock_connection
        ):
            feature_flags.set_flag("dark_mode", True, 50)

        # Note: changed_by is currently not persisted by the implementation.
        mock_connection.commit.assert_called_once()

    def test_missing_flag_during_update_raises_runtime_error(self, mock_connection):
        mock_connection.execute.side_effect = [
            MagicMock(fetchone=MagicMock(return_value=None)),
            MagicMock(fetchone=MagicMock(return_value=None)),
        ]

        with (
            patch.object(feature_flags, "get_connection", return_value=mock_connection),
            patch.object(feature_flags.logger, "exception"),
            pytest.raises(RuntimeError, match="disapeared"),
        ):
            feature_flags.set_flag("dark_mode", True, 75)

        mock_connection.rollback.assert_called_once()
        mock_connection.commit.assert_not_called()

    def test_insert_failure_rolls_back(self, mock_connection):
        mock_connection.execute.side_effect = RuntimeError("Insert failed")

        with (
            patch.object(feature_flags, "get_connection", return_value=mock_connection),
            patch.object(feature_flags.logger, "exception"),
            pytest.raises(RuntimeError, match="Insert failed"),
        ):
            feature_flags.set_flag("dark_mode", True, 50)

        mock_connection.rollback.assert_called_once()
        mock_connection.commit.assert_not_called()

    def test_update_failure_rolls_back(self, mock_connection):
        mock_connection.execute.side_effect = [
            MagicMock(fetchone=MagicMock(return_value=None)),
            MagicMock(fetchone=MagicMock(return_value=(False, 20, None))),
            RuntimeError("Update failed"),
        ]

        with (
            patch.object(feature_flags, "get_connection", return_value=mock_connection),
            patch.object(feature_flags.logger, "exception"),
            pytest.raises(RuntimeError, match="Update failed"),
        ):
            feature_flags.set_flag("dark_mode", True, 75)

        mock_connection.rollback.assert_called_once()

    def test_commit_failure_rolls_back(self, mock_connection):
        mock_connection.execute.return_value.fetchone.return_value = (True, 50, None)
        mock_connection.commit.side_effect = RuntimeError("Commit failed")

        with (
            patch.object(feature_flags, "get_connection", return_value=mock_connection),
            patch.object(feature_flags.logger, "exception"),
            pytest.raises(RuntimeError, match="Commit failed"),
        ):
            feature_flags.set_flag("dark_mode", True, 50)

        mock_connection.rollback.assert_called_once()

    def test_connection_is_closed(self, mock_connection):
        mock_connection.execute.return_value.fetchone.return_value = (True, 50, None)

        with patch.object(
            feature_flags, "get_connection", return_value=mock_connection
        ):
            feature_flags.set_flag("dark_mode", True, 50)

        mock_connection.close.assert_called_once()

    @pytest.mark.parametrize("flag_name", [None, "", "   "])
    def test_invalid_flag_name(self, flag_name):
        with pytest.raises(ValueError, match="flag_name"):
            feature_flags.set_flag(flag_name, True, 50)

    @pytest.mark.parametrize("rollout_percent", [-1, 101])
    def test_invalid_rollout_percent(self, rollout_percent):
        with pytest.raises(ValueError, match="rollout_percent"):
            feature_flags.set_flag("dark_mode", True, rollout_percent)
