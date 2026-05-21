import textwrap
import re
import json
from typing import List, Set, Optional

from src.core.models import TrendAnalysis, ProjectIdea
from src.core.llm import LLMClient
from src.core.config import Config


class IdeaGenerator:
    """Generates specific, actionable research project ideas from trend analysis."""
    
    DIFFICULTY_LEVELS = {
        "Undergraduate": {
            "cost": "Free Tier (Colab/Laptop)",
            "note": "Runs on Google Colab free tier or a personal laptop. No paid compute needed.",
            "timeline": "1 semester (4-5 months)"
        },
        "Master's": {
            "cost": "Cloud GPU ($50-200)",
            "note": "Needs cloud GPU access (A100/L4) for a few days of training. ~$50-200 total.",
            "timeline": "6-12 months"
        },
        "PhD": {
            "cost": "Institutional Resources",
            "note": "Requires multi-GPU cluster, large datasets, or specialized lab equipment.",
            "timeline": "1-3 years"
        }
    }

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def generate(self, trend: TrendAnalysis, existing_titles: Set[str], n: int,
                 research_context: str = '', language: str = 'en', approach: str = 'any') -> List[ProjectIdea]:
        category = trend.category
        ref_papers = trend.ref_papers
        
        # Build numbered paper list (use ALL available ref_papers, not just 5)
        available_papers = ref_papers[:15]  # Up to 15 papers for context
        paper_ctx = "\n".join(
            f"  [P{i+1}] \"{p.title}\"\n       ID: {p.id}\n       Abstract: {p.abstract[:180]}"
            for i, p in enumerate(available_papers)
        )
        paper_count = len(available_papers)
        
        methods_ctx = ""
        if trend.methodology_patterns:
            methods_ctx = f"\nCommon methodologies in this area:\n" + "\n".join(f"  - {m}" for m in trend.methodology_patterns)
        
        gaps_ctx = "\n".join(f"  - {g}" for g in trend.research_gaps) if trend.research_gaps else "  (infer from the papers above)"
        
        avoid_str = "\n".join(f"  - {t}" for t in list(existing_titles)[-10:]) or "  None"

        context_section = ""
        if research_context:
            context_section = f"""
Student context: {research_context}
Tailor ideas to match this student's background, available resources, and interests.
"""

        language_section = ""
        if language == "id":
            language_section = """
Write ALL fields including idea_title, abstract, why_hard, methodology_hint, and next_steps in formal academic Bahasa Indonesia.
The idea_title MUST also be in Bahasa Indonesia. Use proper scientific terminology. Do not mix English and Indonesian in the same sentence.
"""

        # Research approach constraint
        approach_section = ""
        if approach == "computational":
            approach_section = """
IMPORTANT CONSTRAINT: Generate ONLY computational/AI-based research ideas.
Ideas must involve: machine learning, deep learning, data analysis, simulation, or computational modeling.
All ideas must be implementable primarily through code and computation.
"""
        elif approach == "experimental":
            approach_section = """
IMPORTANT CONSTRAINT: Generate ONLY experimental/laboratory research ideas.
Ideas must involve: wet lab experiments, hardware prototyping, physical measurements, material synthesis, or bench-top research.
Do NOT suggest purely computational or AI/ML-based projects. The core contribution must come from physical experimentation.
"""
        elif approach == "clinical":
            approach_section = """
IMPORTANT CONSTRAINT: Generate ONLY clinical/field study research ideas.
Ideas must involve: patient studies, clinical trials, observational cohorts, surveys, epidemiological analysis, or intervention studies.
Do NOT suggest purely computational projects. The core contribution must come from real-world data collection with human subjects.
"""
        elif approach == "theoretical":
            approach_section = """
IMPORTANT CONSTRAINT: Generate ONLY theoretical/review research ideas.
Ideas must involve: systematic reviews, meta-analyses, theoretical frameworks, mathematical proofs, or conceptual models.
The core contribution should be synthesis of existing knowledge or new theoretical insights, not new experiments or code.
"""

        prompt = textwrap.dedent(f"""
You are a research advisor. Generate project ideas STRICTLY grounded in the papers below.
You must NOT invent, hallucinate, or reference any paper, dataset, or method that is not mentioned in the provided list.

Category: {category}
Trending keywords: {', '.join(trend.top_keywords)}
Identified research gaps:
{gaps_ctx}
{methods_ctx}

=== AVAILABLE PAPERS (P1 to P{paper_count}) ===
{paper_ctx}
=== END OF PAPERS ===

Already generated (DO NOT duplicate):
{avoid_str}
{context_section}{language_section}{approach_section}
Generate exactly {n} research project ideas as a JSON array. Each object MUST have:

- "idea_title": Specific, descriptive (8-18 words). NOT generic.

- "difficulty": "Undergraduate" | "Master's" | "PhD"

- "abstract": 3-4 sentences. Problem, approach, expected outcome. Be concrete.

- "why_hard": 2 sentences. The specific technical challenge.

- "methodology_hint": 2-3 sentences. HOW to approach this technically.

- "next_steps": Exactly 3 items as an array. First 3 actions to start.

- "key_paper_ids": Array of 2-3 paper IDs from the list above (e.g., ["P1", "P3", "P7"]).
  CRITICAL: You may ONLY reference papers from the list above (P1 to P{paper_count}).
  Do NOT invent paper titles. Do NOT reference papers not in the list.

- "resources_needed": comma-separated list.

- "inspired_by_ids": Array of paper IDs from above (e.g., ["P1", "P5"]).

ANTI-HALLUCINATION RULES:
1. Every paper reference MUST use the P-number from the list above.
2. Do NOT invent paper titles, author names, or URLs.
3. Do NOT reference datasets you are not certain exist.
4. If you are unsure about something, leave it out rather than fabricate.
5. Ideas must be directly derivable from the papers provided — not from your general knowledge.

Respond ONLY with a valid JSON array. No markdown, no explanation.
""").strip()

        response = self.llm.call(prompt, task_type="idea_generation")
        results: List[ProjectIdea] = []
        
        if response:
            cleaned = re.sub(r"```(?:json)?|```", "", response).strip()
            try:
                ideas_raw = json.loads(cleaned)
                if isinstance(ideas_raw, dict): 
                    ideas_raw = [ideas_raw]
                    
                for idea in ideas_raw[:n]:
                    title = idea.get("idea_title", "").strip()
                    if not title or title in existing_titles: 
                        continue
                    
                    # Normalize difficulty
                    diff = idea.get("difficulty", "Master's")
                    if diff not in self.DIFFICULTY_LEVELS:
                        diff_lower = diff.lower()
                        if "under" in diff_lower or "sarjana" in diff_lower:
                            diff = "Undergraduate"
                        elif "phd" in diff_lower or "doktor" in diff_lower:
                            diff = "PhD"
                        else:
                            diff = "Master's"
                    
                    level_info = self.DIFFICULTY_LEVELS[diff]
                    
                    # Map key_paper_ids (P1, P2...) back to actual paper objects
                    key_paper_ids = idea.get("key_paper_ids", [])
                    key_paper_titles = []
                    insp = []
                    for pid in key_paper_ids:
                        try:
                            idx = int(pid.replace("P", "").replace("p", "")) - 1
                            if 0 <= idx < len(available_papers):
                                key_paper_titles.append(available_papers[idx].title[:80])
                                if available_papers[idx] not in insp:
                                    insp.append(available_papers[idx])
                        except (ValueError, IndexError):
                            pass
                    
                    # Also map inspired_by_ids
                    for pid in idea.get("inspired_by_ids", []):
                        try:
                            idx = int(str(pid).replace("P", "").replace("p", "")) - 1
                            if 0 <= idx < len(available_papers):
                                if available_papers[idx] not in insp:
                                    insp.append(available_papers[idx])
                        except (ValueError, IndexError):
                            pass
                    
                    if not insp:
                        insp = available_papers[:2]
                    
                    # Format next_steps
                    next_steps = idea.get("next_steps", "")
                    if isinstance(next_steps, list):
                        next_steps = " | ".join(next_steps[:3])
                    
                    # Format key_papers from mapped titles (grounded, not hallucinated)
                    key_papers = " | ".join(key_paper_titles[:3]) if key_paper_titles else ""
                        
                    obj = ProjectIdea(
                        idea_title=title,
                        field=category,
                        difficulty=diff,
                        cost_estimate=level_info["cost"],
                        cost_note=level_info["note"],
                        why_hard=idea.get("why_hard", ""),
                        resources_needed=idea.get("resources_needed", ""),
                        abstract=idea.get("abstract", ""),
                        methodology_hint=idea.get("methodology_hint", ""),
                        next_steps=next_steps,
                        key_papers=key_papers,
                        inspired_by="; ".join(p.id for p in insp),
                        inspiration_title="; ".join(p.title[:80] for p in insp),
                        inspiration_link="; ".join(p.link for p in insp),
                        generated_date=Config.TODAY_STR
                    )
                    results.append(obj)
                    existing_titles.add(title)
                    self.llm._emit("idea", idea=obj.to_dict(), msg=title[:60])
            except Exception as e:
                self.llm._emit("llm_error", msg=f"Idea parse failed {category}: {e}")

        # Fallback if LLM fails entirely
        if not results:
            for kw in trend.top_keywords[:n]:
                title = f"Benchmarking {kw.title()} Methods on {category.split('.')[-1].upper()} Tasks with Limited Supervision"
                if title in existing_titles: 
                    continue
                insp = ref_papers[:2]
                
                obj = ProjectIdea(
                    idea_title=title,
                    field=category,
                    difficulty="Master's",
                    cost_estimate="Cloud GPU ($50-200)",
                    cost_note=self.DIFFICULTY_LEVELS["Master's"]["note"],
                    why_hard="Requires careful experimental design and fair comparison across methods.",
                    resources_needed="Cloud GPU, benchmark datasets, HuggingFace Transformers",
                    abstract=f"Systematic comparison of recent {kw} approaches on standard benchmarks with limited labeled data.",
                    methodology_hint=f"Implement 3-4 recent {kw} methods, evaluate on same splits, report with confidence intervals.",
                    next_steps="Survey recent papers on this topic | Identify 2-3 standard benchmarks | Set up evaluation pipeline",
                    key_papers="; ".join(p.title[:60] for p in insp[:2]),
                    inspired_by="; ".join(p.id for p in insp),
                    inspiration_title="; ".join(p.title[:80] for p in insp),
                    inspiration_link="; ".join(p.link for p in insp),
                    generated_date=Config.TODAY_STR
                )
                results.append(obj)
                existing_titles.add(title)
                self.llm._emit("idea", idea=obj.to_dict(), msg=title[:60])
                
        return results
