# Substantial AI assistance used; verified with backend unit tests.
"""Optional AI suggestions for the advisor's priority actions.

AI is strictly best-effort: if it is disabled, misconfigured, slow, or returns
something unusable, callers get a status of "disabled" or "unavailable" and an
empty list. It never raises, so the dashboard keeps working without it.
"""

import json
import os
from typing import Protocol

import httpx

from app.logging_config import get_logger

logger = get_logger("app.services.ai_suggestions")

MAX_ITEMS_SENT = 10
MAX_SUGGESTIONS = 5
MAX_SUGGESTION_LENGTH = 300

SYSTEM_PROMPT = (
    "You help a financial advisor decide what to do next. You receive a JSON "
    "list of urgent follow-ups. For the most important ones, write one short, "
    "concrete next step each (max 25 words). Do not invent facts that are not "
    'in the input. Reply with JSON only, in the form {"suggestions": '
    '[{"follow_up_id": <int>, "text": "<next step>"}]}.'
)


class SuggestionProvider(Protocol):
    def suggest(self, items: list[dict]) -> list[dict]: ...


class OpenAICompatibleProvider:
    def __init__(self, base_url: str, model: str, api_key: str, timeout: float):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    def suggest(self, items: list[dict]) -> list[dict]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            timeout=self.timeout,
            json={
                "model": self.model,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(items)},
                ],
            },
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return _parse_suggestions(content)


def _parse_suggestions(content: str) -> list[dict]:
    """Pull the JSON object out of the model's reply, tolerating code fences."""
    start, end = content.find("{"), content.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("AI response did not contain JSON.")
    suggestions = json.loads(content[start : end + 1]).get("suggestions", [])
    if not isinstance(suggestions, list):
        raise TypeError("AI response 'suggestions' is not a list.")
    return suggestions


def get_ai_provider() -> SuggestionProvider | None:
    """Build the provider from env vars, or return None if AI is turned off."""
    if os.getenv("AI_SUGGESTIONS_ENABLED", "false").lower() not in {"1", "true", "yes"}:
        return None
    base_url = os.getenv("AI_BASE_URL", "").strip()
    model = os.getenv("AI_MODEL", "").strip()
    if not base_url or not model:
        logger.warning("AI suggestions enabled but AI_BASE_URL or AI_MODEL is not set")
        return None
    return OpenAICompatibleProvider(
        base_url=base_url,
        model=model,
        api_key=os.getenv("AI_API_KEY", ""),
        timeout=float(os.getenv("AI_TIMEOUT_SECONDS", "5")),
    )


def _to_prompt_item(action: dict) -> dict:
    # Deliberately excludes client name, email, phone and other identifiers.
    return {
        "follow_up_id": action["follow_up_id"],
        "reason": action["reason"],
        "financial_planning_stage": action.get("financial_planning_stage"),
        "priority": action["priority"],
        "urgency": action["urgency_reason"],
    }


def get_suggestions(actions: list[dict], provider: SuggestionProvider | None) -> dict:
    """Return {"status": ..., "suggestions": [...]} and never raise."""
    if provider is None:
        return {"status": "disabled", "suggestions": []}
    if not actions:
        return {"status": "available", "suggestions": []}

    items = [_to_prompt_item(action) for action in actions[:MAX_ITEMS_SENT]]
    allowed_ids = {item["follow_up_id"] for item in items}

    try:
        raw_suggestions = provider.suggest(items)
    except Exception:
        logger.warning("AI suggestions unavailable", exc_info=True)
        return {"status": "unavailable", "suggestions": []}

    suggestions = []
    for suggestion in raw_suggestions:
        if not isinstance(suggestion, dict):
            continue
        follow_up_id = suggestion.get("follow_up_id")
        text = suggestion.get("text")
        # Drop anything referring to a follow-up we did not send (hallucinated
        # or another advisor's id) and anything without usable text.
        if follow_up_id not in allowed_ids or not isinstance(text, str):
            continue
        text = text.strip()
        if not text:
            continue
        suggestions.append(
            {"follow_up_id": follow_up_id, "text": text[:MAX_SUGGESTION_LENGTH]}
        )
        if len(suggestions) == MAX_SUGGESTIONS:
            break

    return {"status": "available", "suggestions": suggestions}
