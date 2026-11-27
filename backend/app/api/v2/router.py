from fastapi import APIRouter

from app.api.v2.routers import clients, public_booking

router = APIRouter()

router.include_router(clients.router)
router.include_router(public_booking.router)
