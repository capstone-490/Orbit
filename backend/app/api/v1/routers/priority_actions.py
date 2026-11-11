# Substantial AI assistance used; verified with backend unit tests.
import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg import Error as PsycopgError
from psycopg.rows import dict_row

from app.auth import get_current_advisor
from app.dependencies.db import get_connection
from app.logging_config import get_logger
from app.services.ai_suggestions import get_ai_provider, get_suggestions
from app.services.priority_actions import (
    ACTIVE_STATUSES,
    HIGH_PRIORITY_WINDOW_DAYS,
    rank_priority_actions,
)

router = APIRouter(prefix="/priority-actions", tags=["Priority Actions"])
logger = get_logger("app.api.priority_actions")


def _today() -> date:
    timezone = ZoneInfo(os.getenv("ORBIT_TIMEZONE", "America/Toronto"))
    return datetime.now(timezone).date()


def _fetch_candidate_follow_ups(advisor_id: int, horizon: date) -> list[dict]:
    """Active follow-ups for this advisor that are due on or before `horizon`.

    The clients join also checks advisor_id so a follow-up can never surface a
    client that is not assigned to the signed-in advisor.
    """
    try:
        with get_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT f.id, f.client_id, c.name AS client_name, f.reason,
                       f.financial_planning_stage::text AS financial_planning_stage,
                       f.due_date, f.priority::text AS priority,
                       f.status::text AS status
                FROM follow_ups f
                JOIN clients c
                  ON c.id = f.client_id AND c.advisor_id = f.advisor_id
                WHERE f.advisor_id = %s
                  AND f.status::text = ANY(%s)
                  AND f.due_date <= %s
                """,
                (advisor_id, list(ACTIVE_STATUSES), horizon),
            )
            return cur.fetchall()
    except PsycopgError as error:
        logger.exception(
            "Failed to retrieve priority actions", extra={"advisor_id": advisor_id}
        )
        raise HTTPException(
            status_code=500, detail="Unable to retrieve priority actions."
        ) from error


def _ranked_actions(advisor_id: int) -> list[dict]:
    today = _today()
    horizon = today + timedelta(days=HIGH_PRIORITY_WINDOW_DAYS)
    return rank_priority_actions(
        _fetch_candidate_follow_ups(advisor_id, horizon), today
    )


@router.get("")
def list_priority_actions(
    limit: int = Query(default=5, ge=1, le=50),
    advisor: dict[str, int] = Depends(get_current_advisor),
):
    actions = _ranked_actions(advisor["id"])
    return {"items": actions[:limit], "total": len(actions)}


@router.get("/suggestions")
def list_priority_action_suggestions(
    advisor: dict[str, int] = Depends(get_current_advisor),
):
    actions = _ranked_actions(advisor["id"])
    return get_suggestions(actions, get_ai_provider())
