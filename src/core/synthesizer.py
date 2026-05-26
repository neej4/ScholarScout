"""
Literature Synthesizer for Review Mode.
Takes clustered papers and produces:
1. Per-cluster synthesis (methodology, findings, gaps)
2. Cross-cutting analysis (timeline, debates, open questions, reading list)
"""
import json
from typing import List, Dict, Optional
from src.core.models import Paper
from src.core.llm import LLMClient


class LiteratureSynthesizer:
    """
    Synthesizes literature from clustered papers.
    Produces structured output for Review Mode.
    """

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def synthesize_cluster(self, cluster_name: str, papers: List[Paper]) -> Dict:
        """
        Synthesize a single cluster of papers.

        Returns:
            {
                "name": str,
                "paper_count": int,
                "methodology_summary": str,
                "key_findings": str,
                "gaps": str,
                "papers": List[dict]
            }
        """
        # Build paper list for prompt
        paper_list = "\n".join(
            f"P{i+1}: {p.title} ({p.source}, {p.submitted_date})\n    Abstract: {p.abstract[:200]}"
            for i, p in enumerate(papers[:12])
        )

        prompt = f"""You are a research synthesis expert. Analyze these papers from the cluster "{cluster_name}":

{paper_list}

Produce a JSON object with these exact keys:
- "methodology_summary": string (2-3 sentences describing the common methodologies used across these papers)
- "key_findings": string (2-3 sentences summarizing the main findings/contributions)
- "gaps": string (2-3 sentences identifying what these papers collectively leave unaddressed)

Be specific. Reference paper numbers (P1, P2, etc) where relevant.
Respond ONLY with valid JSON."""

        response = self.llm.call(prompt, retries=2, task_type="trend_analysis")
        if not response:
            return {
                "name": cluster_name,
                "paper_count": len(papers),
                "methodology_summary": "(Synthesis unavailable)",
                "key_findings": "(Synthesis unavailable)",
                "gaps": "(Synthesis unavailable)",
                "papers": [p.to_dict() for p in papers],
            }

        try:
            cleaned = response.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split('\n')
                if lines[0].startswith("```"): lines = lines[1:]
                if lines and lines[-1].strip() == "```": lines = lines[:-1]
                cleaned = '\n'.join(lines)
            data = json.loads(cleaned)
        except (json.JSONDecodeError, ValueError):
            data = {
                "methodology_summary": response[:300],
                "key_findings": "",
                "gaps": "",
            }

        return {
            "name": cluster_name,
            "paper_count": len(papers),
            "methodology_summary": data.get("methodology_summary", ""),
            "key_findings": data.get("key_findings", ""),
            "gaps": data.get("gaps", ""),
            "papers": [p.to_dict() for p in papers],
        }

    def cross_cutting_analysis(self, cluster_summaries: List[Dict], all_papers: List[Paper]) -> Dict:
        """
        Produce cross-cutting analysis across all clusters.

        Returns:
            {
                "timeline": str,
                "debates": str,
                "open_questions": List[str],
                "reading_list": List[dict]  (top 5-10 papers)
            }
        """
        # Build cluster summary for prompt
        cluster_text = "\n\n".join(
            f"Cluster: {c['name']} ({c['paper_count']} papers)\n"
            f"Methods: {c['methodology_summary']}\n"
            f"Findings: {c['key_findings']}\n"
            f"Gaps: {c['gaps']}"
            for c in cluster_summaries
        )

        prompt = f"""You are a senior research advisor producing a cross-cutting literature analysis.

Here are the cluster summaries from a literature review:

{cluster_text}

Produce a JSON object with these exact keys:
- "timeline": string (describe how this field evolved chronologically — foundational work → recent advances)
- "debates": string (identify 2-3 active disagreements or tensions between different approaches)
- "open_questions": array of 3-5 strings (specific unresolved questions that no paper has answered)
- "reading_list_rationale": string (explain the logic for selecting must-read papers)

Be specific and reference cluster names where relevant.
Respond ONLY with valid JSON."""

        response = self.llm.call(prompt, retries=2, task_type="deep_dive")
        if not response:
            return {
                "timeline": "(Analysis unavailable)",
                "debates": "(Analysis unavailable)",
                "open_questions": [],
                "reading_list": [],
            }

        try:
            cleaned = response.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split('\n')
                if lines[0].startswith("```"): lines = lines[1:]
                if lines and lines[-1].strip() == "```": lines = lines[:-1]
                cleaned = '\n'.join(lines)
            data = json.loads(cleaned)
        except (json.JSONDecodeError, ValueError):
            data = {"timeline": response[:300], "debates": "", "open_questions": [], "reading_list_rationale": ""}

        # Build reading list: top papers by citation count
        sorted_papers = sorted(all_papers, key=lambda p: p.citations, reverse=True)
        reading_list = [p.to_dict() for p in sorted_papers[:8]]

        return {
            "timeline": data.get("timeline", ""),
            "debates": data.get("debates", ""),
            "open_questions": data.get("open_questions", []),
            "reading_list": reading_list,
        }
