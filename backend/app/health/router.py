from fastapi import APIRouter

health_router = APIRouter(tags=["Health"])


@health_router.get("/", include_in_schema=False)
def root():
    return {"Hello": "World"}


@health_router.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}
