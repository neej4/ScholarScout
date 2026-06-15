"""Unit tests for idea-level evidence grounding helpers."""

from src.core.evidence import build_evidence_pack, build_paper_ref_map, resolve_paper_refs


def test_build_paper_ref_map_uses_p_numbers(stub_papers):
    refs = build_paper_ref_map(stub_papers)

    assert refs["P1"].id == "2401.12345"
    assert refs["P2"].title == "Reinforcement Learning in Robotics"


def test_resolve_paper_refs_reports_invalid_refs(stub_papers):
    resolved = resolve_paper_refs(["P1", "p2", "P99", "not-a-ref"], stub_papers)

    assert [paper.id for paper in resolved.valid_papers] == ["2401.12345", "2401.67890"]
    assert resolved.invalid_refs == ["P99", "not-a-ref"]


def test_build_evidence_pack_scores_claims_with_valid_sources(stub_papers):
    raw_idea = {
        "idea_title": "Grounded robotics control benchmark",
        "abstract": "Robotics control can use reinforcement learning for safer policies.",
        "inspired_by_ids": ["P2"],
        "evidence_claims": [
            {
                "claim": "The idea relies on reinforcement learning for robotic control.",
                "paper_ids": ["P2"],
            }
        ],
    }

    pack = build_evidence_pack(raw_idea, stub_papers)

    assert pack["grounding_score"] >= 60
    assert pack["source_papers"][0]["id"] == "2401.67890"
    assert pack["evidence_claims"][0]["paper_ids"] == ["P2"]
    assert "weak_grounding" not in pack["risk_flags"]


def test_build_evidence_pack_flags_invalid_and_malformed_refs(stub_papers):
    raw_idea = {
        "idea_title": "Unverified idea",
        "inspired_by_ids": ["P42"],
        "evidence_claims": [
            {"claim": "This cites a missing paper.", "paper_ids": ["P42"]},
            "A malformed claim without evidence.",
        ],
    }

    pack = build_evidence_pack(raw_idea, stub_papers)

    assert pack["grounding_score"] < 60
    assert "llm_unverified_reference" in pack["risk_flags"]
    assert "weak_grounding" in pack["risk_flags"]
    assert pack["evidence_claims"][0]["invalid_paper_ids"] == ["P42"]


def test_build_evidence_pack_is_safe_without_papers():
    pack = build_evidence_pack({"idea_title": "No papers", "evidence_claims": []}, [])

    assert pack["source_papers"] == []
    assert pack["grounding_score"] == 0
    assert "low_source_count" in pack["risk_flags"]
    assert "missing_evidence_claims" in pack["risk_flags"]
