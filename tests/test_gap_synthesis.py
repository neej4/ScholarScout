from src.core.gap_synthesis import synthesize_gap_candidates


def test_gap_synthesis_builds_candidates_from_trend(stub_trend, stub_papers):
    trend = stub_trend
    trend.ref_papers = stub_papers
    trend.cross_pollination = ["Use reinforcement learning signals to improve low-resource NLP adaptation."]

    candidates = synthesize_gap_candidates(trend, stub_papers, limit=6)

    assert candidates
    assert all(candidate["paper_ids"] for candidate in candidates)
    assert any(candidate["gap_type"] == "underexplored_combination" for candidate in candidates)


def test_gap_synthesis_handles_sparse_paper_text(stub_trend, stub_papers):
    trend = stub_trend
    for paper in stub_papers:
        paper.abstract = ""

    candidates = synthesize_gap_candidates(trend, stub_papers, limit=4)

    assert candidates
    assert len(candidates) <= 4
    assert all(candidate["strength_score"] >= 3 for candidate in candidates)


def test_gap_synthesis_steering_prioritizes_practical_gaps(stub_trend, stub_papers):
    practical_trend = stub_trend.__class__(
        category="cs.AI",
        paper_count=3,
        top_keywords=["agents", "evaluation"],
        emerging_methods=["tool use"],
        research_gaps=["Deployment latency remains a major blocker", "Need stronger real-world evaluation"],
        ref_papers=[],
    )
    practical_papers = [
        stub_papers[0].__class__(
            id="p1",
            title="Deployment latency for multi-agent systems",
            category="cs.AI",
            authors="A",
            abstract="Latency and deployment memory issues limit production use.",
            link="https://example.com/p1",
            submitted_date="2026-01-01",
        ),
        stub_papers[0].__class__(
            id="p2",
            title="Realistic evaluation of agent workflows",
            category="cs.AI",
            authors="B",
            abstract="Benchmark and real-world evaluation remain missing for many systems.",
            link="https://example.com/p2",
            submitted_date="2026-01-02",
        ),
    ]

    practical = synthesize_gap_candidates(practical_trend, practical_papers, limit=3, steering="practical")
    breakthrough = synthesize_gap_candidates(practical_trend, practical_papers, limit=3, steering="breakthrough")

    assert practical
    assert breakthrough
    assert practical[0]["gap_type"] in {"implementation_bottleneck", "recurring_limitation", "missing_evaluation"}
