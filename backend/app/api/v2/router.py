from fastapi import APIRouter

from app.api.v2.routers import public_booking

router = APIRouter()

router.include_router(public_booking.router)
