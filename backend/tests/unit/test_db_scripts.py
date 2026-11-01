# 50% or more AI-generated
from unittest.mock import MagicMock, patch

import pytest

import scripts.provision_db_credentials as provision_module
import scripts.seed_db as seed_module

# ------------------------------------------------------------------
# provision_credentials
# ------------------------------------------------------------------


def test_provision_credentials_success(capsys):
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = (1,)

    with patch.object(
        provision_module,
        "get_admin_connection",
    ) as get_connection:
        get_connection.return_value.__enter__.return_value = conn

        provision_module.provision_credentials(
            username="orbit_test",
            password="test-password",
        )

    conn.execute.assert_any_call(
        """
            SELECT 1
            FROM pg_roles
            WHERE rolname = %s
            """,
        ("orbit_test",),
    )

    conn.commit.assert_called_once()

    assert "Successfully provisioned credentials for orbit_test." in (
        capsys.readouterr().out
    )


@pytest.mark.parametrize(
    "username",
    [
        "postgres",
        "admin",
        "root",
        "invalid_role",
    ],
)
def test_provision_credentials_rejects_unauthorized_role(username):
    with pytest.raises(
        ValueError,
        match="Unexpected application database role",
    ):
        provision_module.provision_credentials(
            username=username,
            password="test-password",
        )


@pytest.mark.parametrize("password", [""])
def test_provision_credentials_rejects_empty_password(password):
    with pytest.raises(
        ValueError,
        match="DB_PASSWORD must not be empty",
    ):
        provision_module.provision_credentials(
            username="orbit_test",
            password=password,
        )


def test_provision_credentials_rejects_missing_database_role():
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = None

    with patch.object(
        provision_module,
        "get_admin_connection",
    ) as get_connection:
        get_connection.return_value.__enter__.return_value = conn

        with pytest.raises(
            RuntimeError,
            match="Database role 'orbit_test' does not exist",
        ):
            provision_module.provision_credentials(
                username="orbit_test",
                password="test-password",
            )

    conn.commit.assert_not_called()


def test_provision_credentials_uses_default_settings():
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = (1,)

    with (
        patch.object(
            provision_module,
            "get_admin_connection",
        ) as get_connection,
        patch.object(
            provision_module,
            "settings",
        ) as mock_settings,
    ):
        mock_settings.DB_USER = "orbit_app"
        mock_settings.DB_PASSWORD = "app-password"

        get_connection.return_value.__enter__.return_value = conn

        provision_module.provision_credentials()

    conn.commit.assert_called_once()


# ------------------------------------------------------------------
# seed_db
# ------------------------------------------------------------------


def test_seed_data_commits_database_session():
    db = MagicMock()

    seed_module.seed_data(db)

    db.commit.assert_called_once()


def test_main_skips_seeding_in_production(caplog):
    with (
        patch.object(seed_module, "settings") as mock_settings,
        patch.object(seed_module, "SessionLocal") as session_local,
    ):
        mock_settings.ENVIRONMENT = "production"

        with pytest.raises(SystemExit) as exc:
            seed_module.main()

    assert exc.value.code == 0
    session_local.assert_not_called()

    assert (
        "Skipping seed_db: refusing to seed in production environment." in caplog.text
    )
