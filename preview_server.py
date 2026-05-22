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
        if body.get("goal"): env["SCOUT_GOAL"] = body["goal"]
            
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

@app.route("/api/quick", methods=["POST"])
def api_quick():
    """Quick mode: generate ideas from cache or LLM knowledge (no fetching)."""
    from src.core.config import Config
    from src.core.llm import LLMClient
    from src.core.analyzer import TrendAnalyzer
    import re as re_mod
    
    body = request.get_json(silent=True) or {}
    categories = body.get("categories", ["cs.AI"])
    max_ideas = min(int(body.get("max_ideas", 5)), 20)
    language = body.get("language", "en")
    approach = body.get("approach", "any")
    goal = body.get("goal", "any")
    context = body.get("context", "")
    
    # Try to load papers from cache
    cache_file = os.path.join(data_dir, "papers_cache.json")
    cached_papers = {}
    from_cache = False
    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            cached_papers = json.load(f)
        from_cache = True
    except:
        pass
    
    # Filter cached papers by selected categories
    relevant_papers = []
    for pid, paper in cached_papers.items():
        if paper.get("category") in categories:
            relevant_papers.append(paper)
    
    # Build paper context for prompt
    paper_context = ""
    if relevant_papers:
        # Sort by recency, take top papers
        relevant_papers.sort(key=lambda p: p.get("submitted", ""), reverse=True)
        top_papers = relevant_papers[:15]
        paper_context = "\n".join(
            f"[P{i+1}] \"{p.get('title','')}\"\n    Abstract: {p.get('abstract','')[:150]}"
            for i, p in enumerate(top_papers)
        )
        paper_context = f"\n=== REFERENCE PAPERS (from cache) ===\n{paper_context}\n=== END ===\n"
    
    # Build approach/goal constraints
    approach_hint = ""
    if approach == "computational": approach_hint = "Ideas must be computational/AI-based."
    elif approach == "experimental": approach_hint = "Ideas must involve physical experiments, NOT computation."
    elif approach == "clinical": approach_hint = "Ideas must involve clinical/field studies."
    elif approach == "theoretical": approach_hint = "Ideas must be theoretical/review."
    
    goal_hint = ""
    if goal == "HACKATHON":
        goal_hint = "Ideas must be demo-able in 4-12 hours. Use existing APIs/tools. Include: what the demo looks like, tech stack, MVP scope."
    elif goal == "SIDE_PROJECT":
        goal_hint = "Ideas must be completable in 1-4 weekends. Deployable on free hosting."
    elif goal == "THESIS":
        goal_hint = "Ideas must fill 40-100 pages. Include literature review angle."
    elif goal == "PUBLICATION":
        goal_hint = "Ideas must have clear novelty claim and be publishable."
    
    lang_hint = "Write in formal academic Bahasa Indonesia." if language == "id" else ""
    
    cats_str = ", ".join(categories[:5])
    
    prompt = f"""Generate exactly {max_ideas} project ideas for the fields: {cats_str}
{approach_hint}
{goal_hint}
{lang_hint}
{f'Student context: {context}' if context else ''}
{paper_context}

Return a JSON array. Each object must have: idea_title, difficulty, abstract (3 sentences), why_hard, methodology_hint, next_steps (array of 3), resources_needed, prerequisites (array of 3-5 skills), why_this_idea, quality_score (1-10).
{f'Reference papers using P-numbers from the list above for key_paper_ids.' if paper_context else ''}

Respond ONLY with valid JSON array. No markdown."""

    try:
        llm = LLMClient()
        response = llm.call(prompt, task_type="idea_generation")
        
        if not response:
            return jsonify({"error": "LLM returned empty response", "ideas": []}), 500
        
        cleaned = re_mod.sub(r"```(?:json)?|```", "", response).strip()
        ideas_raw = json.loads(cleaned)
        if isinstance(ideas_raw, dict):
            ideas_raw = [ideas_raw]
        
        # Format ideas
        ideas = []
        cost_map = {"Undergraduate": "Free Tier", "Master's": "Cloud GPU ($50-200)", "PhD": "Institutional", "Hackathon": "Free (laptop + APIs)", "Side Project": "Free-$20", "Industry": "Company Budget"}
        
        for idea in ideas_raw[:max_ideas]:
            diff = idea.get("difficulty", "Master's")
            ideas.append({
                "idea_title": idea.get("idea_title", ""),
                "field": categories[0] if categories else "",
                "difficulty": diff,
                "cost_estimate": cost_map.get(diff, "Cloud GPU ($50-200)"),
                "cost_note": "",
                "why_hard": idea.get("why_hard", ""),
                "resources_needed": idea.get("resources_needed", ""),
                "abstract": idea.get("abstract", ""),
                "methodology_hint": idea.get("methodology_hint", ""),
                "next_steps": " | ".join(idea.get("next_steps", [])) if isinstance(idea.get("next_steps"), list) else idea.get("next_steps", ""),
                "key_papers": "",
                "why_this_idea": idea.get("why_this_idea", ""),
                "quality_score": idea.get("quality_score", 7),
                "prerequisites": " | ".join(idea.get("prerequisites", [])) if isinstance(idea.get("prerequisites"), list) else idea.get("prerequisites", ""),
                "inspired_by": "",
                "inspiration_title": "",
                "inspiration_link": "",
                "generated_date": Config.TODAY_STR
            })
        
        return jsonify({"ideas": ideas, "from_cache": from_cache and bool(relevant_papers)})
    except Exception as e:
        return jsonify({"error": str(e), "ideas": []}), 500

@app.route("/api/regenerate", methods=["POST"])
def api_regenerate():
    """Regenerate a single idea for a given field/approach."""
    from src.core.config import Config
    from src.core.llm import LLMClient
    from src.core.models import TrendAnalysis, Paper
    
    body = request.get_json(silent=True) or {}
    field = body.get("field", "cs.AI")
    approach = body.get("approach", "any")
    language = body.get("language", "en")
    context = body.get("context", "")
    exclude = body.get("exclude_title", "")
    
    try:
        llm = LLMClient()
        
        # Simple single-idea generation prompt (no paper grounding needed)
        from src.core.analyzer import TrendAnalyzer
        keywords = TrendAnalyzer.KEYWORD_SEEDS.get(field, ["research", "analysis"])[:5]
        
        approach_hint = ""
        if approach == "experimental":
            approach_hint = "The idea MUST involve physical experiments or lab work, NOT computation."
        elif approach == "clinical":
            approach_hint = "The idea MUST involve clinical studies with human subjects."
        elif approach == "theoretical":
            approach_hint = "The idea MUST be a theoretical contribution or systematic review."
        
        lang_hint = ""
        if language == "id":
            lang_hint = "Write ALL fields in formal academic Bahasa Indonesia."
        
        prompt = f"""Generate exactly 1 novel research idea for the field: {field}
Keywords in this area: {', '.join(keywords)}
{approach_hint}
{lang_hint}
{f'Student context: {context}' if context else ''}
Do NOT generate this title: {exclude}

Return a JSON object with: idea_title, difficulty (Undergraduate|Master's|PhD), abstract (3 sentences), why_hard (2 sentences), methodology_hint (2 sentences), next_steps (array of 3 strings), resources_needed, prerequisites (array of 3-5 skills needed), why_this_idea (1 sentence), quality_score (1-10).

Respond ONLY with valid JSON. No markdown."""

        response = llm.call(prompt, task_type="idea_generation")
        if response:
            import re
            cleaned = re.sub(r"```(?:json)?|```", "", response).strip()
            idea_data = json.loads(cleaned)
            
            # Normalize difficulty
            diff = idea_data.get("difficulty", "Master's")
            cost_map = {"Undergraduate": "Free Tier (Colab/Laptop)", "Master's": "Cloud GPU ($50-200)", "PhD": "Institutional Resources"}
            
            result = {
                "idea_title": idea_data.get("idea_title", ""),
                "field": field,
                "difficulty": diff,
                "cost_estimate": cost_map.get(diff, "Cloud GPU ($50-200)"),
                "cost_note": "",
                "why_hard": idea_data.get("why_hard", ""),
                "resources_needed": idea_data.get("resources_needed", ""),
                "abstract": idea_data.get("abstract", ""),
                "methodology_hint": idea_data.get("methodology_hint", ""),
                "next_steps": " | ".join(idea_data.get("next_steps", [])) if isinstance(idea_data.get("next_steps"), list) else idea_data.get("next_steps", ""),
                "key_papers": "",
                "why_this_idea": idea_data.get("why_this_idea", ""),
                "quality_score": idea_data.get("quality_score", 7),
                "prerequisites": " | ".join(idea_data.get("prerequisites", [])) if isinstance(idea_data.get("prerequisites"), list) else idea_data.get("prerequisites", ""),
                "inspired_by": "",
                "inspiration_title": "",
                "inspiration_link": "",
                "generated_date": Config.TODAY_STR
            }
            return jsonify({"idea": result})
        
        return jsonify({"error": "LLM returned empty response"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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

@app.route("/api/clear-cache", methods=["POST"])
def api_clear_cache():
    """Clear papers cache."""
    cache_file = os.path.join(data_dir, "papers_cache.json")
    try:
        open(cache_file, "w").write("{}")
        return jsonify({"status": "cleared"})
    except:
        return jsonify({"status": "ok"})

@app.route("/api/clear-sessions", methods=["POST"])
def api_clear_sessions():
    """Clear session history."""
    history_file = os.path.join(data_dir, "session_history.json")
    try:
        open(history_file, "w").write("[]")
        return jsonify({"status": "cleared"})
    except:
        return jsonify({"status": "ok"})

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
    print("  ScholarScout v1.3")
    print("  http://localhost:5050")
    print("=" * 50)
    
    try:
        from waitress import serve
        serve(app, host="0.0.0.0", port=5050, threads=4)
    except ImportError:
        # Waitress not installed — use Flask dev server
        app.run(host="0.0.0.0", port=5050, debug=False, threaded=True)
