"""
Pipeline routes: /api/run, /api/stop, /api/status, /api/stream, /api/results
"""
import os
import json
import time
import threading
import subprocess
import sys
import glob

from flask import Blueprint, Response, jsonify, request
from src.core.session_compat import normalize_session

pipeline_bp = Blueprint("pipeline", __name__)

_pipeline_proc = None
_pipeline_lock = threading.Lock()

# Resolved at import time — same as before
_base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_data_dir = os.path.join(_base_dir, "data")
_progress_file = os.path.join(_data_dir, "pipeline_progress.jsonl")


def is_running() -> bool:
    global _pipeline_proc
    return _pipeline_proc is not None and _pipeline_proc.poll() is None


@pipeline_bp.route("/api/run", methods=["POST"])
def api_run():
    global _pipeline_proc
    with _pipeline_lock:
        if is_running():
            return jsonify({"status": "already_running"}), 409

        open(_progress_file, "w").close()
        env = os.environ.copy()
        body = request.get_json(silent=True) or {}

        # Map request body to environment variables consumed by run_pipeline.py
        _env_map = {
            "api_key":          "OPENROUTER_API_KEY",
            "model":            "OPENROUTER_MODEL",
            "start_date":       "SCOUT_START_DATE",
            "end_date":         "SCOUT_END_DATE",
            "max_ideas":        None,   # handled separately (int cast)
            "categories":       None,   # handled separately (join)
            "research_context": "SCOUT_CONTEXT",
            "language":         "SCOUT_LANGUAGE",
            "approach":         "SCOUT_APPROACH",
            "goal":             "SCOUT_GOAL",
            "goal_style":       "SCOUT_GOAL_STYLE",
            "gap_steering":     "SCOUT_GAP_STEERING",
            "refine":           "SCOUT_REFINE",
            "sensitivity":      "SCOUT_SENSITIVITY",
            "user_profile":     "SCOUT_USER_PROFILE",
            "feedback_summary": "SCOUT_FEEDBACK_SUMMARY",
        }
        for key, env_key in _env_map.items():
            val = body.get(key)
            if val is None:
                continue
            if key == "max_ideas":
                env["SCOUT_MAX_IDEAS"] = str(int(val))
            elif key == "categories":
                env["SCOUT_CATEGORIES"] = ",".join(val)
            elif env_key:
                env[env_key] = json.dumps(val, ensure_ascii=False) if isinstance(val, (dict, list)) else str(val)

        # Pipeline mode (default or review)
        mode = body.get("mode", "default")
        if mode:
            env["SCOUT_MODE"] = mode

        # Force refresh: bypass cache entirely, fetch fresh papers
        if body.get("force_refresh"):
            env["SCOUT_FORCE_REFRESH"] = "1"

        # Append uploaded file context to SCOUT_CONTEXT (if any)
        from src.web.routes.upload import get_uploaded_context
        uploaded = get_uploaded_context()
        if uploaded:
            existing_ctx = env.get("SCOUT_CONTEXT", "")
            env["SCOUT_CONTEXT"] = (existing_ctx + "\n\n--- ATTACHED FILE ---\n" + uploaded) if existing_ctx else uploaded

        script_path = os.path.join(_base_dir, "run_pipeline.py")
        _pipeline_proc = subprocess.Popen([sys.executable, script_path], env=env)

    return jsonify({"status": "started"})


@pipeline_bp.route("/api/stop", methods=["POST"])
def api_stop():
    global _pipeline_proc
    with _pipeline_lock:
        if _pipeline_proc and is_running():
            _pipeline_proc.terminate()
    return jsonify({"status": "stopped"})


@pipeline_bp.route("/api/status")
def api_status():
    snaps = sorted(glob.glob(os.path.join(_data_dir, "snapshot_*.json")), reverse=True)
    ideas_count = 0
    if snaps:
        try:
            with open(snaps[0], encoding="utf-8") as f:
                ideas_count = json.load(f).get("ideas_total", 0)
        except Exception:
            pass
    return jsonify({"running": is_running(), "ideas_count": ideas_count})


@pipeline_bp.route("/api/results")
def api_results():
    snaps = sorted(glob.glob(os.path.join(_data_dir, "snapshot_*.json")), reverse=True)
    if not snaps:
        return jsonify({"ideas": [], "papers_total": 0})
    try:
        with open(snaps[0], encoding="utf-8") as f:
            return jsonify(normalize_session(json.load(f)))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@pipeline_bp.route("/api/stream")
def api_stream():
    def generate():
        pos = 0
        yield ": connected\n\n"
        while True:
            try:
                if os.path.exists(_progress_file):
                    if os.path.getsize(_progress_file) < pos:
                        pos = 0
                    with open(_progress_file, "r", encoding="utf-8") as f:
                        f.seek(pos)
                        lines = f.readlines()
                        pos = f.tell()
                    for line in lines:
                        if line.strip():
                            yield f"data: {line.strip()}\n\n"
            except Exception:
                pass
            yield 'data: {"event":"ping"}\n\n'
            time.sleep(2)

    return Response(generate(), mimetype="text/event-stream")
