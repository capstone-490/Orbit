
# Currently it affects the DB directly and delete all info after it runs

import pytest
import psycopg
from psycopg import errors

from db import get_connection
from migrations.migrate import migrate

TABLES = [
    "password_reset_tokens", "notes", "agent_assignments", "agents",
    "goals", "documents", "clients", "advisors",
]

#Run migrations and checks indempotence
@pytest.fixture(scope="session", autouse=True)
def schema():
    migrate()
    migrate()
    yield

#Wipe all data after every test
@pytest.fixture(autouse=True)
def clean_tables():

    yield
    with get_connection() as conn:
        conn.execute(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY CASCADE")
        conn.commit()

#Execute one statement in its own connection/transaction.
def run(sql, params=None, fetch=False):
    with get_connection() as conn:
        cur = conn.execute(sql, params or ())
        row = cur.fetchone() if fetch else None
        conn.commit()
        return row


def make_advisor(username="testAdvisor", email="testAdvisor@example.com"):
    return run(
        "INSERT INTO advisors (username, email, password_hash) "
        "VALUES (%s, %s, 'hash') RETURNING id",
        (username, email), fetch=True,
    )[0]


def make_client(advisor_id=None, name="testClient", phone="000-000-0000", email="testClient@example.com"):
    return run(
        "INSERT INTO clients (name, phone_number, email, advisor_id) "
        "VALUES (%s, %s, %s, %s) RETURNING id",
        (name, phone, email, advisor_id), fetch=True,
    )[0]


def make_agent(advisor_id=None, type_="testAgent"):
    return run(
        "INSERT INTO agents (type, advisor_id) VALUES (%s, %s) RETURNING id",
        (type_, advisor_id), fetch=True,
    )[0]


def count(table, where="TRUE", params=None):
    return run(f"SELECT COUNT(*) FROM {table} WHERE {where}", params, fetch=True)[0]


class TestAdvisors:
    def test_insert_valid(self):
        assert make_advisor() is not None

    def test_email_unique(self):
        make_advisor(email="dup@example.com")
        with pytest.raises(errors.UniqueViolation):
            make_advisor(username="other", email="dup@example.com")

    @pytest.mark.parametrize("col", ["username", "email", "password_hash"])
    def test_required_columns_not_null(self, col):
        values = {"username": "u", "email": "u@example.com", "password_hash": "h"}
        values[col] = None
        with pytest.raises(errors.NotNullViolation):
            run("INSERT INTO advisors (username, email, password_hash) VALUES (%s,%s,%s)",
                (values["username"], values["email"], values["password_hash"]))

    def test_timestamps_default(self):
        aid = make_advisor()
        row = run("SELECT created_at, updated_at FROM advisors WHERE id=%s", (aid,), fetch=True)
        assert row[0] is not None and row[1] is not None

class TestClients:
    def test_insert_valid(self):
        assert make_client() is not None

    def test_phone_unique(self):
        make_client(phone="000-000-0000", email="testA@example.com")
        with pytest.raises(errors.UniqueViolation):
            make_client(phone="000-000-0000", email="testB@example.com")

    def test_email_unique(self):
        make_client(phone="000-000-0000", email="test@example.com")
        with pytest.raises(errors.UniqueViolation):
            make_client(phone="000-000-0001", email="test@example.com")

    def test_phone_max_length_32(self):
        with pytest.raises(errors.StringDataRightTruncation):
            make_client(phone="0" * 33)

    def test_name_not_null(self):
        with pytest.raises(errors.NotNullViolation):
            run("INSERT INTO clients (name, phone_number, email) VALUES (NULL,'000-000-0000','test@example.com')")

    @pytest.mark.parametrize("value", ["Conservative", "Moderate", "Aggressive"])
    def test_risk_tolerance_valid(self, value):
        run("INSERT INTO clients (name, phone_number, email, risk_tolerance) "
            "VALUES ('testName','000-000-0000','test@example.com',%s)", (value,))

    def test_risk_tolerance_invalid(self):
        with pytest.raises(errors.InvalidTextRepresentation):
            run("INSERT INTO clients (name, phone_number, email, risk_tolerance) "
                "VALUES ('testName','000-000-0000','test@example.com','NotARiskTolerance')")

    def test_timeline_invalid(self):
        with pytest.raises(errors.InvalidTextRepresentation):
            run("INSERT INTO clients (name, phone_number, email, timeline) "
                "VALUES ('testName','000-000-0000','test@example.com','NotATimeline')")

    def test_fk_invalid_advisor(self):
        with pytest.raises(errors.ForeignKeyViolation):
            make_client(advisor_id=999999)

    def test_cascade_delete_advisor_removes_clients(self):
        aid = make_advisor()
        make_client(advisor_id=aid)
        run("DELETE FROM advisors WHERE id=%s", (aid,))
        assert count("clients") == 0

class TestDocuments:
    def test_default_status_is_unsent(self):
        cid = make_client()
        doc_id = run("INSERT INTO documents (client_id, name) VALUES (%s,'testName') RETURNING id",
                     (cid,), fetch=True)[0]
        status = run("SELECT status FROM documents WHERE id=%s", (doc_id,), fetch=True)[0]
        assert status == "Unsent"

    def test_invalid_status(self):
        cid = make_client()
        with pytest.raises(errors.InvalidTextRepresentation):
            run("INSERT INTO documents (client_id, name, status) VALUES (%s,'testName','notAStatus')", (cid,))

    def test_client_id_required(self):
        with pytest.raises(errors.NotNullViolation):
            run("INSERT INTO documents (client_id, name) VALUES (NULL,'testName')")

    def test_fk_invalid_client(self):
        with pytest.raises(errors.ForeignKeyViolation):
            run("INSERT INTO documents (client_id, name) VALUES (100000,'testName')")

    def test_cascade_delete_client(self):
        cid = make_client()
        run("INSERT INTO documents (client_id, name) VALUES (%s,'testName')", (cid,))
        run("DELETE FROM clients WHERE id=%s", (cid,))
        assert count("documents") == 0

class TestGoals:
    @pytest.mark.parametrize("duration", ["Short-term", "Medium-term", "Long-term"])
    def test_duration_valid(self, duration):
        cid = make_client()
        run("INSERT INTO goals (client_id, name, duration) VALUES (%s,'testName',%s)", (cid, duration))

    def test_duration_invalid(self):
        cid = make_client()
        with pytest.raises(errors.InvalidTextRepresentation):
            run("INSERT INTO goals (client_id, name, duration) VALUES (%s,'testName','NotADuration')", (cid,))

    def test_name_not_null(self):
        cid = make_client()
        with pytest.raises(errors.NotNullViolation):
            run("INSERT INTO goals (client_id, name) VALUES (%s, NULL)", (cid,))

    def test_cascade_delete_client(self):
        cid = make_client()
        run("INSERT INTO goals (client_id, name) VALUES (%s,'testName')", (cid,))
        run("DELETE FROM clients WHERE id=%s", (cid,))
        assert count("goals") == 0

class TestAgents:
    def test_type_not_null(self):
        with pytest.raises(errors.NotNullViolation):
            run("INSERT INTO agents (type) VALUES (NULL)")

    def test_fk_invalid_advisor(self):
        with pytest.raises(errors.ForeignKeyViolation):
            make_agent(advisor_id=100000)

    def test_cascade_delete_advisor_removes_agents(self):
        aid = make_advisor()
        make_agent(advisor_id=aid)
        run("DELETE FROM advisors WHERE id=%s", (aid,))
        assert count("agents") == 0

class TestAgentAssignments:
    def test_default_status_pending(self):
        cid = make_agent()
        agid = make_client()
        row = run("INSERT INTO agent_assignments (client_id, agent_id, assigned_at) "
                  "VALUES (%s,%s,NOW()) RETURNING status", (cid, agid), fetch=True)
        assert row[0] == "Pending"

    def test_invalid_status(self):
        cid, agid = make_client(), make_agent()
        with pytest.raises(errors.InvalidTextRepresentation):
            run("INSERT INTO agent_assignments (client_id, agent_id, assigned_at, status) "
                "VALUES (%s,%s,NOW(),'NotAStatus')", (cid, agid))

    def test_assigned_at_required(self):
        cid, agid = make_client(), make_agent()
        with pytest.raises(errors.NotNullViolation):
            run("INSERT INTO agent_assignments (client_id, agent_id) VALUES (%s,%s)", (cid, agid))

    def test_fk_invalid_client_and_agent(self):
        with pytest.raises(errors.ForeignKeyViolation):
            run("INSERT INTO agent_assignments (client_id, agent_id, assigned_at) "
                "VALUES (10000, 10000, NOW())")

    def test_cascade_delete_client_and_agent(self):
        cid, agid = make_client(), make_agent()
        run("INSERT INTO agent_assignments (client_id, agent_id, assigned_at) "
            "VALUES (%s,%s,NOW())", (cid, agid))
        run("DELETE FROM agents WHERE id=%s", (agid,))
        assert count("agent_assignments") == 0

class TestNotes:
    def test_insert_valid(self):
        cid = make_client()
        run("INSERT INTO notes (content, title, client_id, author_id, author_type) "
            "VALUES ('testContent','testTitle',%s,1,'Advisor')", (cid,))

    def test_invalid_author_type(self):
        cid = make_client()
        with pytest.raises(errors.InvalidTextRepresentation):
            run("INSERT INTO notes (content, title, client_id, author_id, author_type) "
                "VALUES ('testContent','testT',%s,1,'NotAType')", (cid,))

    @pytest.mark.parametrize("col", ["content", "title", "author_id", "author_type"])
    def test_required_columns(self, col):
        cid = make_client()
        vals = {"content": "testConent", "title": "testTitle", "author_id": 1, "author_type": "Advisor"}
        vals[col] = None
        with pytest.raises(errors.NotNullViolation):
            run("INSERT INTO notes (content, title, client_id, author_id, author_type) "
                "VALUES (%s,%s,%s,%s,%s)",
                (vals["content"], vals["title"], cid, vals["author_id"], vals["author_type"]))

    def test_cascade_delete_client(self):
        cid = make_client()
        run("INSERT INTO notes (content, title, client_id, author_id, author_type) "
            "VALUES ('testConent','testTitle',%s,1,'Advisor')", (cid,))
        run("DELETE FROM clients WHERE id=%s", (cid,))
        assert count("notes") == 0

class TestPasswordResetTokens:
    def _insert(self, advisor_id, token_hash):
        run("INSERT INTO password_reset_tokens (advisor_id, token_hash, expires_at) "
            "VALUES (%s,%s,NOW() + INTERVAL '1 hour')", (advisor_id, token_hash))

    def test_insert_valid(self):
        self._insert(make_advisor(), "testHash")

    def test_token_hash_unique(self):
        aid = make_advisor()
        self._insert(aid, "testHash")
        with pytest.raises(errors.UniqueViolation):
            self._insert(aid, "testHash")

    @pytest.mark.parametrize("bad", ["", "   ", "\t\n"])
    def test_token_hash_not_empty_check(self, bad):
        with pytest.raises(errors.CheckViolation):
            self._insert(make_advisor(), bad)

    def test_expires_at_required(self):
        aid = make_advisor()
        with pytest.raises(errors.NotNullViolation):
            run("INSERT INTO password_reset_tokens (advisor_id, token_hash) VALUES (%s,'testHash')", (aid,))

    def test_fk_invalid_advisor(self):
        with pytest.raises(errors.ForeignKeyViolation):
            self._insert(10000, "testHash")

    def test_cascade_delete_advisor(self):
        aid = make_advisor()
        self._insert(aid, "testHash")
        run("DELETE FROM advisors WHERE id=%s", (aid,))
        assert count("password_reset_tokens") == 0