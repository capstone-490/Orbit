# app/services/clients.py
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid7

from app.domain.entities import Client
from app.domain.enums import ClientStatus, OnboardingStage
from app.domain.exceptions import ClientNotFoundError
from app.domain.uow import AbstractUnitOfWork

UNSET = object()


class ClientService:
    def __init__(self, uow: AbstractUnitOfWork) -> None:
        self._uow = uow

    async def list_clients(
        self,
        *,
        organization_id: UUID,
        subscription_id: UUID,
        advisor_membership_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Client]:
        async with self._uow as uow:
            await uow.set_tenant_context(organization_id)
            return await uow.clients.list_by_subscription(
                organization_id,
                subscription_id,
                advisor_membership_id=advisor_membership_id,
                limit=limit,
                offset=offset,
            )

    async def get_client(
        self,
        *,
        organization_id: UUID,
        subscription_id: UUID,
        client_id: UUID,
    ) -> Client:
        async with self._uow as uow:
            await uow.set_tenant_context(organization_id)
            client = await uow.clients.get_by_id(
                organization_id, subscription_id, client_id
            )
            if client is None:
                raise ClientNotFoundError(f"Client {client_id} not found.")
            return client

    async def create_client(
        self,
        *,
        organization_id: UUID,
        subscription_id: UUID,
        display_name: str,
        email: str | None = None,
        phone: str | None = None,
        address: str | None = None,
        date_of_birth: date | None = None,
        occupation: str | None = None,
        onboarding_stage: OnboardingStage | None = None,
        primary_advisor_membership_id: UUID | None = None,
    ) -> Client:
        client = Client(
            id=uuid7(),
            organization_id=organization_id,
            subscription_id=subscription_id,
            display_name=display_name,
            email=email,
            phone=phone,
            address=address,
            date_of_birth=date_of_birth,
            occupation=occupation,
            onboarding_stage=onboarding_stage,
            primary_advisor_membership_id=primary_advisor_membership_id,
            status=ClientStatus.ACTIVE,
        )

        async with self._uow as uow:
            await uow.set_tenant_context(organization_id)
            await uow.clients.add(client)
            await uow.commit()
            return client

    async def update_client(
        self,
        *,
        organization_id: UUID,
        subscription_id: UUID,
        client_id: UUID,
        display_name: str | None = None,
        email: str | object = UNSET,
        phone: str | object = UNSET,
        address: str | object = UNSET,
        date_of_birth: date | object = UNSET,
        occupation: str | object = UNSET,
        onboarding_stage: OnboardingStage | object = UNSET,
        status: ClientStatus | None = None,
    ) -> Client:
        """
        Partial update (`PATCH`): only fields explicitly passed (not `UNSET`) are modified.
        """
        async with self._uow as uow:
            await uow.set_tenant_context(organization_id)
            client = await uow.clients.get_by_id(
                organization_id, subscription_id, client_id, for_update=True
            )
            if client is None:
                raise ClientNotFoundError(f"Client {client_id} not found.")

            if display_name is not None:
                client.display_name = display_name.strip()
            if email is not UNSET:
                client.email = str(email).strip().lower() if email else None
            if phone is not UNSET:
                client.phone = str(phone).strip() if phone else None
            if address is not UNSET:
                client.address = str(address).strip() if address else None
            if date_of_birth is not UNSET:
                client.date_of_birth = date_of_birth  # type: ignore[assignment]
            if occupation is not UNSET:
                client.occupation = str(occupation).strip() if occupation else None
            if onboarding_stage is not UNSET:
                client.onboarding_stage = onboarding_stage  # type: ignore[assignment]
            if status is not None and status != ClientStatus.DELETED:
                client.status = status

            # re-validate invariants after mutation
            client.__post_init__()

            await uow.clients.save(client)
            await uow.commit()
            return client

    async def delete_client(
        self,
        *,
        organization_id: UUID,
        subscription_id: UUID,
        client_id: UUID,
        now: datetime,
    ) -> Client:
        """Soft-deletes a client (`status = 'deleted'`, `deleted_at = now`)."""
        async with self._uow as uow:
            await uow.set_tenant_context(organization_id)
            client = await uow.clients.get_by_id(
                organization_id, subscription_id, client_id, for_update=True
            )
            if client is None:
                raise ClientNotFoundError(f"Client {client_id} not found.")

            client.soft_delete(now=now)
            await uow.clients.save(client)
            await uow.commit()
            return client
