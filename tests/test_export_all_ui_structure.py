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
