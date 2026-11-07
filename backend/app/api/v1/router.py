from fastapi import APIRouter

from app.api.v1.routers import (
    advisor_registrations,
    advisors,
    clients,
    feature_flags,
    meetings,
    sessions,
    tasks,
)

router = APIRouter()

router.include_router(sessions.router)
router.include_router(clients.router)
router.include_router(advisors.router)
router.include_router(advisor_registrations.router)
router.include_router(meetings.router)
router.include_router(feature_flags.router)
router.include_router(tasks.router)
