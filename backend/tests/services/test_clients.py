# 50 % or more Ai-generated code
from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

import app.services.clients as clients_module
from app.domain.enums import ClientStatus, OnboardingStage
from app.domain.exceptions import ClientNotFoundError
from app.services.clients import ClientService


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
def mock_client():
    client = SimpleNamespace(
        id=UUID("55555555-5555-4555-8555-555555555555"),
        display_name="John Doe",
        email="john@example.com",
        phone="1234567890",
        address="123 Main Street",
        date_of_birth=date(1990, 1, 1),
        occupation="Engineer",
        onboarding_stage=None,
        primary_advisor_membership_id=None,
        status=ClientStatus.ACTIVE,
        deleted_at=None,
    )
    client.__post_init__ = MagicMock()

    def soft_delete(*, now):
        client.status = ClientStatus.DELETED
        client.deleted_at = now

    client.soft_delete = MagicMock(side_effect=soft_delete)

    return client


@pytest.fixture
def mock_uow():
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)

    uow.set_tenant_context = AsyncMock()
    uow.commit = AsyncMock()

    uow.clients = MagicMock()
    uow.clients.list_by_subscription = AsyncMock(return_value=[])
    uow.clients.get_by_id = AsyncMock(return_value=None)
    uow.clients.add = AsyncMock()
    uow.clients.save = AsyncMock()

    return uow


@pytest.fixture
def service(mock_uow):
    return ClientService(mock_uow)


@pytest.mark.asyncio
async def test_list_clients(
    service,
    mock_uow,
    organization_id,
    subscription_id,
    advisor_id,
    mock_client,
):
    mock_uow.clients.list_by_subscription.return_value = [mock_client]

    result = await service.list_clients(
        organization_id=organization_id,
        subscription_id=subscription_id,
        advisor_membership_id=advisor_id,
        limit=20,
        offset=10,
    )

    assert result == [mock_client]

    mock_uow.set_tenant_context.assert_awaited_once_with(organization_id)

    mock_uow.clients.list_by_subscription.assert_awaited_once_with(
        organization_id,
        subscription_id,
        advisor_membership_id=advisor_id,
        limit=20,
        offset=10,
    )

    mock_uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_list_clients_with_default_pagination(
    service,
    mock_uow,
    organization_id,
    subscription_id,
):
    await service.list_clients(
        organization_id=organization_id,
        subscription_id=subscription_id,
    )

    mock_uow.clients.list_by_subscription.assert_awaited_once_with(
        organization_id,
        subscription_id,
        advisor_membership_id=None,
        limit=50,
        offset=0,
    )


@pytest.mark.asyncio
async def test_get_client(
    service,
    mock_uow,
    organization_id,
    subscription_id,
    client_id,
    mock_client,
):
    mock_uow.clients.get_by_id.return_value = mock_client

    result = await service.get_client(
        organization_id=organization_id,
        subscription_id=subscription_id,
        client_id=client_id,
    )

    assert result is mock_client

    mock_uow.set_tenant_context.assert_awaited_once_with(organization_id)

    mock_uow.clients.get_by_id.assert_awaited_once_with(
        organization_id,
        subscription_id,
        client_id,
    )


@pytest.mark.asyncio
async def test_get_client_not_found(
    service,
    mock_uow,
    organization_id,
    subscription_id,
    client_id,
):
    mock_uow.clients.get_by_id.return_value = None

    with pytest.raises(ClientNotFoundError, match="not found"):
        await service.get_client(
            organization_id=organization_id,
            subscription_id=subscription_id,
            client_id=client_id,
        )

    mock_uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_client(
    service,
    mock_uow,
    monkeypatch,
    organization_id,
    subscription_id,
    advisor_id,
):
    generated_id = UUID("66666666-6666-4666-8666-666666666666")
    monkeypatch.setattr(clients_module, "uuid7", lambda: generated_id)

    created_client = SimpleNamespace()

    def client_factory(**kwargs):
        created_client.__dict__.update(kwargs)
        return created_client

    monkeypatch.setattr(clients_module, "Client", client_factory)

    result = await service.create_client(
        organization_id=organization_id,
        subscription_id=subscription_id,
        display_name="Jane Doe",
        email="jane@example.com",
        phone="1234567890",
        address="456 Main Street",
        date_of_birth=date(1995, 5, 15),
        occupation="Developer",
        onboarding_stage=None,
        primary_advisor_membership_id=advisor_id,
    )

    assert result is created_client
    assert result.id == generated_id
    assert result.organization_id == organization_id
    assert result.subscription_id == subscription_id
    assert result.display_name == "Jane Doe"
    assert result.email == "jane@example.com"
    assert result.phone == "1234567890"
    assert result.address == "456 Main Street"
    assert result.date_of_birth == date(1995, 5, 15)
    assert result.occupation == "Developer"
    assert result.primary_advisor_membership_id == advisor_id
    assert result.status == ClientStatus.ACTIVE

    mock_uow.set_tenant_context.assert_awaited_once_with(organization_id)
    mock_uow.clients.add.assert_awaited_once_with(created_client)
    mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_client_with_optional_fields_omitted(
    service,
    mock_uow,
    monkeypatch,
    organization_id,
    subscription_id,
):
    monkeypatch.setattr(
        clients_module,
        "uuid7",
        lambda: UUID("77777777-7777-4777-8777-777777777777"),
    )

    created_client = SimpleNamespace()

    monkeypatch.setattr(
        clients_module,
        "Client",
        lambda **kwargs: created_client.__dict__.update(kwargs) or created_client,
    )

    result = await service.create_client(
        organization_id=organization_id,
        subscription_id=subscription_id,
        display_name="Jane Doe",
    )

    assert result.email is None
    assert result.phone is None
    assert result.address is None
    assert result.date_of_birth is None
    assert result.occupation is None
    assert result.onboarding_stage is None
    assert result.primary_advisor_membership_id is None
    assert result.status == ClientStatus.ACTIVE

    mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_client(
    service,
    mock_uow,
    organization_id,
    subscription_id,
    client_id,
    mock_client,
):
    mock_uow.clients.get_by_id.return_value = mock_client

    result = await service.update_client(
        organization_id=organization_id,
        subscription_id=subscription_id,
        client_id=client_id,
        display_name="  Jane Doe  ",
        email="  JANE@EXAMPLE.COM  ",
        phone="  9876543210  ",
        address="  456 New Street  ",
        occupation="  Designer  ",
        status=ClientStatus.INACTIVE,
    )

    assert result is mock_client
    assert mock_client.display_name == "Jane Doe"
    assert mock_client.email == "jane@example.com"
    assert mock_client.phone == "9876543210"
    assert mock_client.address == "456 New Street"
    assert mock_client.occupation == "Designer"
    assert mock_client.status == ClientStatus.INACTIVE

    mock_uow.clients.get_by_id.assert_awaited_once_with(
        organization_id,
        subscription_id,
        client_id,
        for_update=True,
    )

    mock_client.__post_init__.assert_called_once()
    mock_uow.clients.save.assert_awaited_once_with(mock_client)
    mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_client_unset_fields_remain_unchanged(
    service,
    mock_uow,
    organization_id,
    subscription_id,
    client_id,
    mock_client,
):
    original_values = {
        "display_name": mock_client.display_name,
        "email": mock_client.email,
        "phone": mock_client.phone,
        "address": mock_client.address,
        "occupation": mock_client.occupation,
    }

    mock_uow.clients.get_by_id.return_value = mock_client

    await service.update_client(
        organization_id=organization_id,
        subscription_id=subscription_id,
        client_id=client_id,
    )

    for field, original_value in original_values.items():
        assert getattr(mock_client, field) == original_value

    mock_uow.clients.save.assert_awaited_once_with(mock_client)
    mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_client_explicit_none_clears_optional_fields(
    service,
    mock_uow,
    organization_id,
    subscription_id,
    client_id,
    mock_client,
):
    mock_uow.clients.get_by_id.return_value = mock_client

    await service.update_client(
        organization_id=organization_id,
        subscription_id=subscription_id,
        client_id=client_id,
        email=None,
        phone=None,
        address=None,
        occupation=None,
    )

    assert mock_client.email is None
    assert mock_client.phone is None
    assert mock_client.address is None
    assert mock_client.occupation is None

    mock_uow.clients.save.assert_awaited_once_with(mock_client)
    mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_client_does_not_allow_deleted_status(
    service,
    mock_uow,
    organization_id,
    subscription_id,
    client_id,
    mock_client,
):
    mock_uow.clients.get_by_id.return_value = mock_client

    await service.update_client(
        organization_id=organization_id,
        subscription_id=subscription_id,
        client_id=client_id,
        status=ClientStatus.DELETED,
    )

    assert mock_client.status == ClientStatus.ACTIVE
    mock_uow.clients.save.assert_awaited_once_with(mock_client)


@pytest.mark.asyncio
async def test_update_client_updates_date_and_onboarding_stage(
    service,
    mock_uow,
    organization_id,
    subscription_id,
    client_id,
    mock_client,
):
    new_date = date(1985, 6, 20)
    stage = next(iter(OnboardingStage))

    mock_uow.clients.get_by_id.return_value = mock_client

    await service.update_client(
        organization_id=organization_id,
        subscription_id=subscription_id,
        client_id=client_id,
        date_of_birth=new_date,
        onboarding_stage=stage,
    )

    assert mock_client.date_of_birth == new_date
    assert mock_client.onboarding_stage == stage

    mock_uow.clients.save.assert_awaited_once_with(mock_client)


@pytest.mark.asyncio
async def test_update_client_not_found(
    service,
    mock_uow,
    organization_id,
    subscription_id,
    client_id,
):
    mock_uow.clients.get_by_id.return_value = None

    with pytest.raises(ClientNotFoundError, match="not found"):
        await service.update_client(
            organization_id=organization_id,
            subscription_id=subscription_id,
            client_id=client_id,
            display_name="Jane Doe",
        )

    mock_uow.clients.save.assert_not_awaited()
    mock_uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_client_validation_error_does_not_save(
    service,
    mock_uow,
    organization_id,
    subscription_id,
    client_id,
    mock_client,
):
    mock_uow.clients.get_by_id.return_value = mock_client
    mock_client.__post_init__.side_effect = ValueError("Invalid client")

    with pytest.raises(ValueError, match="Invalid client"):
        await service.update_client(
            organization_id=organization_id,
            subscription_id=subscription_id,
            client_id=client_id,
            display_name="Invalid",
        )

    mock_uow.clients.save.assert_not_awaited()
    mock_uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_client(
    service,
    mock_uow,
    organization_id,
    subscription_id,
    client_id,
    mock_client,
):
    now = datetime(2026, 11, 22, 12, 0, tzinfo=UTC)
    mock_uow.clients.get_by_id.return_value = mock_client

    result = await service.delete_client(
        organization_id=organization_id,
        subscription_id=subscription_id,
        client_id=client_id,
        now=now,
    )

    assert result is mock_client
    assert mock_client.status == ClientStatus.DELETED
    assert mock_client.deleted_at == now

    mock_uow.clients.get_by_id.assert_awaited_once_with(
        organization_id,
        subscription_id,
        client_id,
        for_update=True,
    )

    mock_client.soft_delete.assert_called_once_with(now=now)
    mock_uow.clients.save.assert_awaited_once_with(mock_client)
    mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_client_not_found(
    service,
    mock_uow,
    organization_id,
    subscription_id,
    client_id,
):
    mock_uow.clients.get_by_id.return_value = None

    now = datetime.now(UTC)

    with pytest.raises(ClientNotFoundError, match="not found"):
        await service.delete_client(
            organization_id=organization_id,
            subscription_id=subscription_id,
            client_id=client_id,
            now=now,
        )

    mock_uow.clients.save.assert_not_awaited()
    mock_uow.commit.assert_not_awaited()
