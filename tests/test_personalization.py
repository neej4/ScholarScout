"""Tests for personality/profile steering helpers."""

from src.core.personalization import (
    build_personalization_brief,
    normalize_user_profile,
    summarize_feedback_memory,
)


def test_normalize_user_profile_handles_partial_input():
    profile = normalize_user_profile({"work_style": "practical", "constraints": "limited GPU"})

    assert profile["work_style"] == "practical"
    assert profile["scope_preference"] == "balanced"
    assert profile["constraints"] == "limited GPU"


def test_summarize_feedback_memory_handles_legacy_and_rich_feedback():
    summary = summarize_feedback_memory({
        "Idea A": "up",
        "Idea B": {"vote": "down", "reasons": ["too generic", "too broad"], "note": "feels vague"},
        "Idea C": {"vote": "up", "reasons": ["practical", "feasible"]},
    })

    assert "practical" in summary["top_likes"]
    assert "too generic" in summary["top_dislikes"]
    assert "feels vague" in summary["summary"]


def test_build_personalization_brief_includes_profile_and_feedback():
    brief = build_personalization_brief(
        {"work_style": "practical", "scope_preference": "narrow"},
        {"Idea X": {"vote": "down", "reasons": ["too broad"]}},
    )

    assert "work_style: practical" in brief
    assert "scope_preference: narrow" in brief
    assert "User often dislikes: too broad" in brief
