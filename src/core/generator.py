import textwrap
import re
import json
import os
from typing import List, Set, Optional

from src.core.models import TrendAnalysis, ProjectIdea
from src.core.llm import LLMClient
from src.core.config import Config


# Goals that trigger PRODUCT mode (output = buildable product, not research paper)
PRODUCT_GOALS = {"HACKATHON", "SIDE_PROJECT", "AI_TOOL", "INDUSTRY_RND"}
DEVELOP_GOALS = {"FEATURE", "INTEGRATION", "OPTIMIZATION", "EXTENSION", "PIVOT"}
ACADEMIC_GOALS = {"THESIS", "PUBLICATION", "GRANT_PROPOSAL", "UNDERGRADUATE",
                  "MASTERS", "PHD", "LAB_SCIENTIST", "CLINICAL_RESEARCHER", "DATA_SCIENTIST"}


class IdeaGenerator:
    """Generates specific, actionable ideas from trend analysis.
    
    Two modes:
    - ACADEMIC: research project ideas (methodology, thesis outline, key papers)
    - PRODUCT: buildable product ideas (MVP features, tech stack, target user, revenue)
    """

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
        },
        "Hackathon": {
            "cost": "Free (laptop + APIs)",
            "note": "Must be demo-able in 4-12 hours. Use pre-trained models and free APIs only.",
            "timeline": "4-12 hours"
        },
        "Side Project": {
            "cost": "Free-$20",
            "note": "Completable in weekends. Deployable on free tier hosting.",
            "timeline": "1-4 weekends"
        },
        "Industry": {
            "cost": "Company Budget",
            "note": "Company-funded compute. Must show ROI to stakeholders.",
            "timeline": "1-6 months"
        },
    }

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def _is_product_mode(self, goal: str) -> bool:
        return goal.upper() in PRODUCT_GOALS

    def _is_develop_mode(self, goal: str) -> bool:
        return goal.upper() in DEVELOP_GOALS

    def _load_skill_constraints(self, goal: str) -> str:
        """Load skill file from DEVELOP/, PRODUCT/, or ACADEMIC/ subfolder."""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # Try new structure: skills/DEVELOP/FEATURE/SKILL.md, skills/PRODUCT/HACKATHON/SKILL.md, etc.
        for category_dir in ("DEVELOP", "PRODUCT", "ACADEMIC"):
            skill_path = os.path.join(base_dir, "skills", category_dir, goal, "SKILL.md")
            if os.path.exists(skill_path):
                break
        else:
            # Fallback: flat structure skills/HACKATHON/SKILL.md (backward compat)
            skill_path = os.path.join(base_dir, "skills", goal, "SKILL.md")

        try:
            with open(skill_path, "r", encoding="utf-8") as f:
                content = f.read()
            if len(content) > 2000:
                content = content[:2000] + "\n..."
            return f"\n--- SKILL PROFILE ({goal}) ---\n{content}\n--- END SKILL PROFILE ---\nGenerate ideas that fit within the constraints above.\n"
        except Exception:
            return ""

    # Max ideas per single LLM call to avoid truncated JSON
    CHUNK_SIZE = 3

    def generate(self, trend: TrendAnalysis, existing_titles: Set[str], n: int,
                 research_context: str = '', language: str = 'en',
                 approach: str = 'any', goal: str = 'any',
                 refine: bool = False) -> List[ProjectIdea]:
        """Route to academic, product, or develop generator based on goal.
        
        If n > CHUNK_SIZE, splits into multiple LLM calls to avoid truncated JSON.
        """
        # Pick the right sub-generator
        if self._is_develop_mode(goal):
            gen_fn = self._generate_develop
        elif self._is_product_mode(goal):
            gen_fn = self._generate_product
        else:
            gen_fn = self._generate_academic

        # Chunked generation: split into batches of CHUNK_SIZE
        ideas: List[ProjectIdea] = []
        remaining = n
        while remaining > 0 and len(ideas) < n:
            batch_size = min(remaining, self.CHUNK_SIZE)
            try:
                batch = gen_fn(trend, existing_titles, batch_size,
                               research_context, language, approach, goal)
                ideas.extend(batch)
            except Exception as e:
                self.llm._emit("llm_error", msg=f"Batch generation failed: {e}")
                # Continue with next batch — partial results better than nothing
            remaining = n - len(ideas)

        # Trim to exactly n
        ideas = ideas[:n]

        # Optional self-distillation refinement step
        if refine and ideas:
            ideas = self._refine_ideas(ideas, language)

        return ideas

    # ─── SELF-DISTILLATION REFINEMENT ─────────────────────────────────────────

    def _refine_ideas(self, ideas: List[ProjectIdea], language: str = 'en') -> List[ProjectIdea]:
        """
        Re-prompt LLM with generated ideas for self-distillation:
        remove redundancy, sharpen specificity, improve feasibility.
        Returns refined ideas (same count, same structure).
        """
        if not ideas:
            return ideas

        # Serialize ideas to JSON for the refinement prompt
        ideas_json = json.dumps([i.to_dict() for i in ideas], ensure_ascii=False, indent=1)

        lang_hint = "Respond in Bahasa Indonesia." if language == "id" else ""

        prompt = textwrap.dedent(f"""
You are a senior research advisor reviewing draft project ideas. Your job is to REFINE them — not generate new ones.

For each idea below:
1. Remove redundant or vague phrasing — make every sentence count
2. Sharpen the title to be more specific and memorable
3. Improve feasibility — if an idea is unrealistic, scope it down
4. Ensure next_steps are concrete first actions (not restatements of methodology)
5. If two ideas are too similar, differentiate them clearly

Return the SAME number of ideas in the SAME JSON array format. Keep all fields. Only improve the text content.
{lang_hint}

=== IDEAS TO REFINE ===
{ideas_json}
=== END ===

Respond ONLY with valid JSON array. No markdown, no explanation.
""").strip()

        response = self.llm.call(prompt, task_type="idea_generation")
        if not response:
            return ideas  # Refinement failed — return originals

        try:
            cleaned = re.sub(r"```(?:json)?|```", "", response).strip()
            refined_raw = json.loads(cleaned)
            if isinstance(refined_raw, dict):
                refined_raw = [refined_raw]
        except Exception:
            return ideas  # Parse failed — return originals

        # Map refined data back onto existing ProjectIdea objects (preserve metadata)
        for i, idea in enumerate(ideas):
            if i >= len(refined_raw):
                break
            r = refined_raw[i]
            # Only update text fields — preserve IDs, links, dates, scores
            if r.get("idea_title"):
                idea.idea_title = r["idea_title"]
            if r.get("abstract"):
                idea.abstract = r["abstract"]
            if r.get("why_hard"):
                idea.why_hard = r["why_hard"]
            if r.get("methodology_hint"):
                idea.methodology_hint = r["methodology_hint"]
            if r.get("next_steps"):
                ns = r["next_steps"]
                idea.next_steps = " | ".join(ns) if isinstance(ns, list) else ns
            if r.get("why_this_idea"):
                idea.why_this_idea = r["why_this_idea"]

        self.llm._emit("refine_done", msg=f"Refined {len(ideas)} ideas via self-distillation")
        return ideas

    # ─── DEVELOP MODE ───────────────────────────────────────────────────────────

    def _generate_develop(self, trend: TrendAnalysis, existing_titles: Set[str], n: int,
                          research_context: str, language: str, approach: str, goal: str) -> List[ProjectIdea]:
        """Generate feature/improvement ideas for an EXISTING project, grounded in papers."""
        category = trend.category
        available_papers = trend.ref_papers[:15]
        paper_ctx = "\n".join(
            f"  [P{i+1}] \"{p.title}\"\n       Abstract: {p.abstract[:200]}"
            for i, p in enumerate(available_papers)
        )
        paper_count = len(available_papers)

        goal_section = self._load_skill_constraints(goal)
        avoid_str = "\n".join(f"  - {t}" for t in list(existing_titles)[-10:]) or "  None"

        if not research_context:
            research_context = "A software project (no further details provided)"

        language_section = ""
        if language == "id":
            language_section = "\nWrite ALL fields in Bahasa Indonesia.\n"

        prompt = textwrap.dedent(f"""
You are a senior software architect who reads research papers to find techniques that can improve EXISTING projects.

CRITICAL: The user has an existing project. Every idea you generate MUST be a feature, improvement, or extension for THEIR project. Do NOT suggest building a new standalone product. Do NOT suggest ideas unrelated to the project described below.

=== THE USER'S PROJECT ===
{research_context}
=== END PROJECT DESCRIPTION ===

Category: {category}
Trending techniques in this area: {', '.join(trend.top_keywords)}

=== RECENT PAPERS (P1 to P{paper_count}) ===
{paper_ctx}
=== END OF PAPERS ===

Already suggested (DO NOT duplicate):
{avoid_str}
{language_section}{goal_section}
Generate exactly {n} development ideas as a JSON array. Each idea is a concrete improvement to the user's project, inspired by a technique from the papers above.

Each object MUST have:
- "idea_title": Feature/improvement name (specific to the project, 5-15 words)
- "target_user": Who benefits from this improvement (existing users, new segment, developers)
- "problem_solved": What pain point or limitation of the current project this addresses (2 sentences)
- "implementation_plan": Array of 3-5 concrete implementation steps
- "tech_stack": Array of 2-4 technologies/libraries needed (prefer what the project already uses)
- "effort_estimate": "hours" | "days" | "weeks" (realistic for a solo developer)
- "inspired_by_ids": Array of paper IDs (e.g., ["P1", "P3"]) — which paper technique enables this
- "risk": 1 sentence — what could go wrong or be harder than expected
- "difficulty": "Hackathon" | "Side Project" | "Industry"
- "quality_score": Integer 1-10 (relevance to the project + feasibility + impact)

RULES:
1. EVERY idea must be directly applicable to the project described above.
2. If the project description mentions specific tech (Python, Flask, etc.), use that stack.
3. Ideas must be ADDITIVE (don't suggest rewriting existing features).
4. Reference papers using P-numbers only.
5. If you cannot find relevant techniques for the project, say so — do NOT generate generic ideas.

Respond ONLY with valid JSON array. No markdown.
""").strip()

        response = self.llm.call(prompt, task_type="idea_generation")
        return self._parse_develop_response(response, available_papers, category, existing_titles, goal)

    def _parse_develop_response(self, response: Optional[str], available_papers: list,
                                 category: str, existing_titles: Set[str], goal: str) -> List[ProjectIdea]:
        """Parse LLM response for develop mode into ProjectIdea objects."""
        results: List[ProjectIdea] = []
        if not response:
            return results

        cleaned = re.sub(r"```(?:json)?|```", "", response).strip()
        try:
            ideas_raw = json.loads(cleaned)
            if isinstance(ideas_raw, dict):
                ideas_raw = [ideas_raw]
        except Exception as e:
            self.llm._emit("llm_error", msg=f"Develop idea parse failed {category}: {e}")
            return results

        for idea in ideas_raw:
            title = idea.get("idea_title", "").strip()
            if not title or title in existing_titles:
                continue

            try:
                quality_score = int(idea.get("quality_score", 7))
            except (ValueError, TypeError):
                quality_score = 7
            if quality_score < 5:
                continue

            # Map difficulty
            diff = idea.get("difficulty", "Side Project")
            if diff not in self.DIFFICULTY_LEVELS:
                diff = "Side Project"
            level_info = self.DIFFICULTY_LEVELS[diff]

            # Map inspired_by_ids
            insp = []
            for pid in idea.get("inspired_by_ids", []):
                try:
                    idx = int(str(pid).replace("P", "").replace("p", "")) - 1
                    if 0 <= idx < len(available_papers):
                        insp.append(available_papers[idx])
                except (ValueError, IndexError):
                    pass
            if not insp:
                insp = available_papers[:2]

            # Format arrays
            impl_plan = idea.get("implementation_plan", [])
            if isinstance(impl_plan, list):
                impl_plan = " | ".join(impl_plan[:5])
            tech = idea.get("tech_stack", [])
            if isinstance(tech, list):
                tech = ", ".join(tech[:6])

            # Build abstract
            problem = idea.get("problem_solved", "")
            target = idea.get("target_user", "")
            effort = idea.get("effort_estimate", "days")
            abstract = f"Target: {target}. {problem} (Effort: {effort})" if target else problem

            obj = ProjectIdea(
                idea_title=title,
                field=category,
                difficulty=diff,
                cost_estimate=level_info["cost"],
                cost_note=f"Effort: {effort}",
                why_hard=idea.get("risk", ""),
                resources_needed=tech,
                abstract=abstract,
                methodology_hint=impl_plan,  # repurpose: implementation plan
                next_steps=" | ".join(idea.get("implementation_plan", [])[:3]),
                key_papers="",
                why_this_idea=f"Effort: {effort}",
                quality_score=quality_score,
                prerequisites=target,
                inspired_by="; ".join(p.id for p in insp),
                inspiration_title="; ".join(p.title[:80] for p in insp),
                inspiration_link="; ".join(p.link for p in insp),
                generated_date=Config.TODAY_STR,
            )
            results.append(obj)
            existing_titles.add(title)
            self.llm._emit("idea", idea=obj.to_dict(), msg=title[:60])

        return results

    # ─── PRODUCT MODE ─────────────────────────────────────────────────────────

    def _generate_product(self, trend: TrendAnalysis, existing_titles: Set[str], n: int,
                          research_context: str, language: str, approach: str, goal: str) -> List[ProjectIdea]:
        """Generate buildable product ideas grounded in recent papers."""
        category = trend.category
        available_papers = trend.ref_papers[:15]
        paper_ctx = "\n".join(
            f"  [P{i+1}] \"{p.title}\"\n       Abstract: {p.abstract[:200]}"
            for i, p in enumerate(available_papers)
        )
        paper_count = len(available_papers)

        goal_section = self._load_skill_constraints(goal)
        avoid_str = "\n".join(f"  - {t}" for t in list(existing_titles)[-10:]) or "  None"

        context_section = ""
        if research_context:
            context_section = f"\nBuilder context: {research_context}\nTailor ideas to match this person's skills, available tools, and interests.\n"

        language_section = ""
        if language == "id":
            language_section = "\nWrite ALL fields in Bahasa Indonesia. Product names can stay in English.\n"

        prompt = textwrap.dedent(f"""
You are a product strategist who reads research papers to find buildable product opportunities.
Your job: identify problems that papers solve theoretically but NO existing tool/product addresses yet.

Category: {category}
Trending keywords: {', '.join(trend.top_keywords)}
Research gaps (= unmet needs):
{chr(10).join(f'  - {g}' for g in trend.research_gaps) if trend.research_gaps else '  (infer from papers)'}

=== RECENT PAPERS (P1 to P{paper_count}) ===
{paper_ctx}
=== END OF PAPERS ===

Already generated (DO NOT duplicate):
{avoid_str}
{context_section}{language_section}{goal_section}
Generate exactly {n} PRODUCT ideas as a JSON array. Each idea is a buildable tool/app/service inspired by the papers above.

Each object MUST have:
- "idea_title": Product name or one-line description (catchy, specific, 5-12 words)
- "target_user": Who would use this? Be specific (e.g., "ML engineers at startups with <10 people")
- "problem_solved": 2 sentences. What pain point does this solve? Why do people need this NOW?
- "mvp_features": Array of 3-5 core features for the minimum viable product
- "tech_stack": Array of 3-6 technologies/frameworks/APIs needed to build this
- "revenue_model": How does this make money? (freemium, API pricing, subscription, open-core, etc.)
- "competitors": Array of 1-3 existing tools that partially solve this + what they're missing
- "moat": 1-2 sentences. Why is this hard to copy? What's the unfair advantage?
- "next_steps": Array of 3 concrete first actions to start building
- "inspired_by_ids": Array of paper IDs (e.g., ["P1", "P3"])
- "difficulty": "Hackathon" | "Side Project" | "Industry"
- "quality_score": Integer 1-10. Is this viable, specific, and differentiated?

RULES:
1. Every idea must be GROUNDED in a technique/finding from the papers above.
2. Do NOT suggest generic ideas ("build a chatbot"). Be specific about WHAT technique from WHICH paper.
3. Ideas must be BUILDABLE with current technology (not research proposals).
4. Reference papers using P-numbers only.

Respond ONLY with valid JSON array. No markdown.
""").strip()

        response = self.llm.call(prompt, task_type="idea_generation")
        return self._parse_product_response(response, available_papers, category, existing_titles, goal)

    def _parse_product_response(self, response: Optional[str], available_papers: list,
                                 category: str, existing_titles: Set[str], goal: str) -> List[ProjectIdea]:
        """Parse LLM response for product mode into ProjectIdea objects."""
        results: List[ProjectIdea] = []
        if not response:
            return results

        cleaned = re.sub(r"```(?:json)?|```", "", response).strip()
        try:
            ideas_raw = json.loads(cleaned)
            if isinstance(ideas_raw, dict):
                ideas_raw = [ideas_raw]
        except Exception as e:
            self.llm._emit("llm_error", msg=f"Product idea parse failed {category}: {e}")
            return results

        for idea in ideas_raw:
            title = idea.get("idea_title", "").strip()
            if not title or title in existing_titles:
                continue

            # Quality filter
            try:
                quality_score = int(idea.get("quality_score", 7))
            except (ValueError, TypeError):
                quality_score = 7
            if quality_score < 5:
                continue

            # Map difficulty
            diff = idea.get("difficulty", "Side Project")
            if diff not in self.DIFFICULTY_LEVELS:
                diff = "Side Project"
            level_info = self.DIFFICULTY_LEVELS[diff]

            # Map inspired_by_ids to paper objects
            insp = []
            for pid in idea.get("inspired_by_ids", []):
                try:
                    idx = int(str(pid).replace("P", "").replace("p", "")) - 1
                    if 0 <= idx < len(available_papers):
                        insp.append(available_papers[idx])
                except (ValueError, IndexError):
                    pass
            if not insp:
                insp = available_papers[:2]

            # Format arrays to pipe-separated strings
            mvp = idea.get("mvp_features", [])
            if isinstance(mvp, list):
                mvp = " | ".join(mvp[:5])
            tech = idea.get("tech_stack", [])
            if isinstance(tech, list):
                tech = ", ".join(tech[:6])
            competitors = idea.get("competitors", [])
            if isinstance(competitors, list):
                competitors = " | ".join(competitors[:3])
            next_steps = idea.get("next_steps", [])
            if isinstance(next_steps, list):
                next_steps = " | ".join(next_steps[:3])

            # Build abstract from product fields
            problem = idea.get("problem_solved", "")
            target = idea.get("target_user", "")
            abstract = f"Target: {target}. {problem}" if target else problem

            obj = ProjectIdea(
                idea_title=title,
                field=category,
                difficulty=diff,
                cost_estimate=level_info["cost"],
                cost_note=level_info["note"],
                why_hard=idea.get("moat", ""),
                resources_needed=tech,
                abstract=abstract,
                methodology_hint=mvp,  # repurpose: MVP features
                next_steps=next_steps,
                key_papers=competitors,  # repurpose: competitors
                why_this_idea=idea.get("revenue_model", ""),  # repurpose: revenue
                quality_score=quality_score,
                prerequisites=idea.get("target_user", ""),  # repurpose: target user
                inspired_by="; ".join(p.id for p in insp),
                inspiration_title="; ".join(p.title[:80] for p in insp),
                inspiration_link="; ".join(p.link for p in insp),
                generated_date=Config.TODAY_STR,
            )
            results.append(obj)
            existing_titles.add(title)
            self.llm._emit("idea", idea=obj.to_dict(), msg=title[:60])

        return results

    # ─── ACADEMIC MODE (original) ─────────────────────────────────────────────

    def _generate_academic(self, trend: TrendAnalysis, existing_titles: Set[str], n: int,
                           research_context: str, language: str, approach: str, goal: str) -> List[ProjectIdea]:
        """Generate research project ideas (original behavior)."""
        category = trend.category
        ref_papers = trend.ref_papers

        available_papers = ref_papers[:15]
        paper_ctx = "\n".join(
            f"  [P{i+1}] \"{p.title}\"\n       ID: {p.id}\n       Abstract: {p.abstract[:180]}"
            for i, p in enumerate(available_papers)
        )
        paper_count = len(available_papers)

        goal_section = ""
        if goal and goal != "any":
            goal_section = self._load_skill_constraints(goal)

        methods_ctx = ""
        if trend.methodology_patterns:
            methods_ctx = f"\nCommon methodologies in this area:\n" + "\n".join(f"  - {m}" for m in trend.methodology_patterns)

        gaps_ctx = "\n".join(f"  - {g}" for g in trend.research_gaps) if trend.research_gaps else "  (infer from the papers above)"

        cross_ctx = ""
        if trend.cross_pollination:
            cross_ctx = f"\nCross-pollination opportunities (combine gap + external technique):\n" + "\n".join(f"  - {c}" for c in trend.cross_pollination)

        saturation_ctx = ""
        if trend.saturation_level:
            saturation_ctx = f"\nField saturation: {trend.saturation_level} (if saturated, ideas must be highly specific and differentiated)"

        avoid_str = "\n".join(f"  - {t}" for t in list(existing_titles)[-10:]) or "  None"

        context_section = ""
        if research_context:
            context_section = f"\nStudent context: {research_context}\nTailor ideas to match this student's background, available resources, and interests.\n"

        language_section = ""
        if language == "id":
            language_section = "\nWrite ALL fields including idea_title, abstract, why_hard, methodology_hint, and next_steps in formal academic Bahasa Indonesia.\nThe idea_title MUST also be in Bahasa Indonesia. Use proper scientific terminology.\n"

        approach_section = ""
        approach_map = {
            "computational": "Generate ONLY computational/AI-based research ideas. Ideas must involve: machine learning, deep learning, data analysis, simulation, or computational modeling.",
            "experimental": "Generate ONLY experimental/laboratory research ideas. Ideas must involve: wet lab experiments, hardware prototyping, physical measurements. Do NOT suggest purely computational projects.",
            "clinical": "Generate ONLY clinical/field study research ideas. Ideas must involve: patient studies, clinical trials, observational cohorts, surveys.",
            "theoretical": "Generate ONLY theoretical/review research ideas. Ideas must involve: systematic reviews, meta-analyses, theoretical frameworks, mathematical proofs.",
        }
        if approach in approach_map:
            approach_section = f"\nIMPORTANT CONSTRAINT: {approach_map[approach]}\n"

        prompt = textwrap.dedent(f"""
You are a research advisor. Generate project ideas STRICTLY grounded in the papers below.
You must NOT invent, hallucinate, or reference any paper, dataset, or method that is not mentioned in the provided list.

Category: {category}
Trending keywords: {', '.join(trend.top_keywords)}
Identified research gaps:
{gaps_ctx}
{methods_ctx}{cross_ctx}{saturation_ctx}

=== AVAILABLE PAPERS (P1 to P{paper_count}) ===
{paper_ctx}
=== END OF PAPERS ===

Already generated (DO NOT duplicate):
{avoid_str}
{context_section}{language_section}{approach_section}{goal_section}
Generate exactly {n} research project ideas as a JSON array. Each object MUST have:

- "idea_title": Specific, descriptive (8-18 words). NOT generic.
- "difficulty": "Undergraduate" | "Master's" | "PhD" | "Hackathon" | "Side Project" | "Industry"
- "abstract": 3-4 sentences. Problem, approach, expected outcome. Be concrete.
- "why_hard": 2 sentences. The specific technical challenge.
- "methodology_hint": 2-3 sentences. HOW to approach this technically.
- "next_steps": Exactly 3 items as an array. First 3 actions to start.
- "key_paper_ids": Array of 2-3 paper IDs from the list above (e.g., ["P1", "P3", "P7"]).
  CRITICAL: You may ONLY reference papers from the list above (P1 to P{paper_count}).
- "resources_needed": comma-separated list.
- "prerequisites": Array of 3-5 skills/knowledge needed.
- "inspired_by_ids": Array of paper IDs from above.
- "why_this_idea": 1-2 sentences explaining which research gap this fills and why NOW.
- "quality_score": Integer 1-10.

ANTI-HALLUCINATION RULES:
1. Every paper reference MUST use the P-number from the list above.
2. Do NOT invent paper titles, author names, or URLs.
3. Do NOT reference datasets you are not certain exist.
4. If you are unsure about something, leave it out rather than fabricate.
5. Ideas must be directly derivable from the papers provided.

Respond ONLY with a valid JSON array. No markdown, no explanation.
""").strip()

        response = self.llm.call(prompt, task_type="idea_generation")
        return self._parse_academic_response(response, available_papers, category, existing_titles, trend)

    def _parse_academic_response(self, response: Optional[str], available_papers: list,
                                  category: str, existing_titles: Set[str], trend: TrendAnalysis) -> List[ProjectIdea]:
        """Parse LLM response for academic mode into ProjectIdea objects."""
        results: List[ProjectIdea] = []
        if not response:
            return self._academic_fallback(trend, existing_titles)

        cleaned = re.sub(r"```(?:json)?|```", "", response).strip()
        try:
            ideas_raw = json.loads(cleaned)
            if isinstance(ideas_raw, dict):
                ideas_raw = [ideas_raw]
        except Exception as e:
            self.llm._emit("llm_error", msg=f"Idea parse failed {category}: {e}")
            return self._academic_fallback(trend, existing_titles)

        for idea in ideas_raw:
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
                elif "hack" in diff_lower:
                    diff = "Hackathon"
                elif "side" in diff_lower or "weekend" in diff_lower:
                    diff = "Side Project"
                elif "industry" in diff_lower or "company" in diff_lower:
                    diff = "Industry"
                else:
                    diff = "Master's"

            level_info = self.DIFFICULTY_LEVELS[diff]

            # Map key_paper_ids back to paper objects
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

            next_steps = idea.get("next_steps", "")
            if isinstance(next_steps, list):
                next_steps = " | ".join(next_steps[:3])

            key_papers = " | ".join(key_paper_titles[:3]) if key_paper_titles else ""

            try:
                quality_score = int(idea.get("quality_score", 7))
            except (ValueError, TypeError):
                quality_score = 7
            if quality_score < 5:
                continue

            prereqs = idea.get("prerequisites", [])
            if isinstance(prereqs, list):
                prereqs = " | ".join(prereqs[:5])

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
                why_this_idea=idea.get("why_this_idea", ""),
                quality_score=quality_score,
                prerequisites=prereqs,
                inspired_by="; ".join(p.id for p in insp),
                inspiration_title="; ".join(p.title[:80] for p in insp),
                inspiration_link="; ".join(p.link for p in insp),
                generated_date=Config.TODAY_STR,
            )
            results.append(obj)
            existing_titles.add(title)
            self.llm._emit("idea", idea=obj.to_dict(), msg=title[:60])

        if not results:
            return self._academic_fallback(trend, existing_titles)
        return results

    def _academic_fallback(self, trend: TrendAnalysis, existing_titles: Set[str]) -> List[ProjectIdea]:
        """Fallback ideas when LLM fails entirely."""
        results = []
        ref_papers = trend.ref_papers
        for kw in trend.top_keywords[:3]:
            title = f"Benchmarking {kw.title()} Methods on {trend.category.split('.')[-1].upper()} Tasks with Limited Supervision"
            if title in existing_titles:
                continue
            insp = ref_papers[:2]
            obj = ProjectIdea(
                idea_title=title,
                field=trend.category,
                difficulty="Master's",
                cost_estimate="Cloud GPU ($50-200)",
                cost_note=self.DIFFICULTY_LEVELS["Master's"]["note"],
                why_hard="Requires careful experimental design and fair comparison across methods.",
                resources_needed="Cloud GPU, benchmark datasets, HuggingFace Transformers",
                abstract=f"Systematic comparison of recent {kw} approaches on standard benchmarks with limited labeled data.",
                methodology_hint=f"Implement 3-4 recent {kw} methods, evaluate on same splits, report with confidence intervals.",
                next_steps="Survey recent papers | Identify 2-3 benchmarks | Set up evaluation pipeline",
                key_papers="; ".join(p.title[:60] for p in insp[:2]),
                why_this_idea=f"No comprehensive benchmark exists for recent {kw} methods under limited supervision.",
                quality_score=6,
                prerequisites="Literature survey | Basic ML implementation | Experiment design",
                inspired_by="; ".join(p.id for p in insp),
                inspiration_title="; ".join(p.title[:80] for p in insp),
                inspiration_link="; ".join(p.link for p in insp),
                generated_date=Config.TODAY_STR,
            )
            results.append(obj)
            existing_titles.add(title)
            self.llm._emit("idea", idea=obj.to_dict(), msg=title[:60])
        return results
