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
    Returns: outline, methodology, datasets, references, timeline, tools.
    """
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "Request body must be JSON"}), 400
    if not body.get("idea_title"):
        return jsonify({"error": "Field 'idea_title' is required"}), 400

    language = body.get("language", "en")

    try:
        llm_client = LLMClient()
        handler = DeepDiveHandler(llm_client)
        result = handler.generate(body, language)
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
