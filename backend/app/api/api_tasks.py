from fastapi import APIRouter, HTTPException
from app.db.db import get_connection
from app.api.api_classes import TaskCreate, TaskResponse


from app.services.sla_cal import (
    compute_urgency,
    get_timezone,
    URGENCY_COLOR,
    force_utc,
    force_timezone_on_DB_return
)

router = APIRouter()

#Need to implement some security later
@router.get(
    "/api/v1/data/tasks",
    response_model=list[TaskResponse]
)
def get_tasks(client_id: int, user_timezone: str = "UTC"):

    try:
        timezone_zi = get_timezone(user_timezone)

        with get_connection() as conn:

            rows = conn.execute("""
                SELECT
                    id,
                    title,
                    description,
                    client_id,
                    task_status,
                    due_date,
                    last_contact_date
                FROM tasks
                WHERE client_id = %s
                ORDER BY due_date ASC
            """, (client_id,)).fetchall()


        tasks = []

        for row in rows:

            task = build_task_response(row, timezone_zi)

            tasks.append(task)

        return tasks

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve tasks"
        )


@router.post(
    "/api/v1/data/tasks",
    response_model=TaskResponse,
    status_code=201
)
def create_task(task: TaskCreate, user_timezone: str = "UTC"):

    try:
        # Validate timezone-aware datetimes
        due_date = force_utc(task.due_date)

        last_contact_date = None

        if (task.last_contact_date is not None):
            last_contact_date = force_utc(task.last_contact_date)

        timezone_zi = get_timezone(user_timezone)

        with get_connection() as conn:

            row = conn.execute("""
                INSERT INTO tasks (
                    title,
                    description,
                    client_id,
                    task_status,
                    due_date,
                    last_contact_date
                )
                VALUES (%s, %s, %s, %s, %s,
                        COALESCE(%s, NOW()))
                RETURNING
                    id,
                    title,
                    description,
                    client_id,
                    task_status,
                    due_date,
                    last_contact_date
            """, (
                task.title,
                task.description,
                task.client_id,
                task.task_status.value,
                due_date,
                last_contact_date
            )).fetchone()

        return build_task_response(row, timezone_zi)

    except HTTPException:
        raise

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve tasks"
        )

def build_task_response(row, timezone_zi, now = None):

    urgency = compute_urgency(
        status=row[4],
        due_date=row[5],
        tz=timezone_zi,
        now = now
    )

    last_contact_date_user_zi = None

    if(row[6] is not None):
        last_contact_date_user_zi= force_timezone_on_DB_return(row[6], timezone_zi)

    return TaskResponse(
        id=row[0],
        title=row[1],
        description=row[2],
        client_id=row[3],
        task_status=row[4],
        due_date=force_timezone_on_DB_return(row[5], timezone_zi),
        last_contact_date=last_contact_date_user_zi,
        urgency_state=urgency,
        urgency_color=URGENCY_COLOR[urgency]
    )