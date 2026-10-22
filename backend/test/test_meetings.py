from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_db(monkeypatch):
    conn = MagicMock()
    cursor = MagicMock()

    conn.__enter__.return_value = conn
    conn.cursor.return_value.__enter__.return_value = cursor

    monkeypatch.setattr(main, "get_connection", lambda: conn)

    return cursor


def test_list_meetings_empty(mock_db):
    mock_db.fetchall.return_value = []
    mock_db.description = [
        MagicMock(name="id"),
        MagicMock(name="client_id"),
        MagicMock(name="advisor_id"),
        MagicMock(name="meeting_date"),
        MagicMock(name="completion_status"),
    ]

    response = client.get("/meetings/1")

    assert response.status_code == 200
    assert response.json() == []

    mock_db.execute.assert_called_once_with(
        """
                SELECT id, client_id, advisor_id, meeting_date, completion_status
                FROM meetings
                WHERE advisor_id = %s
                ORDER BY meeting_date DESC, id DESC
                """,
        (1,),
    )
