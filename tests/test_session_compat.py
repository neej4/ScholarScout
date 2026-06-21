from src.core.session_compat import normalize_idea, normalize_session


def test_normalize_session_adds_gap_defaults_for_legacy_ideas():
    legacy = {
        "timestamp": "2026-06-16T10:00:00Z",
        "date": "2026-06-16",
        "categories": ["cs.AI"],
        "papers_total": 12,
        "ideas_total": 1,
        "ideas": [
            {
                "idea_title": "Legacy idea",
                "field": "cs.AI",
                "abstract": "Old snapshot without gap-first metadata.",
            }
        ],
    }

    normalized = normalize_session(legacy)
    idea = normalized["ideas"][0]

    assert normalized["schema_version"] == "1.6.5"
    assert normalized["gap_steering"] == "balanced"
    assert normalized["gap_candidates_total"] == 0
    assert normalized["gap_diagnostics"] == []
    assert normalized["contributed_papers_total"] == 0
    assert normalized["avg_supporting_papers"] == 0.0
    assert idea["gap_steering"] == "balanced"
    assert idea["anchor_papers"] == []
    assert idea["supporting_papers"] == []
    assert idea["landscape_gap_summary"] == ""
    assert idea["coverage_count"] == 0
    assert idea["coverage_ratio"] == 0.0
    assert idea["gap_type"] == ""
    assert normalize_session(normalized) == normalized


def test_normalize_idea_rejects_non_dict():
    assert normalize_idea(None) == {}
    assert normalize_idea("legacy") == {}
