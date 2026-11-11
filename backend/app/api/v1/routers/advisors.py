from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from psycopg import Error as PsycopgError
from psycopg.rows import dict_row
from pydantic import BaseModel, Field, field_validator

from app.auth import get_current_advisor
from app.dependencies.db import get_connection

router = APIRouter(prefix="/advisors", tags=["Advisors"])


TaskStatus = Literal["TO_DO", "IN_PROGRESS", "IN_REVIEW", "COMPLETED"]


class TaskStatusUpdate(BaseModel):
    status: TaskStatus


class TaskCreate(BaseModel):
    taskTitle: str = Field(min_length=1, max_length=255)
    dueDate: date
    clientId: int | None = None

    @field_validator("taskTitle")
    @classmethod
    def validate_task_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("Task title is required")
        return title


# 1. Fetch Tasks for a Specific Advisor
@router.get("/{advisor_id}/tasks")
def get_advisor_tasks(advisor_id: int):
    query = """
        SELECT
            t.id,
            t.advisor_id AS "advisorId",
            t.task_title AS "taskTitle",
            t.due_date AS "dueDate",
            t.status,
            t.created_at AS "createdAt",
            t.client_id AS "clientId",
            c.name AS "clientName"
        FROM tasks t
        LEFT JOIN clients c ON t.client_id = c.id
        WHERE t.advisor_id = %s
        ORDER BY t.due_date ASC;
    """
    try:
        with get_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (advisor_id,))
            return cur.fetchall()
    except PsycopgError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{advisor_id}/tasks", status_code=201)
def create_advisor_task(
    advisor_id: int,
    body: TaskCreate,
    advisor: dict[str, int] = Depends(get_current_advisor),
):
    if advisor_id != advisor["id"]:
        raise HTTPException(status_code=403, detail="Not authorized for this advisor.")

    query = """
        WITH inserted AS (
            INSERT INTO tasks (advisor_id, client_id, task_title, due_date)
            SELECT %s, %s, %s, %s
            WHERE %s::BIGINT IS NULL OR EXISTS (
                SELECT 1
                FROM clients
                WHERE id = %s AND advisor_id = %s
            )
            RETURNING id, advisor_id, client_id, task_title, due_date, status, created_at
        )
        SELECT
            inserted.id,
            inserted.advisor_id AS "advisorId",
            inserted.task_title AS "taskTitle",
            inserted.due_date AS "dueDate",
            inserted.status,
            inserted.created_at AS "createdAt",
            inserted.client_id AS "clientId",
            clients.name AS "clientName"
        FROM inserted
        LEFT JOIN clients ON clients.id = inserted.client_id;
    """
    try:
        with get_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                query,
                (
                    advisor_id,
                    body.clientId,
                    body.taskTitle,
                    body.dueDate,
                    body.clientId,
                    body.clientId,
                    advisor_id,
                ),
            )
            created_task = cur.fetchone()
            conn.commit()
    except PsycopgError as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not created_task:
        raise HTTPException(status_code=404, detail="Client not found for advisor")

    return created_task


@router.patch("/tasks/{task_id}")
def update_task_status(task_id: int, body: TaskStatusUpdate):

    query = """
        UPDATE tasks
        SET status = %s
        WHERE id = %s
        RETURNING
            id,
            advisor_id AS "advisorId",
            task_title AS "taskTitle",
            due_date AS "dueDate",
            status,
            created_at AS "createdAt",
            client_id AS "clientId";
    """
    try:
        with get_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (body.status, task_id))
            updated_task = cur.fetchone()
            conn.commit()
    except PsycopgError as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not updated_task:
        raise HTTPException(status_code=404, detail="Task not found")

    return updated_task


# 2. Fetch Schedule/Consultations for a Specific Advisor (JOINing with Clients)
@router.get("/{advisor_id}/schedule")
def get_advisor_schedule(advisor_id: int):
    query = """
        SELECT
            c.id,
            c.meeting_time AS "time",
            c.duration,
            cl.name AS "clientName",
            cl.id AS "clientId",
            c.category,
            c.agenda,
            c.completion_status AS "completionStatus",
            c.location_or_platform AS "locationOrPlatform"
        FROM consultations c
        JOIN clients cl ON c.client_id = cl.id
        WHERE c.advisor_id = %s
        ORDER BY c.meeting_time ASC;
    """
    try:
        with get_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (advisor_id,))
            return cur.fetchall()
    except PsycopgError as e:
        raise HTTPException(status_code=500, detail=str(e))


# 3. Fetch Clients assigned to a Specific Advisor
@router.get("/{advisor_id}/clients")
def get_advisor_clients(advisor_id: int):
    query = """
        SELECT
            id,
            name,
            phone_number AS "phoneNumber",
            email,
            address,
            age,
            occupation,
            timeline::text AS "timeline",
            advisor_id AS "advisorId",
            created_at AS "createdAt",
            updated_at AS "updated_at"
        FROM clients
        WHERE advisor_id = %s
        ORDER BY name ASC;
    """
    try:
        with get_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (advisor_id,))
            return cur.fetchall()
    except PsycopgError as e:
        raise HTTPException(status_code=500, detail=str(e))
