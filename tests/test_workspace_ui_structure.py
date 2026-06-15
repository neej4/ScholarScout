"""Structural tests for the prompt-first ScholarScout workspace refresh."""

from pathlib import Path


def _dashboard() -> str:
    path = Path(__file__).parent.parent / "src" / "web" / "templates" / "dashboard.html"
    return path.read_text(encoding="utf-8")


def test_prompt_first_workspace_shell_exists():
    html = _dashboard()

    assert "Scout Dock" in html
    assert 'id="commandInput"' in html
    assert "Research Command" in html
    assert "class=\"context-rail\"" in html


def test_workspace_meta_and_presets_exist():
    html = _dashboard()

    assert "promptModeMeta" in html
    assert "promptGoalMeta" in html
    assert "promptLangMeta" in html
    assert "class=\"prompt-chip scout-preset\"" in html
    assert "function _updateWorkspaceChrome" in html
