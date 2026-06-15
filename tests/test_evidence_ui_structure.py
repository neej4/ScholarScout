"""Structural tests for grounding and self-improvement UI rendering."""

from pathlib import Path


def _dashboard() -> str:
    path = Path(__file__).parent.parent / "src" / "web" / "templates" / "dashboard.html"
    return path.read_text(encoding="utf-8")


def test_grounding_badge_helper_exists():
    html = _dashboard()

    assert "function _groundingBadge" in html
    assert "Grounded" in html
    assert "Partial" in html
    assert "Caution" in html


def test_refinement_helpers_and_sections_exist():
    html = _dashboard()

    assert "function _renderRefinementChip" in html
    assert "function _renderRefinementSections" in html
    assert "function _renderUserFitSections" in html
    assert "Internal Critique" in html
    assert "Why This Version Is Stronger" in html
    assert "Sharper Novelty Claim" in html
    assert "Feasibility Warning" in html
    assert "Fit To You" in html
    assert "Still Misaligned" in html


def test_card_and_modal_surface_refinement_state():
    html = _dashboard()

    assert "refinement-chip" in html
    assert "idea.refinement_summary" in html
    assert "_renderRefinementChip(idea)" in html
    assert "_renderRefinementSections(idea)" in html


def test_modal_export_and_copy_include_refinement_content():
    html = _dashboard()

    assert "printWin.document.write(`<h2>Internal Critique" in html
    assert "printWin.document.write(`<h2>Why This Version Is Stronger" in html
    assert "parts.push(`\\nInternal critique:" in html
    assert "parts.push(`\\nWhy stronger:" in html
    assert "Fit to user" in html


def test_personality_steering_ui_and_feedback_modal_exist():
    html = _dashboard()

    assert "Personality steering" in html
    assert "id=\"settWorkStyle\"" in html
    assert "id=\"settScopePreference\"" in html
    assert "id=\"settRiskTolerance\"" in html
    assert "id=\"settOutputTone\"" in html
    assert "id=\"feedbackReasonModal\"" in html
    assert "function openFeedbackReasonModal" in html
    assert "function submitFeedbackReason" in html
