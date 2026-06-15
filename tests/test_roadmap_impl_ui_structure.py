"""Structural tests for roadmap persistence and implementation layout fixes."""

from pathlib import Path


def _dashboard() -> str:
    path = Path(__file__).parent.parent / "src" / "web" / "templates" / "dashboard.html"
    return path.read_text(encoding="utf-8")


def test_roadmap_state_persistence_helpers_exist():
    html = _dashboard()
    assert "scout_roadmaps" in html
    assert "scout_active_roadmap" in html
    assert "function _persistRoadmaps" in html
    assert "function _restoreRoadmaps" in html


def test_roadmap_visual_upgrade_hooks_exist():
    html = _dashboard()
    assert "roadmap-legend" in html
    assert "roadmap-lane" in html
    assert "roadmap-overview" in html


def test_implementation_layout_uses_dedicated_mount_logic():
    html = _dashboard()
    assert "function _getImplementationMount" in html
    assert "impl-inline-host" in html
    assert "insertAdjacentElement('afterend'" in html or 'insertAdjacentElement("afterend"' in html
