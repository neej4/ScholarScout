"""Tests for Goal Style defaults and prompt steering."""

from unittest.mock import MagicMock, Mock

from src.core.generator import (
    IdeaGenerator,
    allowed_goal_styles_for_mode,
    suggest_goal_style,
)
from src.core.models import Paper, TrendAnalysis


def _trend() -> TrendAnalysis:
    return TrendAnalysis(
        category="cs.AI",
        paper_count=2,
        top_keywords=["agents", "planning"],
        emerging_methods=["tool use"],
        research_gaps=["weak multi-paper synthesis"],
        ref_papers=[
            Paper(
                id="paper-1",
                title="Agent Planning with Tool Use",
                category="cs.AI",
                authors="A",
                abstract="A paper about coordinated tool use.",
                link="https://example.com/1",
                submitted_date="2026-01-01",
            ),
            Paper(
                id="paper-2",
                title="Long-horizon Multi-agent Coordination",
                category="cs.AI",
                authors="B",
                abstract="A paper about long horizon coordination.",
                link="https://example.com/2",
                submitted_date="2026-01-02",
            ),
        ],
    )


def test_goal_style_defaults_follow_goal_mapping():
    assert suggest_goal_style("PUBLICATION") == "breakthrough"
    assert suggest_goal_style("THESIS") == "thesis"
    assert suggest_goal_style("FEATURE") == "project"
    assert suggest_goal_style("HACKATHON") == "assignment"
    assert suggest_goal_style("SYNTHESIS") == ""


def test_allowed_goal_styles_follow_mode():
    assert allowed_goal_styles_for_mode("academic") == ["breakthrough", "thesis", "project", "assignment"]
    assert allowed_goal_styles_for_mode("product") == ["breakthrough", "project"]
    assert allowed_goal_styles_for_mode("develop") == ["breakthrough", "project", "assignment"]
    assert allowed_goal_styles_for_mode("review") == []


def test_goal_style_is_injected_into_generation_prompt():
    mock_llm = Mock()
    mock_llm.call = MagicMock(return_value="[]")
    mock_llm._emit = MagicMock()
    generator = IdeaGenerator(mock_llm)

    generator.generate(
        _trend(),
        set(),
        n=1,
        research_context="building an internal research copilot",
        language="en",
        goal="FEATURE",
        goal_style="breakthrough",
        gap_steering="practical",
    )

    prompt = mock_llm.call.call_args[0][0]
    assert "Goal style: breakthrough" in prompt
    assert "Gap steering: practical" in prompt
    assert "multi-paper" in prompt.lower() or "landscape" in prompt.lower()
