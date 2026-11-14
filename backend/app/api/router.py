from fastapi import APIRouter

from app.api.v1.router import router as v1_router
from app.api.versions import APIVersion, api_prefix

api_router = APIRouter()

api_router.include_router(
    v1_router,
    prefix=api_prefix(APIVersion.V1),
)
