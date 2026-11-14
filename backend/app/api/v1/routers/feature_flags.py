from fastapi import APIRouter, Depends, Header, HTTPException, Request

from app.core.feature_flags import get_variant

router = APIRouter(
    prefix="/feature-flags",
    tags=["Feature Flags"],
)


def get_user_id(
    user_id: str | None = Header(default=None, alias="User-ID"),
) -> str:
    # Temporary until authenticated identity is implemented.
    return user_id or "unknown"


# Temporary endpoint for testing A/B feature flags.
@router.get("/ab-test")
def ab_test(
    request: Request,
    user_id: str = Depends(get_user_id),
):
    variant = get_variant("demo-ab", user_id)
    request.state.variant = variant
    request.state.ab_variant = variant
    return {"Variant": variant}


@router.get("/{name}")
def read_flag(
    name: str,
    request: Request,
    user_id: str = Depends(get_user_id),
):
    variant = get_variant(name, user_id)
    request.state.variant = variant
    request.state.ab_variant = variant

    return {
        "name": name,
        "variant": variant,
        "use_new_feature": variant == "B",
    }


@router.get("", include_in_schema=False)
@router.get("/", include_in_schema=False)
def flag_empty_name():
    raise HTTPException(
        status_code=422,
        detail="Flag name cannot be empty",
    )
