# Below 50% AI-generated

import json
from pathlib import Path

from app.db.db import get_connection

CONFIG_PATH = Path(__file__).resolve().parent / "config" / "feature_flags.json"

def load_feature_flags() -> None:
    with CONFIG_PATH.open(encoding="utf-8") as f:
        config = json.load(f)

    flags = config.get("flags", [])

    with get_connection() as conn:
        for flag in flags:
            conn.execute(
                """INSERT INTO feature_flags (name, enabled, rollout_percent, description) VALUES (%s, %s, %s, %s) ON CONFLICT (name) DO NOTHING""",
                            (
                                flag["name"],
                                flag["enabled"],
                                flag["rollout_percent"],
                                flag.get("description"),
                            ),
                        )
        conn.commit()


if __name__ == "__main__":
        load_feature_flags()
        print("Feature flags loaded successfully.")
