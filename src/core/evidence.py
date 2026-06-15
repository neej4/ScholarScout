"""Evidence grounding helpers for generated project ideas.

These helpers keep the evidence layer deterministic and independent from LLM
calls so parser behavior is easy to test and old snapshots remain compatible.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence

from src.core.models import Paper


@dataclass
class ResolvedPaperRefs:
    valid_papers: List[Paper]
    valid_refs: List[str]
    invalid_refs: List[str]


def build_paper_ref_map(papers: Sequence[Paper]) -> Dict[str, Paper]:
    """Map prompt-local P-numbers to fetched papers."""
    return {f"P{i + 1}": paper for i, paper in enumerate(papers or [])}


def resolve_paper_refs(refs: Iterable[Any], papers: Sequence[Paper]) -> ResolvedPaperRefs:
    """Resolve P-number refs and preserve invalid references for audit flags."""
    ref_map = build_paper_ref_map(papers)
    valid_papers: List[Paper] = []
    valid_refs: List[str] = []
    invalid_refs: List[str] = []
    seen_valid = set()
    seen_invalid = set()

    for raw_ref in refs or []:
        ref = _normalize_ref(raw_ref)
        if not ref:
            raw_text = str(raw_ref).strip()
            if raw_text and raw_text not in seen_invalid:
                invalid_refs.append(raw_text)
                seen_invalid.add(raw_text)
            continue
        paper = ref_map.get(ref)
        if paper:
            if ref not in seen_valid:
                valid_papers.append(paper)
                valid_refs.append(ref)
                seen_valid.add(ref)
        elif ref not in seen_invalid:
            invalid_refs.append(str(raw_ref).strip())
            seen_invalid.add(ref)

    return ResolvedPaperRefs(valid_papers=valid_papers, valid_refs=valid_refs, invalid_refs=invalid_refs)


def build_evidence_pack(
    raw_idea: Dict[str, Any],
    papers: Sequence[Paper],
    fallback_papers: Optional[Sequence[Paper]] = None,
) -> Dict[str, Any]:
    """Build serializable evidence metadata for one LLM-generated idea."""
    raw_idea = raw_idea if isinstance(raw_idea, dict) else {}
    claims, invalid_claim_refs = _normalize_claims(raw_idea.get("evidence_claims"), papers)

    candidate_refs = []
    for key in ("source_paper_ids", "inspired_by_ids", "key_paper_ids"):
        values = raw_idea.get(key)
        if isinstance(values, list):
            candidate_refs.extend(values)

    resolved_candidates = resolve_paper_refs(candidate_refs, papers)
    source_papers = _dedupe_papers(
        [paper for claim in claims for paper in claim.pop("_papers", [])]
        + resolved_candidates.valid_papers
        + list(fallback_papers or [])
    )

    invalid_refs = _dedupe_strings(invalid_claim_refs + resolved_candidates.invalid_refs)
    score = _score_grounding(raw_idea, claims, source_papers)
    flags = _risk_flags(claims, source_papers, invalid_refs, score)

    return {
        "source_papers": [_paper_to_evidence_dict(paper) for paper in source_papers],
        "evidence_claims": claims,
        "grounding_score": score,
        "risk_flags": flags,
    }


def _normalize_claims(raw_claims: Any, papers: Sequence[Paper]) -> tuple[List[Dict[str, Any]], List[str]]:
    if not isinstance(raw_claims, list):
        return [], []

    claims = []
    invalid_refs: List[str] = []
    for raw_claim in raw_claims:
        if isinstance(raw_claim, dict):
            claim_text = str(raw_claim.get("claim") or raw_claim.get("text") or "").strip()
            paper_refs = raw_claim.get("paper_ids") or raw_claim.get("sources") or raw_claim.get("refs") or []
        else:
            claim_text = str(raw_claim).strip()
            paper_refs = []

        if isinstance(paper_refs, str):
            paper_refs = [paper_refs]
        if not isinstance(paper_refs, list):
            paper_refs = []

        resolved = resolve_paper_refs(paper_refs, papers)
        invalid_refs.extend(resolved.invalid_refs)
        normalized = {
            "claim": claim_text,
            "paper_ids": resolved.valid_refs,
        }
        if resolved.invalid_refs:
            normalized["invalid_paper_ids"] = resolved.invalid_refs
        normalized["_papers"] = resolved.valid_papers
        claims.append(normalized)

    return claims, invalid_refs


def _score_grounding(raw_idea: Dict[str, Any], claims: List[Dict[str, Any]], source_papers: List[Paper]) -> int:
    if not source_papers:
        return 0

    source_score = min(len(source_papers), 2) * 20
    if claims:
        evidenced_claims = sum(1 for claim in claims if claim.get("paper_ids"))
        claim_score = round((evidenced_claims / len(claims)) * 40)
    else:
        claim_score = 0

    idea_text = " ".join(
        str(raw_idea.get(key, ""))
        for key in ("idea_title", "abstract", "why_this_idea", "methodology_hint", "problem_solved")
    )
    evidence_text = " ".join(f"{paper.title} {paper.abstract}" for paper in source_papers)
    overlap_score = min(_token_overlap_count(idea_text, evidence_text) * 4, 20)

    return max(0, min(100, source_score + claim_score + overlap_score))


def _risk_flags(
    claims: List[Dict[str, Any]],
    source_papers: List[Paper],
    invalid_refs: List[str],
    score: int,
) -> List[str]:
    flags = []
    if invalid_refs:
        flags.append("llm_unverified_reference")
    if len(source_papers) < 2:
        flags.append("low_source_count")
    if not claims or not any(claim.get("paper_ids") for claim in claims):
        flags.append("missing_evidence_claims")
    if score < 60:
        flags.append("weak_grounding")
    if _all_sources_stale(source_papers):
        flags.append("stale_papers")
    return flags


def _paper_to_evidence_dict(paper: Paper) -> Dict[str, Any]:
    return {
        "id": paper.id,
        "title": paper.title,
        "authors": paper.authors,
        "source": paper.source,
        "link": paper.link,
        "submitted_date": paper.submitted_date,
        "citations": paper.citations,
    }


def _normalize_ref(raw_ref: Any) -> Optional[str]:
    text = str(raw_ref).strip()
    match = re.fullmatch(r"[Pp]\s*(\d+)", text)
    if not match:
        return None
    return f"P{int(match.group(1))}"


def _dedupe_papers(papers: Sequence[Paper]) -> List[Paper]:
    seen = set()
    result = []
    for paper in papers:
        if not paper or paper.id in seen:
            continue
        seen.add(paper.id)
        result.append(paper)
    return result


def _dedupe_strings(values: Sequence[str]) -> List[str]:
    seen = set()
    result = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _token_overlap_count(left: str, right: str) -> int:
    stopwords = {"the", "and", "for", "with", "that", "this", "from", "into", "using", "pada", "yang", "dan"}
    left_tokens = {t for t in re.findall(r"[a-zA-Z][a-zA-Z0-9-]{3,}", left.lower()) if t not in stopwords}
    right_tokens = {t for t in re.findall(r"[a-zA-Z][a-zA-Z0-9-]{3,}", right.lower()) if t not in stopwords}
    return len(left_tokens & right_tokens)


def _all_sources_stale(papers: Sequence[Paper]) -> bool:
    if not papers:
        return False
    current_year = datetime.utcnow().year
    years = []
    for paper in papers:
        match = re.search(r"(19|20)\d{2}", paper.submitted_date or "")
        if match:
            years.append(int(match.group(0)))
    return bool(years) and all((current_year - year) >= 6 for year in years)
