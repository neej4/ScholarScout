"""Backward-compatible normalization for saved sessions and snapshots."""

from __future__ import annotations

from typing import Any


SCHEMA_VERSION = "1.6.5"

_IDEA_DEFAULTS = {
    "source_papers": list,
    "evidence_claims": list,
    "grounding_score": int,
    "risk_flags": list,
    "fit_to_user_summary": str,
    "misalignment_flags": list,
    "user_fit_score": int,
    "goal_style": str,
    "gap_steering": lambda: "balanced",
    "anchor_papers": list,
    "supporting_papers": list,
    "landscape_gap_summary": str,
    "coverage_count": int,
    "coverage_ratio": float,
    "gap_type": str,
}

_RUN_DEFAULTS = {
    "gap_steering": lambda: "balanced",
    "gap_candidates_total": int,
    "gap_diagnostics": list,
    "contributed_papers_total": int,
    "avg_supporting_papers": float,
}


def normalize_idea(idea: Any) -> dict:
    if not isinstance(idea, dict):
        return {}

    for key, factory in _IDEA_DEFAULTS.items():
        if key not in idea or idea[key] is None:
            idea[key] = factory()
    return idea


def normalize_session(session: Any) -> dict:
    if not isinstance(session, dict):
        return {}

    for key, factory in _RUN_DEFAULTS.items():
        if key not in session or session[key] is None:
            session[key] = factory()

    session["schema_version"] = session.get("schema_version") or SCHEMA_VERSION

    ideas = session.get("ideas")
    if isinstance(ideas, list):
        session["ideas"] = [normalize_idea(idea) for idea in ideas]

    return session


def normalize_history(history: Any) -> list:
    if not isinstance(history, list):
        return []
    return [normalize_session(session) for session in history]
