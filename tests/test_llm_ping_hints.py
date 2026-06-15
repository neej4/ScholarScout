"""Tests for actionable LLM ping error hints."""

from src.core.llm import LLMClient


def test_local_ping_error_adds_endpoint_hint():
    client = LLMClient()
    client.provider = "custom"
    client.base_url = "http://localhost:20128/v1/chat/completions"
    client.model = "cmc/deepseek/deepseek-v4-flash"

    msg = client._format_ping_error("Connection refused while contacting localhost")

    assert "Local endpoint may not be running" in msg


def test_model_not_found_error_adds_model_hint():
    client = LLMClient()
    client.provider = "openrouter"
    client.base_url = "https://openrouter.ai/api/v1/chat/completions"
    client.model = "missing/model"

    msg = client._format_ping_error("Model not found")

    assert "exact model identifier" in msg
