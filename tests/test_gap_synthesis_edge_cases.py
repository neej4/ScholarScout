from src.core.gap_synthesis import synthesize_gap_candidates


def test_gap_synthesis_returns_empty_for_empty_papers(stub_trend):
    assert synthesize_gap_candidates(stub_trend, [], limit=4) == []


def test_gap_synthesis_accepts_release_label_aliases(stub_trend, stub_papers):
    trend = stub_trend
    trend.research_gaps = [
        "Deployment latency remains a major blocker",
        "Need stronger real-world evaluation",
    ]
    papers = [
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

    practical = synthesize_gap_candidates(trend, papers, limit=3, steering="Practical-first")
    breakthrough = synthesize_gap_candidates(trend, papers, limit=3, steering="Breakthrough-heavy")

    assert practical
    assert breakthrough
    assert practical[0]["gap_type"] in {"implementation_bottleneck", "recurring_limitation", "missing_evaluation"}
