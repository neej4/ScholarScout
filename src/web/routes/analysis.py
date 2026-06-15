"""
Analysis routes: /api/deepdive, /api/novelty, /api/implementations, /api/refine
"""
import json
import re

from flask import Blueprint, jsonify, request

from src.core.analysis_utils import normalize_refine_messages, sanitize_roadmap_graph
from src.core.llm import LLMClient
from src.core.deep_dive import DeepDiveHandler
from src.core.novelty_checker import NoveltyChecker
from src.core.impl_finder import ImplementationFinder

analysis_bp = Blueprint("analysis", __name__)


@analysis_bp.route("/api/deepdive", methods=["POST"])
def api_deepdive():
    """
    Deep Dive analysis for a research idea.

    Request body: full idea object (idea_title required).
        Optional: verify_grounding (bool) — if true, compare each section
        against the inspiration paper abstract using semantic similarity.
    Returns: outline, methodology, datasets, references, timeline, tools.
        If verify_grounding requested: also returns "grounding" dict mapping
        section name to {score, level}.
    """
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "Request body must be JSON"}), 400
    if not body.get("idea_title"):
        return jsonify({"error": "Field 'idea_title' is required"}), 400

    language = body.get("language", "en")
    want_grounding = bool(body.get("verify_grounding", False))

    try:
        llm_client = LLMClient()
        handler = DeepDiveHandler(llm_client)
        result = handler.generate(body, language)

        # Optional: verify grounding against the inspiration paper abstract
        if want_grounding:
            # Source text priority: explicit source_text > idea abstract > inspiration_title
            source_text = (
                body.get("source_text")
                or body.get("abstract", "")
                or body.get("inspiration_title", "")
            )
            if source_text:
                try:
                    result["grounding"] = handler.verify_grounding(result, source_text)
                except Exception:
                    # Grounding is best-effort — never fail the whole request
                    result["grounding"] = {}

        # Local telemetry
        try:
            from src.core.health import record_usage
            record_usage("deepdive", field=body.get("field", ""))
        except Exception:
            pass
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"Internal server error: {e}"}), 500


@analysis_bp.route("/api/novelty", methods=["POST"])
def api_novelty():
    """
    Check novelty of a research idea title.

    Request body: {"idea_title": "string"}
    Returns: {"status": "novel"|"similar"|"exists", "papers": [...], "method": "semantic"|"jaccard"}
    """
    body = request.get_json(silent=True)
    if not body or not body.get("idea_title"):
        return jsonify({"error": "idea_title is required"}), 400

    idea_title = body["idea_title"].strip()
    if not idea_title:
        return jsonify({"error": "idea_title cannot be empty"}), 400

    try:
        checker = NoveltyChecker()
        result = checker.check(idea_title)
        return jsonify({
            "status":  result["status"],
            "papers":  result["papers"],
            "method":  result.get("method", "jaccard"),
        })
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {e}"}), 500


@analysis_bp.route("/api/implementations", methods=["POST"])
def api_implementations():
    """
    Find code implementations related to a research idea.

    Request body: idea object (idea_title required).
        Also uses: field, inspiration_title, methodology_hint, abstract.
    Returns: {paper_repos: [...], related_repos: [...], awesome_lists: [...], meta: {...}}
    """
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "Request body must be JSON"}), 400
    if not body.get("idea_title"):
        return jsonify({"error": "Field 'idea_title' is required"}), 400

    try:
        finder = ImplementationFinder()
        results = finder.find(body)
        # Local telemetry
        try:
            from src.core.health import record_usage
            record_usage("impl_search", field=body.get("field", ""),
                         sources=len(results.get("meta", {}).get("sources_queried", [])))
        except Exception:
            pass
        return jsonify(results), 200
    except Exception as e:
        return jsonify({"error": f"Implementation search failed: {e}"}), 500


@analysis_bp.route("/api/refine", methods=["POST"])
def api_refine():
    """
    Idea Refinement Chat — multi-turn conversation to refine a research idea.

    Request body:
        idea: full idea object (provides context)
        messages: list of {role: "user"|"assistant", content: str}
        language: "en" | "id" (optional, default "en")

    Returns: {reply: str}

    The system prompt includes the full idea context so the LLM can give
    targeted refinement suggestions without the user re-explaining.
    """
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "Request body must be JSON"}), 400

    idea = body.get("idea", {})
    user_messages = body.get("messages", [])
    language = body.get("language", "en")

    if not idea.get("idea_title"):
        return jsonify({"error": "idea.idea_title is required"}), 400
    try:
        user_messages = normalize_refine_messages(user_messages)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    # Build system prompt with full idea context
    lang_note = " Respond in Bahasa Indonesia." if language == "id" else ""
    system_prompt = f"""You are a research advisor helping refine a research idea. Be constructive, specific, and actionable.{lang_note}

The idea being refined:
Title: {idea.get('idea_title', '')}
Field: {idea.get('field', '')}
Difficulty: {idea.get('difficulty', '')}
Abstract: {idea.get('abstract', '')}
Methodology: {idea.get('methodology_hint', '')}
Why this idea: {idea.get('why_this_idea', '')}
Next steps: {idea.get('next_steps', '')}
Key papers: {idea.get('key_papers', '')}
Prerequisites: {idea.get('prerequisites', '')}

Help the researcher refine this idea. You can:
- Suggest narrowing or broadening the scope
- Identify weaknesses or blind spots
- Propose alternative methodologies
- Suggest concrete experiments or validations
- Point out potential pitfalls
- Recommend additional resources

    Keep responses concise (2-4 paragraphs max). Be direct and specific to THIS idea."""

    # Build messages array for LLM
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(user_messages)

    try:
        llm_client = LLMClient()
        reply = llm_client.call_chat(messages, retries=2, task_type="chat")
        if not reply:
            return jsonify({"error": "LLM returned empty response"}), 502

        # Local telemetry
        try:
            from src.core.health import record_usage
            record_usage("refine_chat", field=idea.get("field", ""), turns=len(user_messages))
        except Exception:
            pass

        return jsonify({"reply": reply}), 200
    except Exception as e:
        return jsonify({"error": f"Refinement failed: {e}"}), 500


@analysis_bp.route("/api/roadmap", methods=["POST"])
def api_roadmap():
    """
    Generate a research roadmap (knowledge graph) for an idea.

    Request body: idea object (idea_title required).
    Returns: {nodes: [...], edges: [...], title: str}

    Each node: {id, label, type, description, resources, duration, tier}
    Each edge: {from, to, label}
    Types: goal, theory, method, tool, paper, experiment, milestone
    Tiers: 0 (foundation) → 1 (intermediate) → 2 (advanced) → 3 (execution)
    """
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "Request body must be JSON"}), 400
    if not body.get("idea_title"):
        return jsonify({"error": "Field 'idea_title' is required"}), 400

    idea = body
    language = body.get("language", "en")
    lang_note = " Respond in Bahasa Indonesia." if language == "id" else ""

    prompt = f"""You are a research planning expert. Generate a knowledge graph (roadmap) for executing this research idea from zero to mastery.{lang_note}

IDEA:
Title: {idea.get('idea_title', '')}
Field: {idea.get('field', '')}
Difficulty: {idea.get('difficulty', '')}
Abstract: {idea.get('abstract', '')}
Methodology: {idea.get('methodology_hint', '')}
Prerequisites: {idea.get('prerequisites', '')}
Next steps: {idea.get('next_steps', '')}
Key papers: {idea.get('key_papers', '')}

Generate a JSON object with "nodes" and "edges" arrays.

NODES (12-20 nodes): Each node represents a milestone, skill, paper, tool, or experiment.
{{
  "id": "node_1",
  "label": "Short name (3-5 words)",
  "type": "theory|method|tool|paper|experiment|milestone|goal",
  "description": "What to do/learn (1-2 sentences)",
  "resources": "Specific resource (paper title, library name, course, etc.)",
  "duration": "Estimated time (e.g. '2 days', '1 week', '2 weeks')",
  "tier": 0-3 (0=foundation, 1=intermediate, 2=advanced, 3=execution)
}}

EDGES: Each edge connects two nodes (dependency).
{{
  "from": "node_id",
  "to": "node_id"
}}

Rules:
- Start with foundation nodes (tier 0): basic theory, tools to install, papers to read first
- Build up through intermediate (tier 1): core methods, key implementations
- Then advanced (tier 2): specific techniques for this idea
- End with execution (tier 3): run experiments, write paper, present results
- The final node should be the research goal itself
- Each node should have at least 1 incoming edge (except foundation nodes)
- Make it specific to THIS idea, not generic advice
- Include at least 2 paper nodes with real paper titles from the key_papers field
- Include at least 2 tool/library nodes with specific names

Return ONLY valid JSON. No markdown, no explanation."""

    try:
        llm_client = LLMClient()
        response = llm_client.call(prompt, retries=2, task_type="deep_dive")
        if not response:
            return jsonify({"error": "LLM returned empty response"}), 502

        # Parse JSON from response — LLMs often wrap in markdown or add text
        cleaned = response.strip()
        # Remove markdown code fences
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
        cleaned = cleaned.strip()

        data = None
        # Attempt 1: direct parse
        try:
            data = json.loads(cleaned)
        except Exception:
            pass

        # Attempt 2: find the outermost { ... } block
        if not data:
            # Find first { and last }
            start = cleaned.find('{')
            end = cleaned.rfind('}')
            if start >= 0 and end > start:
                json_str = cleaned[start:end+1]
                # Remove trailing commas before } or ]
                json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
                try:
                    data = json.loads(json_str)
                except Exception:
                    pass

        # Attempt 3: look for "nodes" array directly
        if not data:
            nodes_match = re.search(r'"nodes"\s*:\s*\[[\s\S]*?\]', cleaned)
            edges_match = re.search(r'"edges"\s*:\s*\[[\s\S]*?\]', cleaned)
            if nodes_match:
                try:
                    nodes_json = '{' + nodes_match.group() + '}'
                    if edges_match:
                        nodes_json = '{' + nodes_match.group() + ',' + edges_match.group() + '}'
                    nodes_json = re.sub(r',\s*([}\]])', r'\1', nodes_json)
                    data = json.loads(nodes_json)
                except Exception:
                    pass

        if not data or "nodes" not in data:
            return jsonify({"error": "Failed to parse roadmap structure. Try again."}), 502

        try:
            nodes, edges = sanitize_roadmap_graph(data)
        except ValueError:
            return jsonify({"error": "Failed to parse roadmap structure. Try again."}), 502

        result = {
            "title": idea.get("idea_title", ""),
            "nodes": nodes,
            "edges": edges,
        }

        # Telemetry
        try:
            from src.core.health import record_usage
            record_usage("roadmap", field=idea.get("field", ""), nodes=len(nodes))
        except Exception:
            pass

        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": f"Roadmap generation failed: {e}"}), 500
