from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_modes_doc_matches_shipped_modes():
    text = _read("docs/modes.md")

    assert "Three modes" not in text
    assert "# Four modes" in text
    for mode in ("Academic", "Product", "Develop", "Review"):
        assert f"## {mode}" in text


def test_readme_links_to_four_modes():
    text = _read("README.md")

    assert "#four-modes" in text
    assert "ScholarScout-v1.6.5" not in text


def test_architecture_mentions_current_review_pipeline():
    text = _read("docs/architecture.md")

    assert "gap_synthesis.py" in text
    assert "clusterer.py" in text
    assert "synthesizer.py" in text
    assert "Review mode" in text
    assert "3 modes" not in text
