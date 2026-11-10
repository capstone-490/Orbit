# Below 50% AI-generated code
from __future__ import annotations

from uuid import UUID

from sqlalchemy import RowMapping, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import Client
from app.domain.enums import ClientStatus, OnboardingStage
from app.domain.exceptions import DuplicateClientEmailError
from app.domain.repositories import AbstractClientRepository
from app.infrastructure.repositories.helpers import _is_unique_violation


class SqlAlchemyClientRepository(AbstractClientRepository):
    """
    SQLAlchemy 2.0 Async Repository for the clients table.
    Enforces composite tenant scoping (organization_id, subscription_id, id)
    and translates pgsql unique constraint violations into exceptions.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(
        self,
        organization_id: UUID,
        subscription_id: UUID,
        client_id: UUID,
        *,
        for_update: bool = False,
    ) -> Client | None:
        lock_clause = "FOR UPDATE" if for_update else ""
        stmt = text(
            f"""
            SELECT id, organization_id, subscription_id, display_name,
                   email, phone, address, date_of_birth, occupation,
                   onboarding_stage, primary_advisor_membership_id,
                   status, created_at, updated_at, deleted_at
            FROM clients
            WHERE organization_id = :org_id
              AND subscription_id = :sub_id
              AND id = :client_id
              AND deleted_at IS NULL
            {lock_clause}
            """
        )
        row = (
            (
                await self._session.execute(
                    stmt,
                    {
                        "org_id": organization_id,
                        "sub_id": subscription_id,
                        "client_id": client_id,
                    },
                )
            )
            .mappings()
            .first()
        )
        return self._row_to_entity(row) if row is not None else None

    # get clients belonging to the current subscription
    # optionally filter by advisor
    # limit and offset are used for pagination
    async def list_by_subscription(
        self,
        organization_id: UUID,
        subscription_id: UUID,
        *,
        advisor_membership_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Client]:
        stmt = text(
            """
            SELECT id, organization_id, subscription_id, display_name,
                   email, phone, address, date_of_birth, occupation,
                   onboarding_stage, primary_advisor_membership_id,
                   status, created_at, updated_at, deleted_at
            FROM clients
            WHERE organization_id = :org_id
              AND subscription_id = :sub_id
              AND deleted_at IS NULL
              AND (
                  CAST(:advisor_id AS uuid) IS NULL
                  OR primary_advisor_membership_id = CAST(:advisor_id AS uuid)
              )
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
            """
        )
        rows = (
            (
                await self._session.execute(
                    stmt,
                    {
                        "org_id": organization_id,
                        "sub_id": subscription_id,
                        "advisor_id": advisor_membership_id,
                        "limit": limit,
                        "offset": offset,
                    },
                )
            )
            .mappings()
            .all()
        )
        return [self._row_to_entity(row) for row in rows]

    async def add(self, client: Client) -> None:
        stmt = text(
            """
            INSERT INTO clients (
                id, organization_id, subscription_id, display_name,
                email, phone, address, date_of_birth, occupation,
                onboarding_stage, primary_advisor_membership_id,
                status, deleted_at
            ) VALUES (
                :id, :org_id, :sub_id, :display_name,
                :email, :phone, :address, :dob, :occupation,
                :onboarding_stage, :advisor_id,
                :status, :deleted_at
            )
            RETURNING created_at, updated_at
            """
        )
        try:
            row = (
                (
                    await self._session.execute(
                        stmt,
                        {
                            "id": client.id,
                            "org_id": client.organization_id,
                            "sub_id": client.subscription_id,
                            "display_name": client.display_name,
                            "email": client.email,
                            "phone": client.phone,
                            "address": client.address,
                            "dob": client.date_of_birth,
                            "occupation": client.occupation,
                            "onboarding_stage": (
                                client.onboarding_stage.value
                                if client.onboarding_stage is not None
                                else None
                            ),
                            "advisor_id": client.primary_advisor_membership_id,
                            "status": client.status.value,
                            "deleted_at": client.deleted_at,
                        },
                    )
                )
                .mappings()
                .one()
            )
            client.created_at = row["created_at"]
            client.updated_at = row["updated_at"]
        except DBAPIError as exc:
            if _is_unique_violation(exc, "uq_clients_subscription_email"):
                raise DuplicateClientEmailError(
                    f"An active client with email '{client.email}' already exists in this subscription."
                ) from exc
            raise

    async def save(self, client: Client) -> None:
        stmt = text(
            """
            UPDATE clients
            SET display_name = :display_name,
                email = :email,
                phone = :phone,
                address = :address,
                date_of_birth = :dob,
                occupation = :occupation,
                onboarding_stage = :onboarding_stage,
                primary_advisor_membership_id = :advisor_id,
                status = :status,
                deleted_at = :deleted_at
            WHERE organization_id = :org_id
              AND subscription_id = :sub_id
              AND id = :id
            RETURNING updated_at
            """
        )
        try:
            row = (
                (
                    await self._session.execute(
                        stmt,
                        {
                            "id": client.id,
                            "org_id": client.organization_id,
                            "sub_id": client.subscription_id,
                            "display_name": client.display_name,
                            "email": client.email,
                            "phone": client.phone,
                            "address": client.address,
                            "dob": client.date_of_birth,
                            "occupation": client.occupation,
                            "onboarding_stage": (
                                client.onboarding_stage.value
                                if client.onboarding_stage is not None
                                else None
                            ),
                            "advisor_id": client.primary_advisor_membership_id,
                            "status": client.status.value,
                            "deleted_at": client.deleted_at,
                        },
                    )
                )
                .mappings()
                .first()
            )
            if row is not None:
                client.updated_at = row["updated_at"]
        except DBAPIError as exc:
            if _is_unique_violation(exc, "uq_clients_subscription_email"):
                raise DuplicateClientEmailError(
                    f"An active client with email '{client.email}' already exists in this subscription."
                ) from exc
            raise

    @staticmethod
    def _row_to_entity(row: RowMapping) -> Client:
        """
        convert the database row into a client domain object
        convert enum values back into their python enum types
        """

        raw_stage = row["onboarding_stage"]
        return Client(
            id=row["id"],
            organization_id=row["organization_id"],
            subscription_id=row["subscription_id"],
            display_name=str(row["display_name"]),
            email=row["email"],
            phone=row["phone"],
            address=row["address"],
            date_of_birth=row["date_of_birth"],
            occupation=row["occupation"],
            onboarding_stage=(
                OnboardingStage(str(raw_stage)) if raw_stage is not None else None
            ),
            primary_advisor_membership_id=row["primary_advisor_membership_id"],
            status=ClientStatus(str(row["status"])),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            deleted_at=row["deleted_at"],
        )
