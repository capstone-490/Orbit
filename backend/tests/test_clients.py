from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from psycopg.errors import UniqueViolation

from app.api.v1.routers import clients
from app.api.v1.routers.clients import (
    ClientCreate,
    ClientExpenseInput,
    _snapshot_totals,
)
from app.auth import create_access_token
from app.main import app

client = TestClient(
    app,
    headers={"Authorization": f"Bearer {create_access_token(1)}"},
)

COLUMNS = [
    "id",
    "name",
    "email",
    "phone_number",
    "address",
    "age",
    "occupation",
    "timeline",
    "created_at",
    "updated_at",
    "annual_income",
    "risk_tolerance",
    "target_retirement_age",
]


@pytest.fixture
def mock_db(monkeypatch):
    conn = MagicMock()
    cursor = MagicMock()

    conn.__enter__.return_value = conn
    conn.cursor.return_value.__enter__.return_value = cursor

    monkeypatch.setattr(
        clients, "get_connection", lambda user_id=None, user_type="System": conn
    )

    return cursor


def test_create_client_success(mock_db):
    mock_db.fetchone.return_value = (1,)

    response = client.post(
        "/api/v1/clients",
        json={
            "name": "Alice Smith",
            "email": "alice@example.com",
            "phone_number": "514-555-1234",
            "date_of_birth": "1988-04-12",
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "message": "Client created successfully",
    }

    mock_db.execute.assert_called_once()
    query, params = mock_db.execute.call_args.args

    assert "INSERT INTO t_clients" in query
    assert params["name"] == "Alice Smith"
    assert params["email"] == "alice@example.com"
    assert params["phone_number"] == "514-555-1234"
    assert params["advisor_id"] == 1
    assert params["age"] == date.today().year - 1988 - (
        (date.today().month, date.today().day) < (4, 12)
    )
    assert "date_of_birth" not in params


@pytest.mark.parametrize("missing_field", ["name", "email", "phone_number"])
def test_create_client_missing_required_field(mock_db, missing_field):
    payload = {
        "name": "Alice Smith",
        "email": "alice@example.com",
        "phone_number": "514-555-1234",
    }
    del payload[missing_field]

    response = client.post("/api/v1/clients", json=payload)

    assert response.status_code == 422
    mock_db.execute.assert_not_called()


@pytest.mark.parametrize(
    "field,value",
    [
        ("name", ""),
        ("email", "not-an-email"),
        ("phone_number", ""),
    ],
)
def test_create_client_invalid_fields(mock_db, field, value):
    payload = {
        "name": "Alice Smith",
        "email": "alice@example.com",
        "phone_number": "514-555-1234",
    }
    payload[field] = value

    response = client.post("/api/v1/clients", json=payload)

    assert response.status_code == 422
    mock_db.execute.assert_not_called()


@pytest.mark.parametrize(
    "phone",
    ["12345", "abcdefghij", "111-111-1111", "514-ABC-1234"],
)
def test_invalid_phone_number(phone):
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ClientCreate(
            name="Test Client",
            email="test@example.com",
            phone_number=phone,
        )


def test_snapshot_expense_validation_and_period_totals():
    with pytest.raises(ValueError):
        ClientExpenseInput(description="   ", amount=10, frequency="weekly")
    with pytest.raises(ValueError):
        ClientExpenseInput(description="Rent", amount=10, frequency="daily")

    totals = _snapshot_totals(
        [
            {"amount": Decimal("10"), "frequency": "weekly"},
            {"amount": Decimal("100"), "frequency": "monthly"},
            {"amount": Decimal("520"), "frequency": "annually"},
        ],
        [],
        [],
        [],
    )

    assert totals == {
        "expenses": {
            "weekly_total": Decimal("43.08"),
            "monthly_total": Decimal("186.67"),
            "annual_total": Decimal("2240.00"),
        },
        "income": {
            "weekly_total": Decimal("0.00"),
            "monthly_total": Decimal("0.00"),
            "annual_total": Decimal("0.00"),
        },
        "revenue": {
            "weekly_total": Decimal("-43.08"),
            "monthly_total": Decimal("-186.67"),
            "annual_total": Decimal("-2240.00"),
        },
        "assets": {"total": Decimal("0.00")},
        "debts": {"total": Decimal("0.00")},
        "net_worth": Decimal("0.00"),
    }


def test_replace_client_financial_snapshot(client, mock_db):
    mock_db.fetchone.return_value = (1,)
    
    # Use side_effect to return different data for each fetchall call
    # Order: expenses, income, assets, debts
    mock_db.fetchall.side_effect = [
        [(7, "Rent", Decimal("1200.00"), "monthly")],  # expenses
        [],  # income
        [],  # assets
        [],  # debts
    ]
    
    # Set description for expenses columns
    expense_columns = [MagicMock(name=name) for name in ("id", "description", "amount", "frequency")]
    for col, name in zip(expense_columns, ("id", "description", "amount", "frequency")):
        col.name = name
    mock_db.description = expense_columns

    response = client.put(
        "/clients/1/financial-snapshot",
        json={
            "expenses": [
                {"description": "Rent", "amount": 1200, "frequency": "monthly"}
            ],
            "income": [],
            "assets": [],
            "debts": [],
        },
    )

    assert response.status_code == 200
    response_data = response.json()
    # expenses should be a list
    assert isinstance(response_data["expenses"], list)
    assert response_data["expenses"] == [
        {"id": 7, "description": "Rent", "amount": 1200.0, "frequency": "monthly"}
    ]
    assert response_data["income"] == []
    assert response_data["assets"] == []
    assert response_data["debts"] == []
    # Check the totals
    assert float(response_data["totals"]["expenses"]["weekly_total"]) == pytest.approx(276.92, abs=0.01)
    assert float(response_data["totals"]["expenses"]["monthly_total"]) == pytest.approx(1200.0, abs=0.01)
    assert float(response_data["totals"]["expenses"]["annual_total"]) == pytest.approx(14400.0, abs=0.01)
    assert float(response_data["totals"]["net_worth"]) == pytest.approx(0.0, abs=0.01)


def test_create_client_optional_fields(mock_db):
    mock_db.fetchone.return_value = (2,)

    response = client.post(
        "/api/v1/clients",
        json={
            "name": "Bob Jones",
            "email": "bob@example.com",
            "phone_number": "514-555-5678",
        },
    )

    assert response.status_code == 201

    _, params = mock_db.execute.call_args.args

    assert params["address"] is None
    assert params["age"] is None
    assert params["occupation"] is None
    assert params["timeline"] is None


def test_create_client_persists_financial_summary(mock_db):
    mock_db.fetchone.return_value = (3,)

    response = client.post(
        "/api/v1/clients",
        json={
            "name": "Casey Lee",
            "email": "casey@example.com",
            "phone_number": "514-555-7890",
            "annual_income": 95000,
            "risk_tolerance": "Moderate",
            "target_retirement_age": 65,
        },
    )

    assert response.status_code == 201
    assert mock_db.execute.call_count == 2
    summary_query, summary_params = mock_db.execute.call_args_list[1].args
    assert "INSERT INTO t_client_financial_summaries" in summary_query
    assert summary_params == {
        "client_id": 3,
        "annual_income": Decimal("95000"),
        "risk_tolerance": "Moderate",
        "target_retirement_age": 65,
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("annual_income", -1),
        ("risk_tolerance", "Very high"),
        ("target_retirement_age", 131),
    ],
)
def test_create_client_rejects_invalid_financial_summary(mock_db, field, value):
    response = client.post(
        "/api/v1/clients",
        json={
            "name": "Casey Lee",
            "email": "casey@example.com",
            "phone_number": "514-555-7890",
            field: value,
        },
    )

    assert response.status_code == 422
    mock_db.execute.assert_not_called()


def test_create_client_duplicate(mock_db):
    mock_db.execute.side_effect = UniqueViolation("Duplicate client")

    response = client.post(
        "/api/v1/clients",
        json={
            "name": "Alice Smith",
            "email": "alice@example.com",
            "phone_number": "514-555-1234",
        },
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_list_clients(client, mock_db, auth_headers):
    mock_db.description = [MagicMock(name="column") for _ in COLUMNS]
    for column, name in zip(mock_db.description, COLUMNS):
        column.name = name

    mock_db.fetchall.return_value = [
        (
            1,
            "Alice Smith",
            "alice@example.com",
            "514-555-1234",
            None,
            None,
            None,
            None,
            datetime(2026, 10, 15, tzinfo=UTC),
            datetime(2026, 10, 15, tzinfo=UTC),
            None,
            None,
            None,
        )
    ]

    # Endpoint must be /api/v1/clients (collection), not /api/v1/clients/1
    response = client.get("/clients", headers=auth_headers)
    assert response.status_code == 200


def test_get_client(client, mock_db, auth_headers):
    mock_db.description = [MagicMock(name="column") for _ in COLUMNS]
    for column, name in zip(mock_db.description, COLUMNS):
        column.name = name

    mock_db.fetchone.return_value = (
        1,
        "Alice Smith",
        "alice@example.com",
        "514-555-1234",
        None,
        None,
        None,
        None,
        datetime(2026, 10, 15, tzinfo=UTC),
        datetime(2026, 10, 15, tzinfo=UTC),
        None,
        None,
        None,
    )

    response = client.get("/clients/1", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "name": "Alice Smith",
        "email": "alice@example.com",
        "phone_number": "514-555-1234",
        "address": None,
        "age": None,
        "occupation": None,
        "timeline": None,
        "created_at": "2026-10-15T00:00:00+00:00",
        "updated_at": "2026-10-15T00:00:00+00:00",
        "annual_income": None,
        "risk_tolerance": None,
        "target_retirement_age": None,
    }


def test_update_client_not_found(mock_db, client):
    mock_db.fetchone.return_value = None

    response = client.patch(
        "/clients/999",
        json={"name": "Updated Name"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Client not found"}

    mock_db.execute.assert_called_once()


def test_update_client_persists_financial_summary(client, mock_db):
    mock_db.fetchone.side_effect = [
        (1,),
        (
            1,
            "Alice Smith",
            "alice@example.com",
            "514-555-1234",
            None,
            None,
            None,
            None,
            datetime(2026, 10, 15, tzinfo=UTC),
            datetime(2026, 10, 15, tzinfo=UTC),
            95000,
            "Moderate",
            65,
        ),
    ]
    mock_db.description = [MagicMock(name="column") for _ in COLUMNS]
    for column, name in zip(mock_db.description, COLUMNS):
        column.name = name

    response = client.patch(
        "/clients/1",
        json={
            "annual_income": 95000,
            "risk_tolerance": "Moderate",
            "target_retirement_age": 65,
        },
    )

    assert response.status_code == 200
    assert response.json()["annual_income"] == 95000
    assert response.json()["risk_tolerance"] == "Moderate"
    assert response.json()["target_retirement_age"] == 65
    assert mock_db.execute.call_count == 3
    summary_query, summary_params = mock_db.execute.call_args_list[1].args
    assert "ON CONFLICT (client_id) DO UPDATE" in summary_query
    assert summary_params == {
        "client_id": 1,
        "annual_income": Decimal("95000"),
        "risk_tolerance": "Moderate",
        "target_retirement_age": 65,
    }


def test_update_client_no_valid_fields(client):
    response = client.patch(
        "/clients/1",
        json={"invalid_field": "Some value"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "No valid fields provided for update"}
