# app/api/v1/routers/clients.py
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.v2.schemas.clients import (
    ClientCreateRequest,
    ClientResponse,
    ClientUpdateRequest,
)
from app.auth import get_current_advisor
from app.dependencies.uow import get_client_service, get_clock
from app.services.clients import UNSET, ClientService

router = APIRouter(prefix="/clients", tags=["Clients"])


@router.get("", response_model=list[ClientResponse])
async def list_clients(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    advisor: dict[str, UUID] = Depends(get_current_advisor),
    service: ClientService = Depends(get_client_service),
) -> list[ClientResponse]:
    clients = await service.list_clients(
        organization_id=advisor["organization_id"],
        subscription_id=advisor["subscription_id"],
        advisor_membership_id=advisor["membership_id"],
        limit=limit,
        offset=offset,
    )
    return [ClientResponse.model_validate(c) for c in clients]


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: UUID,
    advisor: dict[str, UUID] = Depends(get_current_advisor),
    service: ClientService = Depends(get_client_service),
) -> ClientResponse:
    client = await service.get_client(
        organization_id=advisor["organization_id"],
        subscription_id=advisor["subscription_id"],
        client_id=client_id,
    )
    return ClientResponse.model_validate(client)


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    payload: ClientCreateRequest,
    advisor: dict[str, UUID] = Depends(get_current_advisor),
    service: ClientService = Depends(get_client_service),
) -> ClientResponse:
    client = await service.create_client(
        organization_id=advisor["organization_id"],
        subscription_id=advisor["subscription_id"],
        display_name=payload.display_name,
        email=str(payload.email) if payload.email is not None else None,
        phone=payload.phone,
        address=payload.address,
        date_of_birth=payload.date_of_birth,
        occupation=payload.occupation,
        onboarding_stage=payload.onboarding_stage,
        primary_advisor_membership_id=advisor["membership_id"],
    )
    return ClientResponse.model_validate(client)


@router.patch("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: UUID,
    payload: ClientUpdateRequest,
    advisor: dict[str, UUID] = Depends(get_current_advisor),
    service: ClientService = Depends(get_client_service),
) -> ClientResponse:
    sent = payload.model_fields_set
    client = await service.update_client(
        organization_id=advisor["organization_id"],
        subscription_id=advisor["subscription_id"],
        client_id=client_id,
        display_name=payload.display_name if "display_name" in sent else None,
        email=(
            str(payload.email)
            if "email" in sent and payload.email
            else (None if "email" in sent else UNSET)
        ),
        phone=payload.phone if "phone" in sent else UNSET,
        address=payload.address if "address" in sent else UNSET,
        date_of_birth=payload.date_of_birth if "date_of_birth" in sent else UNSET,
        occupation=payload.occupation if "occupation" in sent else UNSET,
        onboarding_stage=payload.onboarding_stage
        if "onboarding_stage" in sent
        else UNSET,
        status=payload.status if "status" in sent else None,
    )
    return ClientResponse.model_validate(client)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: UUID,
    advisor: dict[str, UUID] = Depends(get_current_advisor),
    service: ClientService = Depends(get_client_service),
    now: datetime = Depends(get_clock),
) -> Response:
    await service.delete_client(
        organization_id=advisor["organization_id"],
        subscription_id=advisor["subscription_id"],
        client_id=client_id,
        now=now,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
