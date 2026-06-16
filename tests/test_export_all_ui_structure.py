"""Structural tests for the Export All feature."""

from pathlib import Path


def _dashboard() -> str:
    path = Path(__file__).parent.parent / "src" / "web" / "templates" / "dashboard.html"
    return path.read_text(encoding="utf-8")


def test_export_all_button_exists():
    html = _dashboard()
    assert 'id="btnExportAll"' in html
    assert 'onclick="exportAllIdeas()"' in html


def test_export_all_helpers_exist():
    html = _dashboard()
    assert "function exportAllIdeas()" in html
    assert "function _updateExportAllButton()" in html
    assert "scholarscout_ideas_" in html
    assert "function _buildIdeaMarkdown" in html
    assert "## Evidence Pack" in html


def test_run_insights_and_feedback_memory_helpers_exist():
    html = _dashboard()
    assert 'id="runInsights"' in html
    assert "function updateRunInsights" in html
    assert "function summarizeFeedbackMemory" in html
    assert 'id="feedbackMemorySummary"' in html


def test_export_selected_and_preset_controls_exist():
    html = _dashboard()
    assert 'id="btnExportSelected"' in html
    assert 'onclick="exportSelectedIdeas()"' in html
    assert 'id="presetSelect"' in html
    assert 'onclick="saveCurrentPreset()"' in html
    assert 'onclick="applySelectedPreset()"' in html
    assert "function exportSelectedIdeas()" in html
    assert "function saveCurrentPreset()" in html
    assert "function loadRunPresets()" in html


def test_goal_style_ui_and_helpers_exist():
    html = _dashboard()
    assert 'id="goalStyleSelect"' in html
    assert "Goal Style" in html
    assert 'id="goalStyleCards"' in html
    assert "function suggestGoalStyleForGoal" in html
    assert "function syncGoalStyleUI" in html
    assert "scholarscout_goal_style" in html
