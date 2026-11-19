from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from psycopg import Error as PsycopgError

from app.api.v1.schemas.task import TaskCreate, TaskResponse
from app.auth import get_current_advisor
from app.dependencies.db import get_connection
from app.services.sla_cal import (
    URGENCY_COLOR,
    compute_urgency,
    force_timezone_on_DB_return,
    force_utc,
    get_timezone,
)

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("", response_model=list[TaskResponse])
def get_tasks(
    client_id: int,
    user_timezone: str = "UTC",
    advisor: dict[str, int] = Depends(get_current_advisor),
):

    try:
        timezone_zi = get_timezone(user_timezone)

        with get_connection(str(advisor["id"]), "Advisor") as conn:
            rows = conn.execute(
                """
                SELECT
                    t.id,
                    t.title,
                    t.description,
                    t.client_id,
                    t.task_status,
                    t.due_date,
                    t.last_contact_date
                FROM t_tasks_advisor t
                INNER JOIN t_clients c ON c.id = t.client_id
                WHERE t.client_id = %s
                  AND c.advisor_id = %s
                ORDER BY t.due_date ASC
                """,
                (client_id, advisor["id"]),
            ).fetchall()

        return [build_task_response(row, timezone_zi) for row in rows]

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except PsycopgError as exc:
        raise HTTPException(
            status_code=500,
            detail="Database operation failed",
        ) from exc


@router.post("", response_model=TaskResponse, status_code=201)
def create_task(
    task: TaskCreate,
    user_timezone: str = "UTC",
    advisor: dict[str, int] = Depends(get_current_advisor),
):

    try:
        # Validate timezone-aware datetimes
        due_date = force_utc(task.due_date)

        last_contact_date = None

        if task.last_contact_date is not None:
            last_contact_date = force_utc(task.last_contact_date)

        timezone_zi = get_timezone(user_timezone)

        with get_connection(str(advisor["id"]), "Advisor") as conn:
            row = conn.execute(
                """
                INSERT INTO tasks_advisor (
                    title,
                    description,
                    client_id,
                    task_status,
                    due_date,
                    last_contact_date
                )
                SELECT
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    COALESCE(%s, NOW())
                FROM clients c
                WHERE c.id = %s
                  AND c.advisor_id = %s
                RETURNING
                    id,
                    title,
                    description,
                    client_id,
                    task_status,
                    due_date,
                    last_contact_date
                """,
                (
                    task.title,
                    task.description,
                    task.client_id,
                    task.status.value,
                    due_date,
                    last_contact_date,
                    task.client_id,
                    advisor["id"],
                ),
            ).fetchone()

            if row is None:
                raise HTTPException(
                    status_code=403,
                    detail="No access to client",
                )

        return build_task_response(row, timezone_zi)

    except HTTPException:
        raise

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except PsycopgError as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


def build_task_response(
    row,
    timezone_zi: ZoneInfo,
    now: datetime | None = None,
) -> TaskResponse:

    urgency = compute_urgency(status=row[4], due_date=row[5], tz=timezone_zi, now=now)

    last_contact_date_user_zi = None

    if row[6] is not None:
        last_contact_date_user_zi = force_timezone_on_DB_return(row[6], timezone_zi)

    return TaskResponse(
        id=row[0],
        title=row[1],
        description=row[2],
        client_id=row[3],
        status=row[4],
        due_date=force_timezone_on_DB_return(row[5], timezone_zi),
        last_contact_date=last_contact_date_user_zi,
        urgency_state=urgency,
        urgency_color=URGENCY_COLOR[urgency],
    )
