"""
Idea generation routes: /api/quick, /api/regenerate
"""
import os
import json
import re

from flask import Blueprint, jsonify, request

from src.core.config import Config
from src.core.llm import LLMClient
from src.core.analyzer import TrendAnalyzer
from src.core.personalization import build_personalization_brief
from src.core.generator import suggest_goal_style

ideas_bp = Blueprint("ideas", __name__)

_COST_MAP = {
    "Undergraduate": "Free Tier",
    "Master's":      "Cloud GPU ($50-200)",
    "PhD":           "Institutional",
    "Hackathon":     "Free (laptop + APIs)",
    "Side Project":  "Free-$20",
    "Industry":      "Company Budget",
}

_base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_data_dir = os.path.join(_base_dir, "data")
_cache_file = os.path.join(_data_dir, "papers_cache.json")


def _load_cache() -> dict:
    try:
        with open(_cache_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _format_idea(raw: dict, field: str, goal_style: str = "") -> dict:
    """Normalise a raw LLM idea dict into the standard idea schema."""
    diff = raw.get("difficulty", "Master's")
    next_steps = raw.get("next_steps", "")
    if isinstance(next_steps, list):
        next_steps = " | ".join(next_steps[:3])
    prereqs = raw.get("prerequisites", [])
    if isinstance(prereqs, list):
        prereqs = " | ".join(prereqs[:5])
    return {
        "idea_title":       raw.get("idea_title", ""),
        "field":            field,
        "difficulty":       diff,
        "cost_estimate":    _COST_MAP.get(diff, "Cloud GPU ($50-200)"),
        "cost_note":        "",
        "why_hard":         raw.get("why_hard", ""),
        "resources_needed": raw.get("resources_needed", ""),
        "abstract":         raw.get("abstract", ""),
        "methodology_hint": raw.get("methodology_hint", ""),
        "next_steps":       next_steps,
        "key_papers":       "",
        "why_this_idea":    raw.get("why_this_idea", ""),
        "quality_score":    raw.get("quality_score", 7),
        "prerequisites":    prereqs,
        "inspired_by":      "",
        "inspiration_title": "",
        "inspiration_link": "",
        "generated_date":   Config.TODAY_STR,
        "source_papers":    raw.get("source_papers", []),
        "evidence_claims":  raw.get("evidence_claims", []),
        "grounding_score":  raw.get("grounding_score", 0),
        "risk_flags":       raw.get("risk_flags", []),
        "critique_summary": raw.get("critique_summary", ""),
        "refinement_summary": raw.get("refinement_summary", ""),
        "novelty_claim":    raw.get("novelty_claim", ""),
        "feasibility_warning": raw.get("feasibility_warning", ""),
        "refined":          bool(raw.get("refined", False)),
        "fit_to_user_summary": raw.get("fit_to_user_summary", ""),
        "misalignment_flags": raw.get("misalignment_flags", []),
        "user_fit_score":   raw.get("user_fit_score", 0),
        "goal_style":       goal_style or raw.get("goal_style", ""),
    }


@ideas_bp.route("/api/quick", methods=["POST"])
def api_quick():
    """Quick mode: generate ideas from cache or LLM knowledge (no fetching)."""
    from src.core.generator import PRODUCT_GOALS, DEVELOP_GOALS

    body = request.get_json(silent=True) or {}
    categories = body.get("categories", ["cs.AI"])
    max_ideas  = min(int(body.get("max_ideas", 5)), 20)
    language   = body.get("language", "en")
    approach   = body.get("approach", "any")
    goal       = body.get("goal", "any")
    goal_style = body.get("goal_style", "") or suggest_goal_style(goal)
    context    = body.get("context", "")
    user_profile = body.get("user_profile", {})
    feedback_summary = body.get("feedback_summary", {})

    # Append uploaded file context if available
    from src.web.routes.upload import get_uploaded_context
    uploaded = get_uploaded_context()
    if uploaded:
        context = (context + "\n\n--- ATTACHED FILE ---\n" + uploaded) if context else uploaded

    # Load and filter cached papers
    cached_papers = _load_cache()
    relevant = sorted(
        [p for p in cached_papers.values() if p.get("category") in categories],
        key=lambda p: p.get("submitted", ""),
        reverse=True,
    )

    paper_context = ""
    from_cache = bool(relevant)
    # Calculate staleness: average _used_count of papers being used
    avg_usage = 0
    if relevant:
        usage_counts = [p.get("_used_count", 0) for p in relevant[:15]]
        avg_usage = sum(usage_counts) / len(usage_counts) if usage_counts else 0
    if relevant:
        top = relevant[:15]
        lines = "\n".join(
            f'[P{i+1}] "{p.get("title","")}"'
            f'\n    Abstract: {p.get("abstract","")[:150]}'
            for i, p in enumerate(top)
        )
        paper_context = f"\n=== REFERENCE PAPERS (from cache) ===\n{lines}\n=== END ===\n"

    # Detect product vs academic vs develop mode
    is_product = goal.upper() in PRODUCT_GOALS
    is_develop = goal.upper() in DEVELOP_GOALS
    cats_str = ", ".join(categories[:5])

    # Build approach hint
    approach_hints = {
        "computational": "Ideas must be computational/AI-based.",
        "experimental":  "Ideas must involve physical experiments, NOT computation.",
        "clinical":      "Ideas must involve clinical/field studies.",
        "theoretical":   "Ideas must be theoretical/review.",
    }
    approach_hint = approach_hints.get(approach, "")
    lang_hint = "Write in formal academic Bahasa Indonesia." if language == "id" else ""
    personalization_hint = build_personalization_brief(user_profile, feedback_summary)
    if personalization_hint:
        personalization_hint = f"\n{personalization_hint}\nPrefer ideas that fit this user profile over generic ambitious ideas.\n"
    goal_style_hint = (
        f"\nGoal style: {goal_style}.\n"
        if goal_style and goal.upper() != "SYNTHESIS" else ""
    )

    if is_develop:
        # ── DEVELOP MODE PROMPT ──
        if not context:
            context = "A software project (describe your project in the Context field for better results)"

        prompt = (
            f"You are a senior software architect. Generate exactly {max_ideas} improvement ideas for an EXISTING project.\n"
            f"CRITICAL: Every idea MUST be directly applicable to the project below. Do NOT suggest new standalone products.\n\n"
            f"=== THE USER'S PROJECT ===\n{context}\n=== END ===\n\n"
            f"Fields: {cats_str}\n{approach_hint}\n{lang_hint}\n"
            f"{paper_context}\n{goal_style_hint}{personalization_hint}\n"
            "Return a JSON array. Each object must have:\n"
            "- idea_title: feature/improvement name (specific to the project, 5-15 words)\n"
            "- difficulty: \"Hackathon\" | \"Side Project\" | \"Industry\"\n"
            "- abstract: \"Target: [who benefits]. [what problem this solves for the project]\"\n"
            "- why_hard: risk / what could go wrong (1-2 sentences)\n"
            "- methodology_hint: implementation steps (3-5 items, pipe-separated)\n"
            "- next_steps: array of 3 first actions\n"
            "- resources_needed: tech stack needed (comma-separated, prefer project's existing stack)\n"
            "- prerequisites: who benefits from this improvement\n"
            "- why_this_idea: effort estimate (hours/days/weeks)\n"
            "- fit_to_user_summary: 1 sentence on why this fits the user's profile\n"
            "- misalignment_flags: array of short warnings if it still mismatches the user\n"
            "- user_fit_score: 1-10 for user fit\n"
            "- quality_score: 1-10 (relevance to project + feasibility + impact)\n"
            f"{'Reference papers using P-numbers.' if paper_context else ''}\n"
            "Respond ONLY with valid JSON array. No markdown."
        )
    elif is_product:
        # ── PRODUCT MODE PROMPT ──
        goal_hints = {
            "HACKATHON":    "Must be demo-able in 4-12 hours. Use existing APIs/tools only.",
            "SIDE_PROJECT": "Must be completable in 1-4 weekends. Deployable on free hosting.",
            "AI_TOOL":      "Must use LLM/AI as core intelligence. Handle failures gracefully.",
            "INDUSTRY_RND": "Must show ROI. Production-ready architecture.",
        }
        goal_hint = goal_hints.get(goal.upper(), "")

        prompt = (
            f"You are a product strategist. Generate exactly {max_ideas} BUILDABLE product ideas for the fields: {cats_str}\n"
            f"{approach_hint}\n{goal_hint}\n{lang_hint}\n"
            f"{'Builder context: ' + context if context else ''}\n"
            f"{paper_context}\n{goal_style_hint}{personalization_hint}\n"
            "Each idea is a tool/app/service that solves a real problem.\n\n"
            "Return a JSON array. Each object must have:\n"
            "- idea_title: product name (catchy, 5-12 words)\n"
            "- difficulty: \"Hackathon\" | \"Side Project\" | \"Industry\"\n"
            "- abstract: \"Target: [who]. [problem solved in 2 sentences]\"\n"
            "- why_hard: moat / why hard to copy (2 sentences)\n"
            "- methodology_hint: MVP features (3-5 items, pipe-separated)\n"
            "- next_steps: array of 3 first actions to build\n"
            "- resources_needed: tech stack (comma-separated)\n"
            "- prerequisites: target user description\n"
            "- why_this_idea: revenue model (1 sentence)\n"
            "- fit_to_user_summary: 1 sentence on why this fits the user's profile\n"
            "- misalignment_flags: array of short warnings if it still mismatches the user\n"
            "- user_fit_score: 1-10 for user fit\n"
            "- quality_score: 1-10 (viability + differentiation)\n"
            f"{'Reference papers using P-numbers.' if paper_context else ''}\n"
            "Respond ONLY with valid JSON array. No markdown."
        )
    else:
        # ── ACADEMIC MODE PROMPT ──
        goal_hints = {
            "THESIS":       "Ideas must fill 40-100 pages. Include literature review angle.",
            "PUBLICATION":  "Ideas must have clear novelty claim and be publishable.",
            "GRANT_PROPOSAL": "Ideas must have clear milestones and budget justification.",
        }
        goal_hint = goal_hints.get(goal.upper(), "")

        prompt = (
            f"Generate exactly {max_ideas} research project ideas for the fields: {cats_str}\n"
            f"{approach_hint}\n{goal_hint}\n{lang_hint}\n"
            f"{'Student context: ' + context if context else ''}\n"
            f"{paper_context}\n{goal_style_hint}{personalization_hint}\n"
            "Return a JSON array. Each object must have: idea_title, difficulty "
            "(\"Undergraduate\" | \"Master's\" | \"PhD\"), abstract (3 sentences), "
            "why_hard, methodology_hint, next_steps (array of 3), resources_needed, "
            "prerequisites (array of 3-5 skills), why_this_idea, fit_to_user_summary, "
            "misalignment_flags (array), user_fit_score (1-10), quality_score (1-10).\n"
            f"{'Reference papers using P-numbers from the list above.' if paper_context else ''}\n"
            "Respond ONLY with valid JSON array. No markdown."
        )

    try:
        llm = LLMClient()
        response = llm.call(prompt, task_type="idea_generation")
        if not response:
            return jsonify({"error": "LLM returned empty response", "ideas": []}), 500

        cleaned = re.sub(r"```(?:json)?|```", "", response).strip()
        ideas_raw = json.loads(cleaned)
        if isinstance(ideas_raw, dict):
            ideas_raw = [ideas_raw]

        ideas = [
            _format_idea(idea, categories[0] if categories else "", goal_style=goal_style)
            for idea in ideas_raw[:max_ideas]
        ]
        # Local telemetry
        try:
            from src.core.health import record_usage
            record_usage("quick_mode", ideas=len(ideas), from_cache=from_cache, goal=goal)
        except Exception:
            pass
        return jsonify({"ideas": ideas, "from_cache": from_cache, "avg_usage": round(avg_usage, 1)})

    except Exception as e:
        return jsonify({"error": str(e), "ideas": []}), 500


@ideas_bp.route("/api/regenerate", methods=["POST"])
def api_regenerate():
    """Regenerate a single idea for a given field/approach."""
    body    = request.get_json(silent=True) or {}
    field   = body.get("field", "cs.AI")
    approach = body.get("approach", "any")
    language = body.get("language", "en")
    goal_style = body.get("goal_style", "") or "project"
    context  = body.get("context", "")
    user_profile = body.get("user_profile", {})
    feedback_summary = body.get("feedback_summary", {})
    exclude  = body.get("exclude_title", "")

    approach_hints = {
        "experimental": "The idea MUST involve physical experiments or lab work, NOT computation.",
        "clinical":     "The idea MUST involve clinical studies with human subjects.",
        "theoretical":  "The idea MUST be a theoretical contribution or systematic review.",
    }
    approach_hint = approach_hints.get(approach, "")
    lang_hint = "Write ALL fields in formal academic Bahasa Indonesia." if language == "id" else ""
    personalization_hint = build_personalization_brief(user_profile, feedback_summary)
    if personalization_hint:
        personalization_hint = f"\n{personalization_hint}\nPrefer fit-to-user over generic novelty.\n"
    goal_style_hint = f"\nGoal style: {goal_style}.\n" if goal_style else ""

    keywords = TrendAnalyzer.KEYWORD_SEEDS.get(field, ["research", "analysis"])[:5]

    prompt = (
        f"Generate exactly 1 novel research idea for the field: {field}\n"
        f"Keywords in this area: {', '.join(keywords)}\n"
        f"{approach_hint}\n{lang_hint}\n"
        f"{'Student context: ' + context if context else ''}\n"
        f"{goal_style_hint}"
        f"{personalization_hint}\n"
        f"Do NOT generate this title: {exclude}\n\n"
        "Return a JSON object with: idea_title, difficulty (Undergraduate|Master's|PhD), "
        "abstract (3 sentences), why_hard (2 sentences), methodology_hint (2 sentences), "
        "next_steps (array of 3 strings), resources_needed, prerequisites (array of 3-5 skills), "
        "why_this_idea (1 sentence), fit_to_user_summary, misalignment_flags (array), "
        "user_fit_score (1-10), quality_score (1-10).\n\n"
        "Respond ONLY with valid JSON. No markdown."
    )

    try:
        llm = LLMClient()
        response = llm.call(prompt, task_type="idea_generation")
        if not response:
            return jsonify({"error": "LLM returned empty response"}), 500

        cleaned = re.sub(r"```(?:json)?|```", "", response).strip()
        idea_data = json.loads(cleaned)
        return jsonify({"idea": _format_idea(idea_data, field, goal_style=goal_style)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
