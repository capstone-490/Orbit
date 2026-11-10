# 50% or more AI-generated code
from __future__ import annotations

from datetime import datetime

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.routers.public_booking import (
    register_booking_exception_handlers,
    router,
)
from app.dependencies.uow import get_clock, get_uow
from tests.unit.test_public_booking_service import FakeUnitOfWork, now, uow  # noqa: F401


@pytest.fixture
def test_app(uow: FakeUnitOfWork, now: datetime) -> FastAPI:  # noqa: F811
    app = FastAPI()
    register_booking_exception_handlers(app)
    app.include_router(router, prefix="/api/v1")

    app.dependency_overrides[get_uow] = lambda: uow
    app.dependency_overrides[get_clock] = lambda: now
    return app


async def test_e2e_public_booking_http_flow(test_app: FastAPI) -> None:
    """
    Tests the complete HTTP flow:
    1. GET /weekly -> 200 OK with 4 available Monday slots
    2. POST /holds -> 201 Created
    3. POST /confirm -> 200 OK with raw `cancel_token` (and zero internal IDs leaked)
    4. POST /cancel -> 200 OK with status = CANCELLED
    """
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        # 1. Fetch weekly slots
        weekly_resp = await client.get(
            "/api/v1/public/booking-links/tok_valid_123/availability/weekly",
            params={"start_date": "2026-11-02", "end_date": "2026-11-08"},
        )
        assert weekly_resp.status_code == 200
        weekly_data = weekly_resp.json()
        assert weekly_data["advisor_display_name"] == "Jane Doe, CFA"
        assert len(weekly_data["slots"]) == 4

        first_slot = weekly_data["slots"][0]

        # 2. Acquire soft hold on the first slot
        hold_resp = await client.post(
            "/api/v1/public/booking-links/tok_valid_123/holds",
            json={
                "start_at": first_slot["start_at"],
                "end_at": first_slot["end_at"],
                "prospect_timezone": "America/New_York",
                "idempotency_key": "http-idem-0001",
            },
        )
        assert hold_resp.status_code == 201
        hold_data = hold_resp.json()
        booking_id = hold_data["booking_id"]
        assert hold_data["status"] == "HELD"

        # 3. Confirm booking
        confirm_resp = await client.post(
            f"/api/v1/public/booking-links/tok_valid_123/bookings/{booking_id}/confirm",
            json={
                "email": "prospect@example.com",
                "full_name": "Jordan Prospect",
                "phone": "+15145550123",
                "meeting_topic": "Portfolio Tax Optimization",
            },
        )
        assert confirm_resp.status_code == 200
        confirm_data = confirm_resp.json()
        assert confirm_data["status"] == "CONFIRMED"
        assert "cancel_token" in confirm_data
        # Privacy check: internal IDs are never in the JSON payload!
        assert "client_id" not in confirm_data
        assert "internal_meeting_id" not in confirm_data

        # 4. Cancel booking using the returned token
        cancel_resp = await client.post(
            "/api/v1/public/booking-links/cancel",
            json={
                "cancel_token": confirm_data["cancel_token"],
                "reason": "Need to reschedule next month",
            },
        )
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"] == "CANCELLED"


async def test_api_error_status_codes(test_app: FastAPI) -> None:
    """Verifies 404 on invalid token and 422 on out-of-hours slot selection."""
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        # 404 Not Found on bogus public_token
        not_found_resp = await client.get(
            "/api/v1/public/booking-links/tok_unknown/availability/weekly",
            params={"start_date": "2026-11-02", "end_date": "2026-11-08"},
        )
        assert not_found_resp.status_code == 404

        # 422 Unprocessable Entity when trying to hold a slot outside working hours (e.g. 03:00 UTC)
        bad_slot_resp = await client.post(
            "/api/v1/public/booking-links/tok_valid_123/holds",
            json={
                "start_at": "2026-11-02T03:00:00Z",
                "end_at": "2026-11-02T03:30:00Z",
                "prospect_timezone": "UTC",
                "idempotency_key": "http-idem-bad-slot",
            },
        )
        assert bad_slot_resp.status_code == 422
