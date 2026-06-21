"""Generator parser tests for evidence-first idea output."""

import json
from copy import deepcopy
from unittest.mock import Mock

from src.core.generator import IdeaGenerator


def _generator():
    llm = Mock()
    llm._emit = Mock()
    return IdeaGenerator(llm)


def test_academic_parser_accepts_evidence_claims(stub_papers, stub_trend):
    generator = _generator()
    trend = stub_trend
    trend.ref_papers = stub_papers
    response = json.dumps([
        {
            "idea_title": "Evidence grounded NLP benchmark",
            "difficulty": "Master's",
            "abstract": "A benchmark for NLP models grounded in fetched papers.",
            "why_hard": "Requires careful evaluation.",
            "methodology_hint": "Compare recent architectures.",
            "next_steps": ["Read papers", "Build baseline", "Evaluate"],
            "key_paper_ids": ["P1", "P3"],
            "landscape_gap_summary": "Recent work still lacks a grounded benchmark for fetched-paper-aware NLP evaluation.",
            "gap_type": "missing_evaluation",
            "anchor_paper_ids": ["P1"],
            "supporting_paper_ids": ["P1", "P3"],
            "resources_needed": "GPU, datasets",
            "prerequisites": ["Python", "NLP"],
            "inspired_by_ids": ["P1"],
            "why_this_idea": "It addresses low-resource model evaluation.",
            "quality_score": 8,
            "evidence_claims": [
                {"claim": "The idea builds on NLP architecture work.", "paper_ids": ["P1"]}
            ],
        }
    ])

    ideas = generator._parse_academic_response(response, stub_papers, "cs.CL", set(), trend)

    assert len(ideas) == 1
    assert ideas[0].source_papers
    assert ideas[0].evidence_claims[0]["paper_ids"] == ["P1"]
    assert ideas[0].grounding_score > 0
    assert ideas[0].anchor_papers
    assert ideas[0].coverage_count >= 1


def test_academic_parser_flags_invalid_evidence_refs(stub_papers, stub_trend):
    generator = _generator()
    response = json.dumps([
        {
            "idea_title": "Invalid citation benchmark",
            "difficulty": "Master's",
            "abstract": "A benchmark with a bad citation.",
            "why_hard": "Requires validation.",
            "methodology_hint": "Validate every reference.",
            "next_steps": ["Check refs", "Run baseline", "Write report"],
            "key_paper_ids": ["P99"],
            "resources_needed": "GPU",
            "prerequisites": ["Python"],
            "inspired_by_ids": ["P42"],
            "why_this_idea": "It tests validation.",
            "quality_score": 8,
            "evidence_claims": [
                {"claim": "This claim cites unavailable paper context.", "paper_ids": ["P42"]}
            ],
        }
    ])

    ideas = generator._parse_academic_response(response, stub_papers, "cs.CL", set(), stub_trend)

    assert len(ideas) == 1
    assert "llm_unverified_reference" in ideas[0].risk_flags


def test_academic_parser_keeps_legacy_response_without_evidence(stub_papers, stub_trend):
    generator = _generator()
    response = json.dumps([
        {
            "idea_title": "Legacy parser idea",
            "difficulty": "Master's",
            "abstract": "A legacy idea without evidence_claims.",
            "why_hard": "Requires backward compatibility.",
            "methodology_hint": "Parse old JSON.",
            "next_steps": ["Parse", "Serialize", "Open"],
            "key_paper_ids": ["P1"],
            "resources_needed": "Laptop",
            "prerequisites": ["Python"],
            "inspired_by_ids": ["P1"],
            "why_this_idea": "Old snapshots should still work.",
            "quality_score": 7,
        }
    ])

    ideas = generator._parse_academic_response(response, stub_papers, "cs.CL", set(), stub_trend)

    assert len(ideas) == 1
    assert ideas[0].to_dict()["evidence_claims"] == []
    assert "missing_evidence_claims" in ideas[0].risk_flags


def test_academic_parser_skips_duplicate_gap_clusters(stub_papers, stub_trend):
    generator = _generator()
    response = json.dumps([
        {
            "idea_title": "Idea one",
            "difficulty": "Master's",
            "abstract": "First idea.",
            "why_hard": "Needs care.",
            "methodology_hint": "Test one setup.",
            "next_steps": ["A", "B", "C"],
            "key_paper_ids": ["P1"],
            "anchor_paper_ids": ["P1"],
            "supporting_paper_ids": ["P1", "P3"],
            "landscape_gap_summary": "Need stronger grounded benchmark coverage.",
            "gap_type": "missing_evaluation",
            "resources_needed": "Laptop",
            "prerequisites": ["Python"],
            "inspired_by_ids": ["P1"],
            "why_this_idea": "Fills an evaluation gap.",
            "quality_score": 8,
        },
        {
            "idea_title": "Idea two",
            "difficulty": "Master's",
            "abstract": "Second idea.",
            "why_hard": "Needs care too.",
            "methodology_hint": "Test one setup again.",
            "next_steps": ["A", "B", "C"],
            "key_paper_ids": ["P1"],
            "anchor_paper_ids": ["P1"],
            "supporting_paper_ids": ["P1", "P3"],
            "landscape_gap_summary": "Need stronger grounded benchmark coverage.",
            "gap_type": "missing_evaluation",
            "resources_needed": "Laptop",
            "prerequisites": ["Python"],
            "inspired_by_ids": ["P1"],
            "why_this_idea": "Fills an evaluation gap too.",
            "quality_score": 8,
        }
    ])

    ideas = generator._parse_academic_response(response, stub_papers, "cs.CL", set(), stub_trend)

    assert len(ideas) == 1


def test_refine_with_critique_updates_visible_fields(stub_idea):
    generator = _generator()
    generator.llm.call.return_value = json.dumps([
        {
            "idea_title": "Scoped Transformer for Low-Resource Morphology",
            "abstract": "This version narrows the task to morphology transfer for low-resource languages.",
            "why_hard": "Evaluation is sensitive to tiny datasets and annotation noise.",
            "methodology_hint": "Benchmark compact transformer variants on one carefully curated language family.",
            "next_steps": ["Freeze task scope", "Collect one benchmark dataset", "Run a compact baseline"],
            "why_this_idea": "It is narrower, measurable, and easier to complete in one thesis cycle.",
            "quality_score": 9,
            "critique_summary": "The original draft was promising but still too broad for a master's timeline.",
            "refinement_summary": "The revised version reduces scope, sharpens the target task, and clarifies first experiments.",
            "novelty_claim": "Novelty comes from focusing on morphology transfer under severe data scarcity instead of generic multilingual NLP.",
            "feasibility_warning": "The dataset may still be too small, so benchmark choice matters.",
            "fit_to_user_summary": "Good fit for a user who prefers narrow NLP thesis ideas with limited compute.",
            "misalignment_flags": ["needs careful dataset selection"],
            "user_fit_score": 8,
            "refined": True,
        }
    ])

    idea = deepcopy(stub_idea)
    refined = generator._refine_ideas_with_critique([idea], "en")

    assert refined[0].idea_title == "Scoped Transformer for Low-Resource Morphology"
    assert refined[0].refined is True
    assert "too broad" in refined[0].critique_summary
    assert "reduces scope" in refined[0].refinement_summary
    assert refined[0].quality_score == 9
    assert refined[0].user_fit_score == 8
    assert "limited compute" in refined[0].fit_to_user_summary


def test_refine_with_critique_falls_back_on_bad_json(stub_idea):
    generator = _generator()
    generator.llm.call.return_value = "{bad json"

    idea = deepcopy(stub_idea)
    original_title = idea.idea_title
    original_summary = idea.refinement_summary
    refined = generator._refine_ideas_with_critique([idea], "en")

    assert refined[0].idea_title == original_title
    assert refined[0].refinement_summary == original_summary
    assert refined[0].refined is False
