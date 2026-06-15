"""Structural tests for CapabilityScout dashboard integration."""

import re
from pathlib import Path


def _dashboard() -> str:
    path = Path(__file__).parent.parent / "src" / "web" / "templates" / "dashboard.html"
    return path.read_text(encoding="utf-8")


def test_capability_mode_card_exists():
    html = _dashboard()
    assert 'data-mode="capability"' in html
    assert "Capability" in html


def test_capability_goal_option_and_cards_exist():
    html = _dashboard()
    assert '<option value="CAPABILITY_MATCH">' in html
    assert 'id="goalCardsCapability"' in html
    assert 'data-value="CAPABILITY_MATCH"' in html


def test_capability_form_section_exists():
    html = _dashboard()
    required_ids = [
        'capabilitySection',
        'capHasDataset',
        'capDatasetSize',
        'capPublicData',
        'capComputeTier',
        'capBudget',
        'capMlLevel',
        'capRisk',
        'capOutputType',
    ]
    for el_id in required_ids:
        assert f'id="{el_id}"' in html, f"{el_id} not found"


def test_capability_start_pipeline_branch_exists():
    html = _dashboard()
    assert "goal === 'CAPABILITY_MATCH'" in html
    assert "runCapabilityMode(" in html
    assert "fetch('/api/capability'" in html


def test_capability_profile_persistence_helpers_exist():
    html = _dashboard()
    assert "scholarscout_capability_profile" in html
    assert "collectCapabilityProfile" in html
    assert "applyCapabilityProfile" in html


def test_capability_results_renderer_exists():
    html = _dashboard()
    assert "renderCapabilityResults" in html
    assert "mapCapabilityGapToIdea" in html
    assert "fit_reason" in html


def test_open_idea_detail_can_show_capability_fit_section():
    html = _dashboard()
    assert "Fit Summary" in html
    assert "fit_reasons" in html
