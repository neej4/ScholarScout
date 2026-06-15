"""Helpers for aligning idea generation with user personality and feedback."""

from __future__ import annotations

import json
from typing import Any, Dict, List


DEFAULT_PROFILE = {
    "work_style": "balanced",
    "scope_preference": "balanced",
    "risk_tolerance": "medium",
    "output_tone": "academic",
    "constraints": "",
}


def normalize_user_profile(raw: Any) -> Dict[str, str]:
    """Accept dict/JSON/string and return a safe user profile mapping."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            raw = {}
    if not isinstance(raw, dict):
        raw = {}

    profile = dict(DEFAULT_PROFILE)
    for key in profile:
        value = raw.get(key, profile[key])
        profile[key] = str(value).strip() if value is not None else profile[key]
    return profile


def summarize_feedback_memory(raw: Any, limit: int = 5) -> Dict[str, Any]:
    """Summarize local feedback entries into compact likes/dislikes patterns."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            raw = []

    entries: List[dict] = []
    if isinstance(raw, dict):
        for title, value in raw.items():
            if isinstance(value, str):
                entries.append({"title": title, "vote": value, "reasons": []})
            elif isinstance(value, dict):
                item = {"title": title, **value}
                item.setdefault("reasons", [])
                entries.append(item)
    elif isinstance(raw, list):
        for value in raw:
            if isinstance(value, dict):
                item = dict(value)
                item.setdefault("reasons", [])
                entries.append(item)

    likes: Dict[str, int] = {}
    dislikes: Dict[str, int] = {}
    notes: List[str] = []
    for entry in entries:
        vote = str(entry.get("vote", "")).lower()
        reasons = entry.get("reasons", [])
        if not isinstance(reasons, list):
            reasons = [str(reasons)]
        for reason in reasons:
            key = str(reason).strip()
            if not key:
                continue
            bucket = likes if vote == "up" else dislikes
            bucket[key] = bucket.get(key, 0) + 1
        note = str(entry.get("note", "")).strip()
        if note:
            notes.append(note)

    top_likes = [k for k, _ in sorted(likes.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]]
    top_dislikes = [k for k, _ in sorted(dislikes.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]]
    note_preview = notes[:2]
    summary_lines = []
    if top_likes:
        summary_lines.append("User often likes: " + ", ".join(top_likes))
    if top_dislikes:
        summary_lines.append("User often dislikes: " + ", ".join(top_dislikes))
    if note_preview:
        summary_lines.append("Recent feedback notes: " + " | ".join(note_preview))
    return {
        "top_likes": top_likes,
        "top_dislikes": top_dislikes,
        "notes": note_preview,
        "summary": " ".join(summary_lines).strip(),
    }


def build_personalization_brief(user_profile: Any, feedback_memory: Any) -> str:
    """Format a short instruction block for prompts."""
    profile = normalize_user_profile(user_profile)
    feedback = summarize_feedback_memory(feedback_memory)

    lines = [
        "=== USER PREFERENCE PROFILE ===",
        f"- work_style: {profile['work_style']}",
        f"- scope_preference: {profile['scope_preference']}",
        f"- risk_tolerance: {profile['risk_tolerance']}",
        f"- output_tone: {profile['output_tone']}",
    ]
    if profile["constraints"]:
        lines.append(f"- constraints: {profile['constraints']}")
    if feedback["summary"]:
        lines.append("=== FEEDBACK MEMORY ===")
        lines.append(feedback["summary"])
    return "\n".join(lines)
