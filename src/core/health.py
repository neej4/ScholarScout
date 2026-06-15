"""
Startup Health Check & Cache Hygiene.

Runs on server start to validate configuration, check connectivity,
and clean up stale data. Reports issues to terminal without blocking startup.

Also provides usage telemetry (local-only, no network).
"""
import os
import json
import time
from datetime import datetime, timezone, timedelta
from typing import List, Tuple

from src.core.config import Config


def run_health_check() -> List[Tuple[str, str, str]]:
    """Run all health checks and return results.

    Returns:
        List of (check_name, status, message) tuples.
        status is one of: "ok", "warn", "fail"
    """
    results = []
    results.append(_check_config_yaml())
    results.append(_check_data_dir())
    results.append(_check_cache_file())
    results.append(_check_session_history())
    results.append(_check_llm_config())
    return results


def print_health_report(results: List[Tuple[str, str, str]]):
    """Print a formatted health report to terminal."""
    icons = {"ok": "+", "warn": "~", "fail": "!"}
    print("  Health Check:")
    for name, status, msg in results:
        icon = icons.get(status, "?")
        print(f"    [{icon}] {name}: {msg}")
    fails = sum(1 for _, s, _ in results if s == "fail")
    warns = sum(1 for _, s, _ in results if s == "warn")
    if fails:
        print(f"  ⚠ {fails} issue(s) found. Check config.yaml.")
    elif warns:
        print(f"  {warns} warning(s) — non-critical.")
    else:
        print("  All checks passed.")


def run_cache_hygiene() -> dict:
    """Clean up stale papers from cache based on CACHE_EXPIRY_DAYS.

    Runs on startup (not just during pipeline). Returns stats.
    """
    stats = {"expired": 0, "total_before": 0, "total_after": 0, "file_exists": False}

    if not os.path.exists(Config.CACHE_FILE):
        return stats

    stats["file_exists"] = True

    try:
        with open(Config.CACHE_FILE, "r", encoding="utf-8") as f:
            cache = json.load(f)
    except (json.JSONDecodeError, IOError):
        return stats

    if not isinstance(cache, dict):
        return stats

    stats["total_before"] = len(cache)
    expiry_days = Config.CACHE_EXPIRY_DAYS

    if expiry_days <= 0:
        stats["total_after"] = len(cache)
        return stats

    cutoff = (datetime.now(timezone.utc) - timedelta(days=expiry_days)).strftime("%Y-%m-%d")
    cleaned = {k: v for k, v in cache.items() if v.get("submitted", "9999") >= cutoff}
    expired = len(cache) - len(cleaned)

    if expired > 0:
        try:
            with open(Config.CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cleaned, f, ensure_ascii=False)
        except IOError:
            pass

    stats["expired"] = expired
    stats["total_after"] = len(cleaned)
    return stats


def record_usage(event: str, **kwargs):
    """Append a usage event to local telemetry file.

    Events: pipeline_run, quick_mode, impl_search, deepdive, novelty_check, export
    No network calls — purely local file append.
    """
    stats_file = os.path.join(Config.DATA_DIR, "usage_stats.jsonl")
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **kwargs,
    }
    try:
        with open(stats_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except IOError:
        pass  # Non-critical — never fail on telemetry


def get_usage_summary() -> dict:
    """Read usage stats and return a summary.

    Returns counts per event type and total sessions.
    """
    stats_file = os.path.join(Config.DATA_DIR, "usage_stats.jsonl")
    summary = {"total_events": 0, "events": {}}

    if not os.path.exists(stats_file):
        return summary

    try:
        with open(stats_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    event = entry.get("event", "unknown")
                    summary["events"][event] = summary["events"].get(event, 0) + 1
                    summary["total_events"] += 1
                except json.JSONDecodeError:
                    continue
    except IOError:
        pass

    return summary


# ─── Individual health checks ──────────────────────────────────────────────────

def _check_config_yaml() -> Tuple[str, str, str]:
    """Check if config.yaml exists and is valid YAML."""
    if not os.path.exists(Config.CONFIG_FILE):
        return ("config.yaml", "warn", "Not found — using defaults")
    try:
        import yaml
        with open(Config.CONFIG_FILE, "r") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            return ("config.yaml", "fail", "Invalid format (not a dict)")
        return ("config.yaml", "ok", "Valid")
    except Exception as e:
        return ("config.yaml", "fail", f"Parse error: {e}")


def _check_data_dir() -> Tuple[str, str, str]:
    """Check if data directory exists and is writable."""
    if not os.path.exists(Config.DATA_DIR):
        try:
            os.makedirs(Config.DATA_DIR, exist_ok=True)
            return ("data/", "ok", "Created")
        except Exception as e:
            return ("data/", "fail", f"Cannot create: {e}")

    # Test write
    test_file = os.path.join(Config.DATA_DIR, ".write_test")
    try:
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        return ("data/", "ok", "Writable")
    except Exception as e:
        return ("data/", "fail", f"Not writable: {e}")


def _check_cache_file() -> Tuple[str, str, str]:
    """Check if papers_cache.json is valid."""
    if not os.path.exists(Config.CACHE_FILE):
        return ("papers_cache", "ok", "Empty (will be created on first Run)")
    try:
        with open(Config.CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return ("papers_cache", "fail", "Invalid format (expected dict)")
        return ("papers_cache", "ok", f"{len(data)} papers cached")
    except json.JSONDecodeError as e:
        return ("papers_cache", "fail", f"Corrupt JSON: {e}")
    except IOError as e:
        return ("papers_cache", "warn", f"Cannot read: {e}")


def _check_session_history() -> Tuple[str, str, str]:
    """Check if session_history.json is valid."""
    history_file = os.path.join(Config.DATA_DIR, "session_history.json")
    if not os.path.exists(history_file):
        return ("session_history", "ok", "Empty (no sessions yet)")
    try:
        with open(history_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return ("session_history", "fail", "Invalid format (expected list)")
        return ("session_history", "ok", f"{len(data)} sessions")
    except json.JSONDecodeError as e:
        return ("session_history", "fail", f"Corrupt JSON: {e}")
    except IOError as e:
        return ("session_history", "warn", f"Cannot read: {e}")


def _check_llm_config() -> Tuple[str, str, str]:
    """Check if LLM configuration looks valid (without making a network call)."""
    provider = Config.LLM_PROVIDER
    api_key = Config.LLM_API_KEY
    model = Config.LLM_MODEL
    base_url = Config.LLM_BASE_URL

    if not provider:
        return ("LLM config", "fail", "No provider set")

    if provider in ("gemini", "groq", "openrouter", "openai") and not api_key:
        return ("LLM config", "warn", f"Provider '{provider}' set but no API key found")

    if provider == "ollama":
        return ("LLM config", "ok", f"Ollama → {model} (local)")

    if not model:
        return ("LLM config", "warn", f"Provider '{provider}' but no model specified")

    return ("LLM config", "ok", f"{provider} → {model}")
