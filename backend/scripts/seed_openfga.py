# backend/scripts/seed_fga.py
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

OPENFGA_API_URL = os.environ.get("OPENFGA_API_URL", "http://openfga:8080")
STORE_NAME = os.environ.get("OPENFGA_STORE_NAME", "orbit")
MODEL_PATH = Path(os.environ.get("OPENFGA_MODEL_PATH", "openfga/model.fga"))


def run_fga(*args: str) -> str:
    cmd = ["fga", *args, "--api-url", OPENFGA_API_URL]
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command {' '.join(cmd)} failed:\n{result.stderr.strip()}")
    return result.stdout.strip()


def main() -> None:
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(f"OpenFGA model file not found at {MODEL_PATH}")

    # check if store already exists
    stores_data = json.loads(run_fga("store", "list"))
    existing_store = next(
        (s for s in stores_data.get("stores", []) if s.get("name") == STORE_NAME),
        None,
    )

    # create store + model if missing
    if existing_store is None:
        created = json.loads(
            run_fga("store", "create", "--name", STORE_NAME, "--model", str(MODEL_PATH))
        )
        store_id = created["store"]["id"]
        model_id = created["model"]["authorization_model_id"]
        print(
            f"INFO: Created OpenFGA store '{STORE_NAME}' (store_id={store_id}, model_id={model_id})"
        )
        return

    store_id = existing_store["id"]

    # compare current running model with local model.fga; write new version if changed
    current_dsl = run_fga("model", "get", "--store-id", store_id, "--format", "fga")
    desired_dsl = MODEL_PATH.read_text(encoding="utf-8").strip()

    if current_dsl.strip() == desired_dsl:
        print(
            f"INFO: OpenFGA store '{STORE_NAME}' ({store_id}) model is already up to date."
        )
        return

    written = json.loads(
        run_fga("model", "write", "--store-id", store_id, "--file", str(MODEL_PATH))
    )
    model_id = written["authorization_model_id"]
    print(
        f"INFO: Updated model in OpenFGA store '{STORE_NAME}' (store_id={store_id}, model_id={model_id})"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
