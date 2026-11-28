# Substantial AI assistance used; verified with frontend tests and production build.
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import get_current_advisor
from app.dependencies.db import get_connection


router = APIRouter(
    tags=["Goals"],
    dependencies=[Depends(get_current_advisor)],
)


# Goal data model and validation
class GoalCreate(BaseModel):
    duration: Literal[
        "Short-term",
        "Medium-term",
        "Long-term",
    ]
    type: str = Field(min_length=1)
    name: str | None = Field(default=None, max_length=255)


class GoalsCreate(BaseModel):
    goals: list[GoalCreate]


# Retrieve predefined financial goal options
@router.get("/goals/types")
def list_goal_types():
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT code, name, duration, category
            FROM public.goal_types
            ORDER BY duration, name
            """
        )

        columns = [column.name for column in cur.description]
        rows = cur.fetchall()

    return [dict(zip(columns, row)) for row in rows]


# Retrieve saved goals for a client
@router.get("/clients/{client_id}/goals")
def get_client_goals(
    client_id: int,
    advisor: dict[str, int] = Depends(get_current_advisor),
):
    with get_connection(str(advisor["id"]), "Advisor") as conn, conn.cursor() as cur:

        # Verify that the client belongs to the advisor
        cur.execute(
            """
            SELECT id
            FROM t_clients
            WHERE id = %(client_id)s
              AND advisor_id = %(advisor_id)s
            """,
            {
                "client_id": client_id,
                "advisor_id": advisor["id"],
            },
        )

        if cur.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="Client not found",
            )

        cur.execute(
            """
            SELECT g.id, g.client_id, g.name, g.duration,
                   g.type, g.category, g.created_at, g.updated_at
            FROM t_goals AS g
            JOIN t_clients AS c ON c.id = g.client_id
            WHERE g.client_id = %(client_id)s
              AND c.advisor_id = %(advisor_id)s
            ORDER BY g.duration, g.id
            """,
            {
                "client_id": client_id,
                "advisor_id": advisor["id"],
            },
        )

        columns = [column.name for column in cur.description]
        rows = cur.fetchall()

    return [dict(zip(columns, row)) for row in rows]


# Save financial goals for a client
@router.post("/clients/{client_id}/goals", status_code=201)
def create_client_goals(
    client_id: int,
    payload: GoalsCreate,
    advisor: dict[str, int] = Depends(get_current_advisor),
):
    saved_goals = []

    with get_connection(str(advisor["id"]), "Advisor") as conn, conn.cursor() as cur:

        # Verify client ownership and lock during the transaction
        cur.execute(
            """
            SELECT id
            FROM t_clients
            WHERE id = %(client_id)s
              AND advisor_id = %(advisor_id)s
            FOR UPDATE
            """,
            {
                "client_id": client_id,
                "advisor_id": advisor["id"],
            },
        )

        if cur.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="Client not found",
            )

        for goal in payload.goals:

            # Handle custom goals
            if goal.type == "other":
                name = (goal.name or "").strip()

                if not name:
                    raise HTTPException(
                        status_code=422,
                        detail="A description is required for Other goals",
                    )

                category = "Other"

            # Handle predefined goals
            else:
                cur.execute(
                    """
                    SELECT name, category
                    FROM public.goal_types
                    WHERE code = %(code)s
                      AND duration = %(duration)s
                    """,
                    {
                        "code": goal.type,
                        "duration": goal.duration,
                    },
                )

                goal_type = cur.fetchone()

                if goal_type is None:
                    raise HTTPException(
                        status_code=422,
                        detail="Invalid goal type for the selected duration",
                    )

                name, category = goal_type

            # Insert the goal
            cur.execute(
                """
                INSERT INTO t_goals (
                    client_id,
                    name,
                    duration,
                    type,
                    category
                )
                VALUES (
                    %(client_id)s,
                    %(name)s,
                    %(duration)s,
                    %(type)s,
                    %(category)s
                )
                RETURNING id, client_id, name, duration,
                          type, category, created_at, updated_at
                """,
                {
                    "client_id": client_id,
                    "name": name,
                    "duration": goal.duration,
                    "type": goal.type,
                    "category": category,
                },
            )

            columns = [column.name for column in cur.description]
            row = cur.fetchone()
            saved_goals.append(dict(zip(columns, row)))

    return {
        "message": "Financial goals saved successfully",
        "goals": saved_goals,
    }
    
# Delete an individual financial goal
@router.delete("/clients/{client_id}/goals/{goal_id}")
def delete_client_goal(
    client_id: int,
    goal_id: int,
    advisor: dict[str, int] = Depends(get_current_advisor),
):
    with get_connection(str(advisor["id"]), "Advisor") as conn, conn.cursor() as cur:

        # Verify that the client belongs to the advisor
        cur.execute(
            """
            SELECT id
            FROM t_clients
            WHERE id = %(client_id)s
              AND advisor_id = %(advisor_id)s
            """,
            {
                "client_id": client_id,
                "advisor_id": advisor["id"],
            },
        )

        if cur.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="Client not found",
            )

        # Delete only the selected goal belonging to this client
        cur.execute(
            """
            DELETE FROM t_goals
            WHERE id = %(goal_id)s
              AND client_id = %(client_id)s
            RETURNING id
            """,
            {
                "goal_id": goal_id,
                "client_id": client_id,
            },
        )

        if cur.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="Financial goal not found",
            )

    return {
        "message": "Financial goal deleted successfully"
    }

