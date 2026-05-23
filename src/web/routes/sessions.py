"""
Session history routes: /api/sessions, /api/sessions/<index>
"""
import os
import json

from flask import Blueprint, jsonify

sessions_bp = Blueprint("sessions", __name__)

_base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_data_dir = os.path.join(_base_dir, "data")
_history_file = os.path.join(_data_dir, "session_history.json")


def _load_history() -> list:
    try:
        with open(_history_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


@sessions_bp.route("/api/sessions")
def api_sessions():
    """Return summary list of past pipeline runs (no full ideas payload)."""
    history = _load_history()
    summary = [
        {
            "timestamp":    s.get("timestamp", ""),
            "date":         s.get("date", ""),
            "categories":   s.get("categories", []),
            "approach":     s.get("approach", "any"),
            "papers_total": s.get("papers_total", 0),
            "ideas_total":  s.get("ideas_total", 0),
        }
        for s in history
    ]
    return jsonify(summary)


@sessions_bp.route("/api/sessions/<int:index>")
def api_session_detail(index: int):
    """Return full ideas for a specific session by index."""
    # Guard against negative indices (would wrap around the list)
    if index < 0:
        return jsonify({"error": "Invalid session index"}), 400

    history = _load_history()
    if index >= len(history):
        return jsonify({"error": "Session not found"}), 404

    return jsonify(history[index])
