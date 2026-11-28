# 50% or more AI-generated code
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.v2.schemas.base import ResponseSchema
from app.dependencies.uow import get_uow
from app.domain.uow import AbstractUnitOfWork
from app.services.feature_flags import FeatureFlagService

router = APIRouter(prefix="/feature-flags", tags=["Feature Flags"])


class FeatureFlagsResponse(ResponseSchema):
    flags: dict[str, bool]


class SingleFlagResponse(ResponseSchema):
    name: str
    enabled: bool


def get_feature_flag_service(
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> FeatureFlagService:
    return FeatureFlagService(uow)


@router.get("", response_model=FeatureFlagsResponse)
async def list_flags(
    service: FeatureFlagService = Depends(get_feature_flag_service),
) -> FeatureFlagsResponse:
    return FeatureFlagsResponse(flags=await service.get_all())


@router.get("/{name}", response_model=SingleFlagResponse)
async def get_flag(
    name: str,
    service: FeatureFlagService = Depends(get_feature_flag_service),
) -> SingleFlagResponse:
    return SingleFlagResponse(name=name, enabled=await service.is_enabled(name))
