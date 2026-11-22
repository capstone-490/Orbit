from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from sqlalchemy.exc import DBAPIError

import app.infrastructure.repositories.client as repository_module
from app.domain.entities import Client
from app.domain.enums import ClientStatus, OnboardingStage
from app.domain.exceptions import DuplicateClientEmailError
from app.infrastructure.repositories.client import SqlAlchemyClientRepository


@pytest.fixture
def organization_id():
    return UUID("11111111-1111-4111-8111-111111111111")


@pytest.fixture
def subscription_id():
    return UUID("22222222-2222-4222-8222-222222222222")


@pytest.fixture
def client_id():
    return UUID("33333333-3333-4333-8333-333333333333")


@pytest.fixture
def advisor_id():
    return UUID("44444444-4444-4444-8444-444444444444")


@pytest.fixture
def timestamps():
    now = datetime(2026, 11, 22, 12, 0, tzinfo=UTC)
    return now, now


@pytest.fixture
def mock_session():
    session = MagicMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def repository(mock_session):
    return SqlAlchemyClientRepository(mock_session)


@pytest.fixture
def client(organization_id, subscription_id, client_id, advisor_id):
    return Client(
        id=client_id,
        organization_id=organization_id,
        subscription_id=subscription_id,
        display_name="John Doe",
        email="john@example.com",
        phone="1234567890",
        address="123 Main Street",
        date_of_birth=date(1990, 1, 1),
        occupation="Engineer",
        onboarding_stage=None,
        primary_advisor_membership_id=advisor_id,
        status=ClientStatus.ACTIVE,
    )


@pytest.fixture
def db_row(
    organization_id,
    subscription_id,
    client_id,
    advisor_id,
    timestamps,
):
    created_at, updated_at = timestamps

    return {
        "id": client_id,
        "organization_id": organization_id,
        "subscription_id": subscription_id,
        "display_name": "John Doe",
        "email": "john@example.com",
        "phone": "1234567890",
        "address": "123 Main Street",
        "date_of_birth": date(1990, 1, 1),
        "occupation": "Engineer",
        "onboarding_stage": None,
        "primary_advisor_membership_id": advisor_id,
        "status": "active",
        "created_at": created_at,
        "updated_at": updated_at,
        "deleted_at": None,
    }


def configure_result(mock_session, *, first=None, all_rows=None, one=None):
    result = MagicMock()
    mappings = MagicMock()

    mappings.first.return_value = first
    mappings.all.return_value = all_rows if all_rows is not None else []
    mappings.one.return_value = one

    result.mappings.return_value = mappings
    mock_session.execute.return_value = result

    return result


def make_dbapi_error():
    return DBAPIError(
        statement="INSERT INTO clients",
        params={},
        orig=Exception("Unique constraint violation"),
        connection_invalidated=False,
    )


@pytest.mark.asyncio
async def test_get_by_id_returns_client(
    repository,
    mock_session,
    organization_id,
    subscription_id,
    client_id,
    db_row,
):
    configure_result(mock_session, first=db_row)

    result = await repository.get_by_id(
        organization_id,
        subscription_id,
        client_id,
    )

    assert isinstance(result, Client)
    assert result.id == client_id
    assert result.display_name == "John Doe"
    assert result.email == "john@example.com"
    assert result.status == ClientStatus.ACTIVE

    mock_session.execute.assert_awaited_once()

    statement, params = mock_session.execute.await_args.args

    assert "organization_id = :org_id" in str(statement)
    assert "subscription_id = :sub_id" in str(statement)
    assert "id = :client_id" in str(statement)
    assert "deleted_at IS NULL" in str(statement)
    assert "FOR UPDATE" not in str(statement)

    assert params == {
        "org_id": organization_id,
        "sub_id": subscription_id,
        "client_id": client_id,
    }


@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_not_found(
    repository,
    mock_session,
    organization_id,
    subscription_id,
    client_id,
):
    configure_result(mock_session, first=None)

    result = await repository.get_by_id(
        organization_id,
        subscription_id,
        client_id,
    )

    assert result is None


@pytest.mark.asyncio
async def test_get_by_id_uses_for_update(
    repository,
    mock_session,
    organization_id,
    subscription_id,
    client_id,
    db_row,
):
    configure_result(mock_session, first=db_row)

    await repository.get_by_id(
        organization_id,
        subscription_id,
        client_id,
        for_update=True,
    )

    statement = mock_session.execute.await_args.args[0]

    assert "FOR UPDATE" in str(statement)


@pytest.mark.asyncio
async def test_get_by_id_without_for_update_does_not_lock(
    repository,
    mock_session,
    organization_id,
    subscription_id,
    client_id,
    db_row,
):
    configure_result(mock_session, first=db_row)

    await repository.get_by_id(
        organization_id,
        subscription_id,
        client_id,
        for_update=False,
    )

    statement = mock_session.execute.await_args.args[0]

    assert "FOR UPDATE" not in str(statement)


# list_by_subscription
@pytest.mark.asyncio
async def test_list_by_subscription_returns_clients(
    repository,
    mock_session,
    organization_id,
    subscription_id,
    advisor_id,
    db_row,
):
    configure_result(mock_session, all_rows=[db_row, db_row])

    result = await repository.list_by_subscription(
        organization_id,
        subscription_id,
        advisor_membership_id=advisor_id,
        limit=20,
        offset=10,
    )

    assert len(result) == 2
    assert all(isinstance(item, Client) for item in result)
    assert all(item.id == db_row["id"] for item in result)

    statement, params = mock_session.execute.await_args.args

    assert "organization_id = :org_id" in str(statement)
    assert "subscription_id = :sub_id" in str(statement)
    assert "deleted_at IS NULL" in str(statement)
    assert "ORDER BY created_at DESC" in str(statement)
    assert "LIMIT :limit OFFSET :offset" in str(statement)

    assert params == {
        "org_id": organization_id,
        "sub_id": subscription_id,
        "advisor_id": advisor_id,
        "limit": 20,
        "offset": 10,
    }


@pytest.mark.asyncio
async def test_list_by_subscription_with_default_pagination(
    repository,
    mock_session,
    organization_id,
    subscription_id,
):
    configure_result(mock_session, all_rows=[])

    result = await repository.list_by_subscription(
        organization_id,
        subscription_id,
    )

    assert result == []

    _, params = mock_session.execute.await_args.args

    assert params["advisor_id"] is None
    assert params["limit"] == 50
    assert params["offset"] == 0


@pytest.mark.asyncio
async def test_list_by_subscription_returns_empty_list(
    repository,
    mock_session,
    organization_id,
    subscription_id,
):
    configure_result(mock_session, all_rows=[])

    result = await repository.list_by_subscription(
        organization_id,
        subscription_id,
    )

    assert result == []


@pytest.mark.asyncio
async def test_list_by_subscription_without_advisor_filter(
    repository,
    mock_session,
    organization_id,
    subscription_id,
):
    configure_result(mock_session, all_rows=[])

    await repository.list_by_subscription(
        organization_id,
        subscription_id,
        advisor_membership_id=None,
    )

    statement, params = mock_session.execute.await_args.args

    assert "CAST(:advisor_id AS uuid) IS NULL" in str(statement)
    assert params["advisor_id"] is None


# add


@pytest.mark.asyncio
async def test_add_client(
    repository,
    mock_session,
    client,
    timestamps,
):
    created_at, updated_at = timestamps

    configure_result(
        mock_session,
        one={
            "created_at": created_at,
            "updated_at": updated_at,
        },
    )

    await repository.add(client)

    assert client.created_at == created_at
    assert client.updated_at == updated_at

    statement, params = mock_session.execute.await_args.args

    assert "INSERT INTO clients" in str(statement)
    assert "RETURNING created_at, updated_at" in str(statement)

    assert params["id"] == client.id
    assert params["org_id"] == client.organization_id
    assert params["sub_id"] == client.subscription_id
    assert params["display_name"] == client.display_name
    assert params["email"] == client.email
    assert params["phone"] == client.phone
    assert params["status"] == client.status.value
    assert params["advisor_id"] == client.primary_advisor_membership_id

    assert params["onboarding_stage"] is None


@pytest.mark.asyncio
async def test_add_client_with_onboarding_stage(
    repository,
    mock_session,
    client,
):
    stage = next(iter(OnboardingStage))
    client.onboarding_stage = stage

    configure_result(
        mock_session,
        one={
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        },
    )

    await repository.add(client)

    _, params = mock_session.execute.await_args.args

    assert params["onboarding_stage"] == stage.value


@pytest.mark.asyncio
async def test_add_client_translates_duplicate_email_error(
    repository,
    mock_session,
    client,
    monkeypatch,
):
    error = make_dbapi_error()

    mock_session.execute.side_effect = error

    monkeypatch.setattr(
        repository_module,
        "_is_unique_violation",
        lambda exc, constraint: constraint == "uq_clients_subscription_email",
    )

    with pytest.raises(DuplicateClientEmailError, match="already exists"):
        await repository.add(client)


@pytest.mark.asyncio
async def test_add_client_reraises_unrelated_db_error(
    repository,
    mock_session,
    client,
    monkeypatch,
):
    error = make_dbapi_error()
    mock_session.execute.side_effect = error

    monkeypatch.setattr(
        repository_module,
        "_is_unique_violation",
        lambda exc, constraint: False,
    )

    with pytest.raises(DBAPIError) as exc_info:
        await repository.add(client)

    assert exc_info.value is error


# save


@pytest.mark.asyncio
async def test_save_client(
    repository,
    mock_session,
    client,
    timestamps,
):
    updated_at = timestamps[1]

    configure_result(
        mock_session,
        first={"updated_at": updated_at},
    )

    await repository.save(client)

    assert client.updated_at == updated_at

    statement, params = mock_session.execute.await_args.args

    assert "UPDATE clients" in str(statement)
    assert "WHERE organization_id = :org_id" in str(statement)
    assert "AND subscription_id = :sub_id" in str(statement)
    assert "AND id = :id" in str(statement)
    assert "RETURNING updated_at" in str(statement)

    assert params["id"] == client.id
    assert params["org_id"] == client.organization_id
    assert params["sub_id"] == client.subscription_id
    assert params["display_name"] == client.display_name
    assert params["email"] == client.email
    assert params["status"] == client.status.value


@pytest.mark.asyncio
async def test_save_client_with_onboarding_stage(
    repository,
    mock_session,
    client,
):
    stage = next(iter(OnboardingStage))
    client.onboarding_stage = stage

    configure_result(
        mock_session,
        first={"updated_at": datetime.now(UTC)},
    )

    await repository.save(client)

    _, params = mock_session.execute.await_args.args

    assert params["onboarding_stage"] == stage.value


@pytest.mark.asyncio
async def test_save_client_without_returned_row(
    repository,
    mock_session,
    client,
):
    original_updated_at = datetime(2025, 1, 1, tzinfo=UTC)

    client.updated_at = original_updated_at

    configure_result(mock_session, first=None)

    await repository.save(client)

    assert client.updated_at == original_updated_at


@pytest.mark.asyncio
async def test_save_client_translates_duplicate_email_error(
    repository,
    mock_session,
    client,
    monkeypatch,
):
    error = make_dbapi_error()
    mock_session.execute.side_effect = error

    monkeypatch.setattr(
        repository_module,
        "_is_unique_violation",
        lambda exc, constraint: constraint == "uq_clients_subscription_email",
    )

    with pytest.raises(DuplicateClientEmailError, match="already exists"):
        await repository.save(client)


@pytest.mark.asyncio
async def test_save_client_reraises_unrelated_db_error(
    repository,
    mock_session,
    client,
    monkeypatch,
):
    error = make_dbapi_error()
    mock_session.execute.side_effect = error

    monkeypatch.setattr(
        repository_module,
        "_is_unique_violation",
        lambda exc, constraint: False,
    )

    with pytest.raises(DBAPIError) as exc_info:
        await repository.save(client)

    assert exc_info.value is error


# _row_to_entity


def test_row_to_entity_maps_all_fields(repository, db_row):
    result = repository._row_to_entity(db_row)

    assert isinstance(result, Client)
    assert result.id == db_row["id"]
    assert result.organization_id == db_row["organization_id"]
    assert result.subscription_id == db_row["subscription_id"]
    assert result.display_name == db_row["display_name"]
    assert result.email == db_row["email"]
    assert result.phone == db_row["phone"]
    assert result.address == db_row["address"]
    assert result.date_of_birth == db_row["date_of_birth"]
    assert result.occupation == db_row["occupation"]
    assert result.onboarding_stage is None
    assert (
        result.primary_advisor_membership_id == db_row["primary_advisor_membership_id"]
    )
    assert result.status == ClientStatus.ACTIVE
    assert result.created_at == db_row["created_at"]
    assert result.updated_at == db_row["updated_at"]
    assert result.deleted_at is None


def test_row_to_entity_converts_onboarding_stage(repository, db_row):
    stage = next(iter(OnboardingStage))
    db_row["onboarding_stage"] = stage.value

    result = repository._row_to_entity(db_row)

    assert result.onboarding_stage == stage


def test_row_to_entity_converts_status(repository, db_row):
    db_row["status"] = ClientStatus.INACTIVE.value

    result = repository._row_to_entity(db_row)

    assert result.status == ClientStatus.INACTIVE


def test_row_to_entity_converts_display_name_to_string(repository, db_row):
    db_row["display_name"] = 12345

    result = repository._row_to_entity(db_row)

    assert result.display_name == "12345"
    assert isinstance(result.display_name, str)


def test_row_to_entity_preserves_nullable_fields(repository, db_row):
    db_row.update(
        {
            "email": None,
            "phone": None,
            "address": None,
            "date_of_birth": None,
            "occupation": None,
            "onboarding_stage": None,
            "primary_advisor_membership_id": None,
            "deleted_at": None,
        }
    )

    result = repository._row_to_entity(db_row)

    assert result.email is None
    assert result.phone is None
    assert result.address is None
    assert result.date_of_birth is None
    assert result.occupation is None
    assert result.onboarding_stage is None
    assert result.primary_advisor_membership_id is None
    assert result.deleted_at is None
