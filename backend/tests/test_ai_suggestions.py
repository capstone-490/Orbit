# Substantial AI assistance used; verified with backend unit tests.
from datetime import UTC, datetime

import httpx
import pytest

from app.api.v1.routers import priority_actions
from app.services import ai_suggestions
from app.services.ai_suggestions import (
    OpenAICompatibleProvider,
    _parse_suggestions,
    get_ai_provider,
)

AI_ENV_VARS = [
    "AI_SUGGESTIONS_ENABLED",
    "AI_BASE_URL",
    "AI_MODEL",
    "AI_API_KEY",
    "AI_TIMEOUT_SECONDS",
]


@pytest.fixture
def ai_env(monkeypatch):
    for name in AI_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


# --------------------------------------------------------------------------
# Provider configuration
# --------------------------------------------------------------------------


def test_ai_is_disabled_by_default(ai_env):
    assert get_ai_provider() is None


def test_ai_stays_disabled_without_url_and_model(ai_env):
    ai_env.setenv("AI_SUGGESTIONS_ENABLED", "true")

    assert get_ai_provider() is None


def test_provider_is_built_from_environment(ai_env):
    ai_env.setenv("AI_SUGGESTIONS_ENABLED", "true")
    ai_env.setenv("AI_BASE_URL", "http://localhost:11434/v1/")
    ai_env.setenv("AI_MODEL", "llama3.2")
    ai_env.setenv("AI_API_KEY", "secret-key")
    ai_env.setenv("AI_TIMEOUT_SECONDS", "12")

    provider = get_ai_provider()

    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.base_url == "http://localhost:11434/v1"
    assert provider.model == "llama3.2"
    assert provider.api_key == "secret-key"
    assert provider.timeout == 12.0


@pytest.mark.parametrize("value", ["abc", "", "0", "-3", "nan", "inf"])
def test_invalid_timeout_falls_back_to_default(ai_env, value):
    ai_env.setenv("AI_SUGGESTIONS_ENABLED", "true")
    ai_env.setenv("AI_BASE_URL", "http://localhost:11434/v1")
    ai_env.setenv("AI_MODEL", "llama3.2")
    ai_env.setenv("AI_TIMEOUT_SECONDS", value)

    provider = get_ai_provider()

    assert provider.timeout == ai_suggestions.DEFAULT_TIMEOUT_SECONDS


# --------------------------------------------------------------------------
# Parsing the model's reply
# --------------------------------------------------------------------------


def test_parse_suggestions_ignores_code_fences():
    content = '```json\n{"suggestions": [{"follow_up_id": 1, "text": "Call."}]}\n```'

    assert _parse_suggestions(content) == [{"follow_up_id": 1, "text": "Call."}]


def test_parse_suggestions_defaults_to_empty_list():
    assert _parse_suggestions('{"other": true}') == []


def test_parse_suggestions_rejects_reply_without_json():
    with pytest.raises(ValueError, match="did not contain JSON"):
        _parse_suggestions("Sorry, I cannot help with that.")


def test_parse_suggestions_rejects_non_list():
    with pytest.raises(TypeError, match="is not a list"):
        _parse_suggestions('{"suggestions": "Call the client."}')


# --------------------------------------------------------------------------
# Calling the AI service
# --------------------------------------------------------------------------


class FakeResponse:
    def __init__(self, payload=None, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("POST", "http://ai.test/chat/completions")
            raise httpx.HTTPStatusError(
                "AI request failed",
                request=request,
                response=httpx.Response(self.status_code, request=request),
            )

    def json(self):
        return self.payload


def chat_reply(content):
    return {"choices": [{"message": {"content": content}}]}


def test_provider_posts_items_and_returns_suggestions(monkeypatch):
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse(
            chat_reply('{"suggestions": [{"follow_up_id": 7, "text": "Email."}]}')
        )

    monkeypatch.setattr(ai_suggestions.httpx, "post", fake_post)
    provider = OpenAICompatibleProvider("http://ai.test/v1", "model-x", "key-1", 3)

    result = provider.suggest([{"follow_up_id": 7, "reason": "Docs"}])

    assert result == [{"follow_up_id": 7, "text": "Email."}]
    url, kwargs = calls[0]
    assert url == "http://ai.test/v1/chat/completions"
    assert kwargs["headers"]["Authorization"] == "Bearer key-1"
    assert kwargs["timeout"] == 3
    assert kwargs["json"]["model"] == "model-x"
    assert '"follow_up_id": 7' in kwargs["json"]["messages"][1]["content"]


def test_provider_omits_authorization_without_api_key(monkeypatch):
    calls = []

    def fake_post(url, **kwargs):
        calls.append(kwargs)
        return FakeResponse(chat_reply('{"suggestions": []}'))

    monkeypatch.setattr(ai_suggestions.httpx, "post", fake_post)
    provider = OpenAICompatibleProvider("http://ai.test/v1", "model-x", "", 3)

    assert provider.suggest([]) == []
    assert "Authorization" not in calls[0]["headers"]


def test_provider_raises_on_http_error(monkeypatch):
    monkeypatch.setattr(
        ai_suggestions.httpx,
        "post",
        lambda url, **kwargs: FakeResponse(status_code=503),
    )
    provider = OpenAICompatibleProvider("http://ai.test/v1", "model-x", "", 3)

    with pytest.raises(httpx.HTTPStatusError):
        provider.suggest([])


# --------------------------------------------------------------------------
# Router helper
# --------------------------------------------------------------------------


def test_today_uses_configured_timezone(monkeypatch):
    monkeypatch.setenv("ORBIT_TIMEZONE", "UTC")

    assert priority_actions._today() == datetime.now(UTC).date()


def test_suggestions_are_capped_at_five_and_300_characters():
    actions = [
        {
            "follow_up_id": index,
            "reason": f"Follow-up {index}",
            "priority": "High",
            "urgency_reason": "Overdue by 1 day",
        }
        for index in range(1, 8)
    ]

    class ManySuggestions:
        def suggest(self, items):
            return [
                {"follow_up_id": item["follow_up_id"], "text": "x" * 400}
                for item in items
            ]

    result = ai_suggestions.get_suggestions(actions, ManySuggestions())

    assert result["status"] == "available"
    assert len(result["suggestions"]) == ai_suggestions.MAX_SUGGESTIONS
    assert all(
        len(s["text"]) == ai_suggestions.MAX_SUGGESTION_LENGTH
        for s in result["suggestions"]
    )
