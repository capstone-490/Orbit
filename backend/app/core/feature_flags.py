# Below 50% AI-generated

import hashlib
import logging
from contextlib import closing

from app.db.db import get_connection

logger = logging.getLogger(__name__)


def get_bucket_value(flag_name: str, user_id: str) -> int:
    """Maps a feature flag and ID to a bucket value between 0 and 99."""
    if flag_name is None or flag_name.strip() == "":
        raise ValueError("flag_name cannot be None or empty")
    if user_id is None or user_id.strip() == "":
        raise ValueError("user_id cannot be None or empty")
    hash_value = hashlib.sha256(f"{flag_name}:{user_id}".encode()).hexdigest()
    bucket_value = int(hash_value, 16) % 100
    return bucket_value


def get_variant(flag_name: str, user_id: str) -> str:
    """Returns 'A' (existing behaviour) or 'B' (new behaviour). Users are consistently assigned to the same flag which defaults to A if flag is missing."""
    if flag_name is None or flag_name.strip() == "":
        raise ValueError("flag_name cannot be None or empty")
    if user_id is None or user_id.strip() == "":
        raise ValueError("user_id cannot be None or empty")
    try:
        with closing(get_connection()) as conn:
            result = conn.execute(
                "SELECT enabled, rollout_percent FROM feature_flags WHERE name = %s",
                (flag_name,),
            ).fetchone()
            if result is None:
                return "A"
            enabled, rollout_percent = result
            if not enabled:
                return "A"
            if get_bucket_value(flag_name, user_id) < rollout_percent:
                return "B"
            return "A"
    except Exception:
        logger.exception(
            'Error fetching feature flag %s, returning "A" ',
            flag_name,
        )
    return "A"


def set_flag(
    flag_name: str,
    enabled: bool,
    rollout_percent: int,
    changed_by: str | None = None,
    description: str | None = None,
) -> None:
    """Sets the feature flag in the database."""
    if flag_name is None or flag_name.strip() == "":
        raise ValueError("flag_name cannot be None or empty")
    if changed_by is None:
        changed_by = "unknown"
    if not 0 <= rollout_percent <= 100:
        raise ValueError("rollout_percent must be between 0 and 100")
    try:
        with closing(get_connection()) as conn:
            try:
                inserted = conn.execute(
                    "INSERT INTO feature_flags (name, enabled, rollout_percent, description) VALUES (%s, %s, %s, %s) ON CONFLICT (name) DO NOTHING RETURNING enabled, rollout_percent, description",
                    (flag_name, enabled, rollout_percent, description),
                ).fetchone()
                if inserted is None:
                    result = conn.execute(
                        "SELECT enabled, rollout_percent, description FROM feature_flags WHERE name = %s FOR UPDATE",
                        (flag_name,),
                    ).fetchone()
                    if result is None:
                        raise RuntimeError(
                            f"Feature flag {flag_name!r} disapeared during update"
                        )
                    conn.execute(
                        "UPDATE feature_flags SET enabled = %s, rollout_percent = %s, description = COALESCE(%s, description), updated_at = NOW() WHERE name = %s",
                        (enabled, rollout_percent, description, flag_name),
                    )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
    except Exception:
        logger.exception("Error setting feature flag %s", flag_name)
        raise
