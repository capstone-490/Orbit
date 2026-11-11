from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.auth import create_access_token
from app.core.config import settings
from app.dependencies.db import get_connection
from app.main import app


@pytest.fixture
def meeting_records():
    # Never run these tests against the regular application database.
    if settings.ENVIRONMENT != "test":
        pytest.fail("Integration tests require ENVIRONMENT=test")

    unique = uuid4().hex
    advisor_id = None
    client_id = None

    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                    INSERT INTO t_advisors (username, email, password_hash)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                (f"test_{unique}", f"{unique}@example.com", "test-only-hash"),
            )
            advisor_id = cur.fetchone()[0]

            cur.execute(
                """
                    INSERT INTO t_clients
                        (name, phone_number, email, advisor_id)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                (
                    "Integration Test Client",
                    unique[:20],
                    f"client_{unique}@example.com",
                    advisor_id,
                ),
            )
            client_id = cur.fetchone()[0]

            cur.execute(
                """
                    INSERT INTO t_meetings
                        (advisor_id, client_id, meeting_date, duration_minutes)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                (
                    advisor_id,
                    client_id,
                    datetime(2030, 5, 30, 10, tzinfo=UTC),
                    30,
                ),
            )
            meeting_id = cur.fetchone()[0]

        yield {
            "advisor_id": advisor_id,
            "client_id": client_id,
            "meeting_id": meeting_id,
        }

    finally:
        # Delete only records created by this fixture.
        if advisor_id is not None:
            with get_connection() as conn, conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM t_meetings WHERE advisor_id = %s",
                    (advisor_id,),
                )
                if client_id is not None:
                    cur.execute(
                        "DELETE FROM t_clients WHERE id = %s",
                        (client_id,),
                    )
                cur.execute(
                    "DELETE FROM t_advisors WHERE id = %s",
                    (advisor_id,),
                )


def test_reschedule_updates_real_database(meeting_records):
    advisor_id = meeting_records["advisor_id"]
    meeting_id = meeting_records["meeting_id"]

    with TestClient(
        app,
        headers={"Authorization": f"Bearer {create_access_token(advisor_id)}"},
    ) as client:
        response = client.patch(
            f"/api/v1/meetings/{meeting_id}/reschedule",
            json={"new_start": "2030-06-01T10:00:00+00:00"},
        )

    assert response.status_code == 200, response.text

    data = response.json()
    assert data["id"] == meeting_id
    assert data["advisor_id"] == advisor_id
    assert data["client_id"] == meeting_records["client_id"]
    assert data["duration_minutes"] == 30

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
                SELECT meeting_date, client_id, advisor_id
                FROM t_meetings
                WHERE id = %s
                """,
            (meeting_id,),
        )
        stored_date, stored_client_id, stored_advisor_id = cur.fetchone()

    assert stored_date == datetime(2030, 6, 1, 10, tzinfo=UTC)
    assert stored_client_id == meeting_records["client_id"]
    assert stored_advisor_id == advisor_id


def test_reschedule_rejects_conflicting_meeting(meeting_records):
    advisor_id = meeting_records["advisor_id"]
    meeting_id = meeting_records["meeting_id"]

    # Add another scheduled meeting for the same advisor.
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
                INSERT INTO t_meetings
                    (advisor_id, client_id, meeting_date, duration_minutes)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
            (
                advisor_id,
                meeting_records["client_id"],
                datetime(2030, 6, 1, 10, tzinfo=UTC),
                30,
            ),
        )
        conflicting_meeting_id = cur.fetchone()[0]

    with TestClient(
        app,
        headers={"Authorization": f"Bearer {create_access_token(advisor_id)}"},
    ) as client:
        response = client.patch(
            f"/api/v1/meetings/{meeting_id}/reschedule",
            json={"new_start": "2030-06-01T10:15:00+00:00"},
        )

    assert response.status_code == 409, response.text
    assert "conflicts" in response.json()["detail"]

    # Verify that neither meeting was modified.
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
                SELECT id, meeting_date
                FROM t_meetings
                WHERE id IN (%s, %s)
                ORDER BY id
                """,
            (meeting_id, conflicting_meeting_id),
        )
        stored_meetings = dict(cur.fetchall())

    assert stored_meetings[meeting_id] == datetime(2030, 5, 30, 10, tzinfo=UTC)
    assert stored_meetings[conflicting_meeting_id] == datetime(
        2030, 6, 1, 10, tzinfo=UTC
    )


def test_reschedule_allows_back_to_back_meetings(meeting_records):
    advisor_id = meeting_records["advisor_id"]
    meeting_id = meeting_records["meeting_id"]

    # Existing appointment: 10:00–10:30.
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
                INSERT INTO t_meetings
                    (advisor_id, client_id, meeting_date, duration_minutes)
                VALUES (%s, %s, %s, %s)
                """,
            (
                advisor_id,
                meeting_records["client_id"],
                datetime(2030, 6, 1, 10, tzinfo=UTC),
                30,
            ),
        )

    # Requested appointment: 10:30–11:00.
    with TestClient(
        app,
        headers={"Authorization": f"Bearer {create_access_token(advisor_id)}"},
    ) as client:
        response = client.patch(
            f"/api/v1/meetings/{meeting_id}/reschedule",
            json={"new_start": "2030-06-01T10:30:00+00:00"},
        )

    assert response.status_code == 200, response.text

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT meeting_date FROM t_meetings WHERE id = %s",
            (meeting_id,),
        )
        stored_date = cur.fetchone()[0]

    assert stored_date == datetime(2030, 6, 1, 10, 30, tzinfo=UTC)


def test_advisor_cannot_reschedule_another_advisors_meeting(meeting_records):
    meeting_id = meeting_records["meeting_id"]
    other_advisor_id = None

    try:
        # Create a second advisor.
        with get_connection() as conn, conn.cursor() as cur:
            unique = uuid4().hex
            cur.execute(
                """
                    INSERT INTO t_advisors (username, email, password_hash)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                (
                    f"other_{unique}",
                    f"other_{unique}@example.com",
                    "test-only-hash",
                ),
            )
            other_advisor_id = cur.fetchone()[0]

        # Advisor B attempts to reschedule Advisor A's meeting.
        with TestClient(
            app,
            headers={
                "Authorization": (f"Bearer {create_access_token(other_advisor_id)}")
            },
        ) as client:
            response = client.patch(
                f"/api/v1/meetings/{meeting_id}/reschedule",
                json={"new_start": "2030-06-01T10:00:00+00:00"},
            )

        assert response.status_code == 404, response.text

        # The original appointment must remain unchanged.
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                    SELECT advisor_id, meeting_date
                    FROM t_meetings
                    WHERE id = %s
                    """,
                (meeting_id,),
            )
            stored_advisor_id, stored_date = cur.fetchone()

        assert stored_advisor_id == meeting_records["advisor_id"]
        assert stored_date == datetime(2030, 5, 30, 10, tzinfo=UTC)

    finally:
        if other_advisor_id is not None:
            with get_connection() as conn, conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM t_advisors WHERE id = %s",
                    (other_advisor_id,),
                )


def test_cannot_reschedule_completed_or_cancelled_meeting(meeting_records):
    meeting_id = meeting_records["meeting_id"]
    advisor_id = meeting_records["advisor_id"]

    for status in ("Completed", "Cancelled"):
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE t_meetings SET completion_status = %s WHERE id = %s",
                (status, meeting_id),
            )

        with TestClient(
            app,
            headers={"Authorization": f"Bearer {create_access_token(advisor_id)}"},
        ) as client:
            response = client.patch(
                f"/api/v1/meetings/{meeting_id}/reschedule",
                json={"new_start": "2030-06-01T10:00:00+00:00"},
            )

        assert response.status_code == 409, response.text

        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT meeting_date FROM t_meetings WHERE id = %s",
                (meeting_id,),
            )
            assert cur.fetchone()[0] == datetime(2030, 5, 30, 10, tzinfo=UTC)


@pytest.mark.parametrize(
    "invalid_start",
    [
        "2020-01-01T10:00:00+00:00",
        "2030-06-01T10:00:00",
        "not-a-date",
    ],
)
def test_invalid_date_preserves_meeting(meeting_records, invalid_start):
    meeting_id = meeting_records["meeting_id"]
    advisor_id = meeting_records["advisor_id"]

    with TestClient(
        app,
        headers={"Authorization": f"Bearer {create_access_token(advisor_id)}"},
    ) as client:
        response = client.patch(
            f"/api/v1/meetings/{meeting_id}/reschedule",
            json={"new_start": invalid_start},
        )

    assert response.status_code == 422, response.text

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT meeting_date FROM t_meetings WHERE id = %s",
            (meeting_id,),
        )
        assert cur.fetchone()[0] == datetime(2030, 5, 30, 10, tzinfo=UTC)


def test_different_advisors_can_use_same_time(meeting_records):
    meeting_id = meeting_records["meeting_id"]
    advisor_id = meeting_records["advisor_id"]
    other_advisor_id = None

    try:
        with get_connection() as conn, conn.cursor() as cur:
            unique = uuid4().hex
            cur.execute(
                """
                    INSERT INTO t_advisors (username, email, password_hash)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                (
                    f"other_{unique}",
                    f"other_{unique}@example.com",
                    "test-only-hash",
                ),
            )
            other_advisor_id = cur.fetchone()[0]

            cur.execute(
                """
                    INSERT INTO t_meetings
                        (advisor_id, client_id, meeting_date, duration_minutes)
                    VALUES (%s, %s, %s, %s)
                    """,
                (
                    other_advisor_id,
                    meeting_records["client_id"],
                    datetime(2030, 6, 1, 10, tzinfo=UTC),
                    30,
                ),
            )

        with TestClient(
            app,
            headers={"Authorization": f"Bearer {create_access_token(advisor_id)}"},
        ) as client:
            response = client.patch(
                f"/api/v1/meetings/{meeting_id}/reschedule",
                json={"new_start": "2030-06-01T10:00:00+00:00"},
            )

        assert response.status_code == 200, response.text

    finally:
        if other_advisor_id is not None:
            with get_connection() as conn, conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM t_meetings WHERE advisor_id = %s",
                    (other_advisor_id,),
                )
                cur.execute(
                    "DELETE FROM t_advisors WHERE id = %s",
                    (other_advisor_id,),
                )


def test_concurrent_reschedules_cannot_double_book(meeting_records):
    advisor_id = meeting_records["advisor_id"]
    first_meeting_id = meeting_records["meeting_id"]

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
                INSERT INTO t_meetings
                    (advisor_id, client_id, meeting_date, duration_minutes)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
            (
                advisor_id,
                meeting_records["client_id"],
                datetime(2030, 5, 31, 10, tzinfo=UTC),
                30,
            ),
        )
        second_meeting_id = cur.fetchone()[0]

    barrier = Barrier(2)
    token = create_access_token(advisor_id)

    def attempt_reschedule(meeting_id):
        with TestClient(
            app,
            headers={"Authorization": f"Bearer {token}"},
        ) as client:
            barrier.wait(timeout=10)
            return client.patch(
                f"/api/v1/meetings/{meeting_id}/reschedule",
                json={"new_start": "2030-06-01T10:00:00+00:00"},
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(attempt_reschedule, first_meeting_id),
            executor.submit(attempt_reschedule, second_meeting_id),
        ]
        statuses = [future.result(timeout=20) for future in futures]

    assert sorted(statuses) == [200, 409], statuses

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
                SELECT COUNT(*)
                FROM t_meetings
                WHERE id IN (%s, %s)
                  AND meeting_date = %s
                """,
            (
                first_meeting_id,
                second_meeting_id,
                datetime(2030, 6, 1, 10, tzinfo=UTC),
            ),
        )
        assert cur.fetchone()[0] == 1
