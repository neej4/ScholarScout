"""
Analysis routes: /api/deepdive, /api/novelty
"""
from flask import Blueprint, jsonify, request

from src.core.llm import LLMClient
from src.core.deep_dive import DeepDiveHandler
from src.core.novelty_checker import NoveltyChecker

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
