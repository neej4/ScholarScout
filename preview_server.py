import os
import json
import time
import threading
import subprocess
import sys
from flask import Flask, Response, jsonify, send_from_directory, request

from src.core.llm import LLMClient
from src.core.deep_dive import DeepDiveHandler
from src.core.novelty_checker import NoveltyChecker

app = Flask(__name__, template_folder="src/web/templates", static_folder="src/web/static")

_pipeline_proc  = None
_pipeline_lock  = threading.Lock()
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
progress_file = os.path.join(data_dir, "pipeline_progress.jsonl")

def is_running():
    global _pipeline_proc
    return _pipeline_proc is not None and _pipeline_proc.poll() is None

@app.route("/")
def index():
    return send_from_directory("src/web/templates", "dashboard.html")

@app.route("/api/run", methods=["POST"])
def api_run():
    global _pipeline_proc
    with _pipeline_lock:
        if is_running():
            return jsonify({"status": "already_running"}), 409
        
        open(progress_file, "w").close()
        env = os.environ.copy()
        body = request.get_json(silent=True) or {}
        
        if body.get("api_key"): env["OPENROUTER_API_KEY"] = body["api_key"]
        if body.get("model"): env["OPENROUTER_MODEL"] = body["model"]
        if body.get("start_date"): env["SCOUT_START_DATE"] = body["start_date"]
        if body.get("end_date"): env["SCOUT_END_DATE"] = body["end_date"]
        if body.get("max_ideas"): env["SCOUT_MAX_IDEAS"] = str(int(body["max_ideas"]))
        if body.get("categories"): env["SCOUT_CATEGORIES"] = ",".join(body["categories"])
        if body.get("research_context"): env["SCOUT_CONTEXT"] = body["research_context"]
        if body.get("language"): env["SCOUT_LANGUAGE"] = body["language"]
        if body.get("approach"): env["SCOUT_APPROACH"] = body["approach"]
            
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run_pipeline.py")
        _pipeline_proc = subprocess.Popen(
            [sys.executable, script_path],
            env=env
        )
    return jsonify({"status": "started"})

@app.route("/api/stop", methods=["POST"])
def api_stop():
    global _pipeline_proc
    with _pipeline_lock:
        if _pipeline_proc and is_running():
            _pipeline_proc.terminate()
    return jsonify({"status": "stopped"})

@app.route("/api/status")
def api_status():
    import glob
    snaps = sorted(glob.glob(os.path.join(data_dir, "snapshot_*.json")), reverse=True)
    ideas_count = 0
    if snaps:
        try:
            with open(snaps[0], encoding="utf-8") as f:
                ideas_count = json.load(f).get("ideas_total", 0)
        except: pass
    return jsonify({"running": is_running(), "ideas_count": ideas_count})

@app.route("/api/results")
def api_results():
    import glob
    snaps = sorted(glob.glob(os.path.join(data_dir, "snapshot_*.json")), reverse=True)
    if not snaps:
        return jsonify({"ideas": [], "papers_total": 0})
    try:
        with open(snaps[0], encoding="utf-8") as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/sessions")
def api_sessions():
    """Get session history (list of past pipeline runs)."""
    history_file = os.path.join(data_dir, "session_history.json")
    try:
        with open(history_file, "r", encoding="utf-8") as f:
            history = json.load(f)
        # Return summary (without full ideas) for the list view
        summary = []
        for session in history:
            summary.append({
                "timestamp": session.get("timestamp", ""),
                "date": session.get("date", ""),
                "categories": session.get("categories", []),
                "approach": session.get("approach", "any"),
                "papers_total": session.get("papers_total", 0),
                "ideas_total": session.get("ideas_total", 0),
            })
        return jsonify(summary)
    except:
        return jsonify([])

@app.route("/api/sessions/<int:index>")
def api_session_detail(index):
    """Get full ideas for a specific session by index."""
    history_file = os.path.join(data_dir, "session_history.json")
    try:
        with open(history_file, "r", encoding="utf-8") as f:
            history = json.load(f)
        if 0 <= index < len(history):
            return jsonify(history[index])
        return jsonify({"error": "Session not found"}), 404
    except:
        return jsonify({"error": "No session history"}), 404

@app.route("/api/deepdive", methods=["POST"])
def api_deepdive():
    """
    Endpoint untuk Deep Dive analysis sebuah ide riset.
    Menerima objek ide lengkap dan mengembalikan analisis mendalam.
    
    Request body: {
        "idea_title": "string",
        "field": "string",
        "difficulty": "string",
        "abstract": "string",
        "why_hard": "string",
        "inspired_by": "string",
        "inspiration_title": "string",
        "inspiration_link": "string",
        "language": "en"|"id" (optional, default: "en")
    }
    
    Returns:
        200: {
            "outline": [...],
            "methodology": "...",
            "datasets": [...],
            "references": [...],
            "timeline": "...",
            "tools": [...]
        }
        400: {"error": "..."}
        500: {"error": "..."}
    """
    try:
        # Parse request body
        body = request.get_json(silent=True)
        if not body:
            return jsonify({"error": "Request body must be JSON"}), 400
        
        # Validasi idea_title ada
        if not body.get("idea_title"):
            return jsonify({"error": "Field 'idea_title' is required"}), 400
        
        # Ambil language dari body atau default ke 'en'
        language = body.get("language", "en")
        
        # Instansiasi LLMClient dan DeepDiveHandler
        llm_client = LLMClient()
        handler = DeepDiveHandler(llm_client)
        
        # Generate deep dive analysis
        result = handler.generate(body, language)
        
        # Return JSON response
        return jsonify(result), 200
        
    except ValueError as e:
        # ValueError dari DeepDiveHandler (parsing error, missing fields, dll)
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        # Exception umum lainnya
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route("/api/novelty", methods=["POST"])
def api_novelty():
    """
    Check novelty of a research idea title.
    
    Request body: {"idea_title": "string"}
    
    Returns:
        200: {"status": "novel"|"similar"|"exists", "papers": [...]}
        400: {"error": "idea_title is required"}
        503: {"error": "Both APIs failed"}
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
        
        # Return only status and papers (exclude max_similarity for cleaner API)
        return jsonify({
            "status": result["status"],
            "papers": result["papers"]
        })
    
    except RuntimeError as e:
        # Both APIs failed
        return jsonify({"error": str(e)}), 503
    
    except Exception as e:
        # Unexpected error
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

@app.route("/api/stream")
def api_stream():
    def generate():
        pos = 0
        yield ": connected\n\n"
        while True:
            try:
                if os.path.exists(progress_file):
                    if os.path.getsize(progress_file) < pos:
                        pos = 0
                with open(progress_file, "r", encoding="utf-8") as f:
                    f.seek(pos)
                    lines = f.readlines()
                    pos = f.tell()
                for line in lines:
                    if line.strip():
                        yield f"data: {line.strip()}\n\n"
            except: pass
            yield "data: {\"event\":\"ping\"}\n\n"
            time.sleep(2)
    return Response(generate(), mimetype="text/event-stream")

# ─── Settings API ────────────────────────────────────────────────────────────────

@app.route("/api/settings", methods=["GET"])
def api_settings_get():
    """Get current LLM settings (masks API key)."""
    from src.core.config import Config
    from src.core.llm import PROVIDERS
    
    key = Config.LLM_API_KEY
    masked_key = ""
    if key:
        masked_key = key[:8] + "..." + key[-4:] if len(key) > 12 else "***"
    
    return jsonify({
        "provider": Config.LLM_PROVIDER,
        "model": Config.LLM_MODEL,
        "base_url": Config.LLM_BASE_URL,
        "api_key_set": bool(key),
        "api_key_masked": masked_key,
        "providers": {k: {"name": v["name"], "free": v["free"], "default_model": v["default_model"], "docs": v["docs"]} 
                      for k, v in PROVIDERS.items()},
    })

@app.route("/api/settings", methods=["POST"])
def api_settings_save():
    """Save LLM settings to config.yaml."""
    import yaml
    from src.core.config import Config
    from src.core.llm import PROVIDERS
    
    body = request.get_json(silent=True) or {}
    provider = body.get("provider", "").lower().strip()
    api_key = body.get("api_key", "").strip()
    model = body.get("model", "").strip()
    base_url = body.get("base_url", "").strip()
    
    if provider and provider not in PROVIDERS:
        return jsonify({"error": f"Unknown provider: {provider}"}), 400
    
    # Read existing config
    config_path = Config.CONFIG_FILE
    try:
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f) or {}
    except:
        cfg = {}
    
    # Update LLM section
    if "llm" not in cfg:
        cfg["llm"] = {}
    
    if provider:
        cfg["llm"]["provider"] = provider
    if api_key:
        cfg["llm"]["api_key"] = api_key
    if model:
        cfg["llm"]["model"] = model
    elif provider:
        # Auto-set default model for provider
        cfg["llm"]["model"] = PROVIDERS[provider]["default_model"]
    if base_url:
        cfg["llm"]["base_url"] = base_url
    elif provider and provider != "custom":
        # Remove custom base_url when switching to known provider
        cfg["llm"].pop("base_url", None)
    
    # Write config
    try:
        with open(config_path, "w") as f:
            yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True)
    except Exception as e:
        return jsonify({"error": f"Failed to write config: {e}"}), 500
    
    # Reload config
    Config.reload()
    
    return jsonify({"status": "saved", "provider": Config.LLM_PROVIDER, "model": Config.LLM_MODEL})

@app.route("/api/settings/test", methods=["POST"])
def api_settings_test():
    """Test LLM connection with current or provided settings."""
    from src.core.config import Config
    from src.core.llm import LLMClient
    
    body = request.get_json(silent=True) or {}
    
    # Temporarily override config for testing
    orig_provider = Config.LLM_PROVIDER
    orig_key = Config.LLM_API_KEY
    orig_model = Config.LLM_MODEL
    orig_url = Config.LLM_BASE_URL
    
    try:
        if body.get("provider"):
            Config.LLM_PROVIDER = body["provider"]
        if body.get("api_key"):
            Config.LLM_API_KEY = body["api_key"]
        if body.get("model"):
            Config.LLM_MODEL = body["model"]
        if body.get("base_url"):
            Config.LLM_BASE_URL = body["base_url"]
        
        client = LLMClient()
        ok = client.ping()
        stats = client.get_token_stats()
        
        return jsonify({
            "success": ok,
            "provider": Config.LLM_PROVIDER,
            "model": Config.LLM_MODEL,
            "tokens_used": stats["total_tokens"],
        })
    finally:
        # Restore original config
        Config.LLM_PROVIDER = orig_provider
        Config.LLM_API_KEY = orig_key
        Config.LLM_MODEL = orig_model
        Config.LLM_BASE_URL = orig_url

if __name__ == "__main__":
    print("=" * 50)
    print("  ScholarScout (Python Preview Server)")
    print("  http://localhost:5050")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5050, debug=False, threaded=True)
