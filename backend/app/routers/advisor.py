from fastapi import APIRouter, HTTPException
from psycopg.rows import dict_row

from app.db.db import get_connection

router = APIRouter(prefix="/advisors", tags=["Advisors"])


# 1. Fetch Tasks for a Specific Advisor
@router.get("/{advisor_id}/tasks")
def get_advisor_tasks(advisor_id: int):
    query = """
        SELECT 
            t.id,
            t.advisor_id AS "advisorId",
            t.task_title AS "taskTitle",
            t.due_date AS "dueDate",
            t.tag,
            t.completed,
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/tasks/{task_id}")
def update_task_completion(task_id: int, body: dict):
    completed = body.get("completed")
    
    query = """
        UPDATE tasks
        SET completed = %s
        WHERE id = %s
        RETURNING 
            id,
            advisor_id AS "advisorId",
            task_title AS "taskTitle",
            due_date AS "dueDate",
            tag,
            completed,
            created_at AS "createdAt",
            client_id AS "clientId";
    """
    try:
        with get_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (completed, task_id))
            updated_task = cur.fetchone()
            conn.commit()
            
            if not updated_task:
                raise HTTPException(status_code=404, detail="Task not found")
                
            return updated_task
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
            c.status_text AS "statusText",
            c.location_or_platform AS "locationOrPlatform",
            c.action_button_label AS "actionButtonLabel"
        FROM consultations c
        JOIN clients cl ON c.client_id = cl.id
        WHERE c.advisor_id = %s
        ORDER BY c.meeting_time ASC;
    """
    try:
        with get_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (advisor_id,))
            return cur.fetchall()
    except Exception as e:
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
            date_of_birth AS "dateOfBirth",
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
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(query, (advisor_id,))
            return cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))