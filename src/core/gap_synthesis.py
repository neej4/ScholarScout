"""Lightweight gap synthesis for v1.6.5 gap-first generation.

This module intentionally uses deterministic heuristics instead of embeddings so
the pipeline stays fast, cheap, and easy to validate in the v1.6.x line.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Iterable, List

from src.core.models import Paper, TrendAnalysis


_STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "into", "using",
    "their", "have", "has", "had", "are", "was", "were", "can", "will",
    "been", "being", "than", "then", "your", "into", "onto", "about",
    "under", "over", "within", "across", "between", "after", "before",
    "more", "less", "only", "also", "they", "them", "such", "these",
    "those", "method", "methods", "paper", "papers", "study", "studies",
}
_LIMITATION_PATTERNS = [
    ("implementation_bottleneck", re.compile(r"\b(latency|compute|memory|deployment|real[- ]world|production|scalab)", re.I)),
    ("missing_evaluation", re.compile(r"\b(benchmark|evaluation|robust|generaliz|long[- ]term|ablation|realistic setting)", re.I)),
    ("recurring_limitation", re.compile(r"\b(limit|challenge|fail|however|bottleneck|weakness|constraint)", re.I)),
]
_STEERING_ALIASES = {
    "balanced": "balanced",
    "breakthrough": "breakthrough",
    "breakthrough-heavy": "breakthrough",
    "practical": "practical",
    "practical-first": "practical",
}


def _tokenize(text: str) -> List[str]:
    words = re.findall(r"[a-z0-9][a-z0-9\-]{2,}", (text or "").lower())
    return [word for word in words if word not in _STOPWORDS]


def _paper_blob(paper: Paper) -> str:
    return f"{paper.title} {paper.abstract}"


def _normalize_steering(steering: str) -> str:
    key = str(steering or "balanced").strip().lower()
    return _STEERING_ALIASES.get(key, key)


def _match_papers(papers: Iterable[Paper], query: str, fallback_count: int = 4) -> List[Paper]:
    tokens = set(_tokenize(query))
    scored = []
    for paper in papers:
        blob_tokens = set(_tokenize(_paper_blob(paper)))
        overlap = len(tokens & blob_tokens)
        scored.append((overlap, paper.citations, paper))
    scored.sort(key=lambda item: (-item[0], -item[1], item[2].title))
    matched = [paper for overlap, _, paper in scored if overlap > 0][:fallback_count]
    if matched:
        return matched
    return [paper for _, _, paper in scored[:fallback_count]]


def synthesize_gap_candidates(trend: TrendAnalysis, papers: List[Paper], limit: int = 6, steering: str = "balanced") -> List[dict]:
    """Build deterministic gap candidates from analyzed papers and trend summary."""
    papers = papers[:20]
    candidates: List[dict] = []

    def add_candidate(title: str, summary: str, gap_type: str, supporting: List[Paper]) -> None:
        paper_ids = []
        seen = set()
        for paper in supporting:
            if paper.id in seen:
                continue
            seen.add(paper.id)
            paper_ids.append(paper.id)
        if not paper_ids:
            return
        strength = min(10, max(3, len(paper_ids) + (2 if gap_type in {"underexplored_combination", "conflicting_findings"} else 1)))
        candidates.append({
            "title": title,
            "summary": summary,
            "gap_type": gap_type,
            "paper_ids": paper_ids,
            "strength_score": strength,
        })

    for idx, gap in enumerate(trend.research_gaps[:3], start=1):
        matched = _match_papers(papers, gap)
        add_candidate(
            title=f"Gap {idx}: {gap[:72]}",
            summary=gap,
            gap_type="recurring_limitation",
            supporting=matched,
        )

    if trend.emerging_methods and trend.top_keywords:
        combo_summary = (
            f"Combine {trend.emerging_methods[0]} with the active theme around "
            f"{trend.top_keywords[0]} to explore an under-tested direction."
        )
        add_candidate(
            title="Underexplored combination",
            summary=combo_summary,
            gap_type="underexplored_combination",
            supporting=_match_papers(papers, combo_summary),
        )

    if trend.cross_pollination:
        summary = trend.cross_pollination[0]
        add_candidate(
            title="Cross-pollination opportunity",
            summary=summary,
            gap_type="underexplored_combination",
            supporting=_match_papers(papers, summary),
        )

    limitation_hits: Counter[str] = Counter()
    for paper in papers:
        blob = _paper_blob(paper)
        for gap_type, pattern in _LIMITATION_PATTERNS:
            if pattern.search(blob):
                limitation_hits[gap_type] += 1
    if limitation_hits:
        top_type, count = limitation_hits.most_common(1)[0]
        keyword = top_type.replace("_", " ")
        summary = (
            f"Multiple papers repeatedly surface a {keyword} problem, suggesting a shared bottleneck "
            f"rather than an isolated limitation."
        )
        supporting = []
        pattern = dict(_LIMITATION_PATTERNS)[top_type]
        for paper in papers:
            if pattern.search(_paper_blob(paper)):
                supporting.append(paper)
        add_candidate(
            title=f"Recurring {keyword}",
            summary=summary,
            gap_type=top_type,
            supporting=supporting[:6],
        )

    deduped: List[dict] = []
    seen_keys = set()
    for candidate in candidates:
        key = (candidate["gap_type"], candidate["summary"].lower()[:80])
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(candidate)

    steering = _normalize_steering(steering)
    steering_bonus = {
        "balanced": {},
        "breakthrough": {
            "underexplored_combination": 2,
            "conflicting_findings": 2,
            "missing_evaluation": 1,
        },
        "practical": {
            "implementation_bottleneck": 2,
            "recurring_limitation": 1,
            "missing_evaluation": 1,
        },
    }
    bonus_map = steering_bonus.get(steering, steering_bonus["balanced"])
    deduped.sort(
        key=lambda item: (
            -(item["strength_score"] + bonus_map.get(item["gap_type"], 0)),
            item["title"],
        )
    )
    return deduped[:limit]
