"""
Settings routes: /api/settings (GET/POST), /api/settings/test,
                 /api/clear-cache, /api/clear-sessions
"""
import os
import re
import json
from typing import Optional

import yaml
from flask import Blueprint, jsonify, request

from src.core.config import Config
from src.core.llm import LLMClient, PROVIDERS

settings_bp = Blueprint("settings", __name__)

_base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_data_dir = os.path.join(_base_dir, "data")

# ─── Allowed base-URL patterns for known providers ────────────────────────────
# Custom endpoints must be HTTPS or localhost (for Ollama / local proxies).
_KNOWN_PROVIDER_URLS = {
    "gemini":     r"^https://generativelanguage\.googleapis\.com/",
    "groq":       r"^https://api\.groq\.com/",
    "openrouter": r"^https://openrouter\.ai/",
    "openai":     r"^https://api\.openai\.com/",
    "ollama":     r"^http://localhost:\d+/",
    "custom":     r"^(https://|http://localhost)",   # HTTPS or localhost only
}


def _validate_base_url(provider: str, url: str) -> Optional[str]:
    """
    Validate that base_url matches the expected pattern for the provider.

    Returns None if valid, or an error string if invalid.
    """
    if not url:
        return None  # Empty is fine — will use provider default
    pattern = _KNOWN_PROVIDER_URLS.get(provider)
    if pattern and not re.match(pattern, url, re.IGNORECASE):
        return (
            f"Invalid base_url for provider '{provider}'. "
            f"Expected URL matching: {pattern}"
        )
    return None


@settings_bp.route("/api/settings", methods=["GET"])
def api_settings_get():
    """Return current LLM settings (API key masked)."""
    key = Config.LLM_API_KEY
    masked_key = ""
    if key:
        masked_key = key[:8] + "..." + key[-4:] if len(key) > 12 else "***"

    return jsonify({
        "provider":       Config.LLM_PROVIDER,
        "model":          Config.LLM_MODEL,
        "base_url":       Config.LLM_BASE_URL,
        "api_key_set":    bool(key),
        "api_key_masked": masked_key,
        "providers": {
            k: {
                "name":          v["name"],
                "free":          v["free"],
                "default_model": v["default_model"],
                "docs":          v["docs"],
            }
            for k, v in PROVIDERS.items()
        },
    })


@settings_bp.route("/api/settings", methods=["POST"])
def api_settings_save():
    """Save LLM settings to config.yaml (with base_url validation)."""
    body     = request.get_json(silent=True) or {}
    provider = body.get("provider", "").lower().strip()
    api_key  = body.get("api_key", "").strip()
    model    = body.get("model", "").strip()
    base_url = body.get("base_url", "").strip()

    if provider and provider not in PROVIDERS:
        return jsonify({"error": f"Unknown provider: {provider}"}), 400

    # Security: validate base_url before writing to disk
    url_error = _validate_base_url(provider or Config.LLM_PROVIDER, base_url)
    if url_error:
        return jsonify({"error": url_error}), 400

    config_path = Config.CONFIG_FILE
    try:
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f) or {}
    except Exception:
        cfg = {}

    if "llm" not in cfg:
        cfg["llm"] = {}

    if provider:
        cfg["llm"]["provider"] = provider
    if api_key:
        cfg["llm"]["api_key"] = api_key
    if model:
        cfg["llm"]["model"] = model
    elif provider:
        cfg["llm"]["model"] = PROVIDERS[provider]["default_model"]
    if base_url:
        cfg["llm"]["base_url"] = base_url
    elif provider and provider != "custom":
        cfg["llm"].pop("base_url", None)

    try:
        with open(config_path, "w") as f:
            yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True)
    except Exception as e:
        return jsonify({"error": f"Failed to write config: {e}"}), 500

    Config.reload()
    return jsonify({
        "status":   "saved",
        "provider": Config.LLM_PROVIDER,
        "model":    Config.LLM_MODEL,
    })


@settings_bp.route("/api/settings/test", methods=["POST"])
def api_settings_test():
    """Test LLM connection with current or provided settings."""
    body = request.get_json(silent=True) or {}

    # Temporarily override config for the test only
    orig = (Config.LLM_PROVIDER, Config.LLM_API_KEY, Config.LLM_MODEL, Config.LLM_BASE_URL)
    try:
        if body.get("provider"):  Config.LLM_PROVIDER = body["provider"]
        if body.get("api_key"):   Config.LLM_API_KEY  = body["api_key"]
        if body.get("model"):     Config.LLM_MODEL    = body["model"]
        if body.get("base_url"):
            url = body["base_url"].strip()
            if Config.LLM_PROVIDER != "gemini" and url and "chat/completions" not in url:
                url = url.rstrip("/") + "/chat/completions"
            Config.LLM_BASE_URL = url

        import sys
        print(f"[TEST] provider={Config.LLM_PROVIDER} model={Config.LLM_MODEL} url={Config.LLM_BASE_URL} key={'set' if Config.LLM_API_KEY else 'empty'}", flush=True, file=sys.stderr)

        # Raw probe: send request and return the actual response body for debugging
        if body.get("debug"):
            import urllib.request as _ur
            import urllib.error as _ue
            _payload = json.dumps({
                "model": Config.LLM_MODEL,
                "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
                "max_tokens": 10, "stream": False,
            }).encode()
            _headers = {"Content-Type": "application/json"}
            if Config.LLM_API_KEY:
                _headers["Authorization"] = f"Bearer {Config.LLM_API_KEY}"
            try:
                _req = _ur.Request(Config.LLM_BASE_URL, data=_payload, headers=_headers, method="POST")
                with _ur.urlopen(_req, timeout=15) as _r:
                    _raw = _r.read().decode("utf-8", errors="ignore")
                return jsonify({"raw": _raw[:2000], "status": _r.status})
            except _ue.HTTPError as _e:
                return jsonify({"raw": _e.read().decode("utf-8", errors="ignore")[:2000], "http_error": _e.code})
            except Exception as _e:
                return jsonify({"raw": str(_e)})

        client = LLMClient()
        ok, error_msg = client.ping()
        stats  = client.get_token_stats()

        return jsonify({
            "success":      ok,
            "provider":     Config.LLM_PROVIDER,
            "model":        Config.LLM_MODEL,
            "base_url":     Config.LLM_BASE_URL,
            "tokens_used":  stats["total_tokens"],
            "error":        error_msg,
        })
    finally:
        Config.LLM_PROVIDER, Config.LLM_API_KEY, Config.LLM_MODEL, Config.LLM_BASE_URL = orig


@settings_bp.route("/api/clear-cache", methods=["POST"])
def api_clear_cache():
    cache_file = os.path.join(_data_dir, "papers_cache.json")
    try:
        with open(cache_file, "w") as f:
            f.write("{}")
        return jsonify({"status": "cleared"})
    except Exception:
        return jsonify({"status": "ok"})


@settings_bp.route("/api/clear-sessions", methods=["POST"])
def api_clear_sessions():
    history_file = os.path.join(_data_dir, "session_history.json")
    try:
        with open(history_file, "w") as f:
            f.write("[]")
        return jsonify({"status": "cleared"})
    except Exception:
        return jsonify({"status": "ok"})
