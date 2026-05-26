import os
import yaml
from datetime import datetime, timedelta, timezone

class Config:
    """
    Main configuration for ScholarScout.
    Reads values from config.yaml and environment variables.
    """
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    CONFIG_FILE = os.path.join(BASE_DIR, "config.yaml")
    
    _yaml_data = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            try:
                _yaml_data = yaml.safe_load(f) or {}
            except: pass

    # ─── DATE & TIME ───────────────────────────────────────────────────────
    TODAY = datetime.now(timezone.utc)
    TODAY_STR = TODAY.strftime("%Y-%m-%d")
    
    _s = os.environ.get("SCOUT_START_DATE", "")
    _e = os.environ.get("SCOUT_END_DATE", "")
    START_DATE = datetime.fromisoformat(_s + "T00:00:00+00:00") if _s else TODAY - timedelta(days=10)
    END_DATE   = datetime.fromisoformat(_e + "T23:59:59+00:00") if _e else TODAY
    
    # ─── FILE PATHS ─────────────────────────────────────────────────────────────
    DATA_DIR = os.path.join(BASE_DIR, "data")
    os.makedirs(DATA_DIR, exist_ok=True)
    
    OUTPUT_CSV    = os.path.join(DATA_DIR, f"scholarscout_ideas_{TODAY_STR}.csv")
    PROGRESS_FILE = os.path.join(DATA_DIR, "pipeline_progress.jsonl")
    SNAPSHOT_FILE = os.path.join(DATA_DIR, f"snapshot_{TODAY_STR}.json")
    CACHE_FILE    = os.path.join(DATA_DIR, "papers_cache.json")
    
    # ─── LLM PROVIDER CONFIG ───────────────────────────────────────────────────
    _llm_conf = _yaml_data.get("llm", {})
    _app_conf = _yaml_data.get("app", {})
    
    # Provider detection: config.yaml > env > default
    LLM_PROVIDER = (
        os.environ.get("SCOUT_LLM_PROVIDER", "") or
        _llm_conf.get("provider", "gemini")
    ).lower().strip()
    
    # API Key: env var (per-provider) > config.yaml > generic env
    _provider_env_keys = {
        "gemini": "GEMINI_API_KEY",
        "groq": "GROQ_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "openai": "OPENAI_API_KEY",
        "ollama": None,
        "custom": None,
    }
    
    _key_env = _provider_env_keys.get(LLM_PROVIDER)
    LLM_API_KEY = (
        (os.environ.get(_key_env, "") if _key_env else "") or
        os.environ.get("OPENROUTER_API_KEY", "") or
        _llm_conf.get("api_key", "")
    )
    
    # Model: env > config.yaml > provider default
    _provider_defaults = {
        "gemini": "gemini-2.0-flash",
        "groq": "llama-3.3-70b-versatile",
        "openrouter": "deepseek/deepseek-chat",
        "openai": "gpt-4o-mini",
        "ollama": "llama3.2",
        "custom": "gpt-4o-mini",
    }
    
    LLM_MODEL = (
        os.environ.get("OPENROUTER_MODEL", "") or
        _llm_conf.get("model", "") or
        _provider_defaults.get(LLM_PROVIDER, "gpt-4o-mini")
    )
    
    # Base URL: config.yaml > provider default
    _provider_urls = {
        "gemini": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        "groq": "https://api.groq.com/openai/v1/chat/completions",
        "openrouter": "https://openrouter.ai/api/v1/chat/completions",
        "openai": "https://api.openai.com/v1/chat/completions",
        "ollama": "http://localhost:11434/v1/chat/completions",
        "custom": "",
    }
    
    LLM_BASE_URL = _llm_conf.get("base_url", "") or _provider_urls.get(LLM_PROVIDER, "")
    
    # For non-Gemini providers, ensure URL ends with /chat/completions
    if LLM_PROVIDER != "gemini" and LLM_BASE_URL and "chat/completions" not in LLM_BASE_URL:
        LLM_BASE_URL = LLM_BASE_URL.rstrip("/") + "/chat/completions"
    
    # ─── BACKWARD COMPATIBILITY ────────────────────────────────────────────────
    # Old config names still work
    OPENROUTER_KEY = LLM_API_KEY
    OPENROUTER_MODEL = LLM_MODEL
    OPENROUTER_URL = LLM_BASE_URL
    
    # ─── PIPELINE SETTINGS ─────────────────────────────────────────────────────
    MAX_IDEAS     = int(os.environ.get("SCOUT_MAX_IDEAS", _app_conf.get("max_ideas", 50)))

    # ─── FEATURE FLAGS ─────────────────────────────────────────────────────────
    # Centralized registry. Overridable via env vars or config.yaml "features" section.
    _features_conf = _yaml_data.get("features", {})
    FEATURE_REFINE      = os.environ.get("SCOUT_REFINE", str(_features_conf.get("refine", False))) == '1'
    FEATURE_SENSITIVITY = os.environ.get("SCOUT_SENSITIVITY", str(_features_conf.get("sensitivity", False))) == '1'
    FEATURE_GROUNDING   = _features_conf.get("grounding", False)
    CACHE_EXPIRY_DAYS   = int(_features_conf.get("cache_expiry_days", 7))
    
    # ─── THRESHOLDS (externalized — tune via config.yaml "thresholds" section) ──
    _thresholds_conf = _yaml_data.get("thresholds", {})
    THRESHOLD_GROUNDING_HIGH       = float(_thresholds_conf.get("grounding_high", 0.65))
    THRESHOLD_GROUNDING_MEDIUM     = float(_thresholds_conf.get("grounding_medium", 0.40))
    THRESHOLD_NOVELTY_SEM_SIMILAR  = float(_thresholds_conf.get("novelty_semantic_similar", 0.82))
    THRESHOLD_NOVELTY_SEM_EXISTS   = float(_thresholds_conf.get("novelty_semantic_exists", 0.92))
    THRESHOLD_NOVELTY_JAC_SIMILAR  = float(_thresholds_conf.get("novelty_jaccard_similar", 0.40))
    THRESHOLD_NOVELTY_JAC_EXISTS   = float(_thresholds_conf.get("novelty_jaccard_exists", 0.70))
    THRESHOLD_CLUSTERER_MIN_JOIN   = float(_thresholds_conf.get("clusterer_min_join", 0.15))
    
    # ─── ARXIV CATEGORIES ────────────────────────────────────────────────────────
    _ui_cats = os.environ.get("SCOUT_CATEGORIES", "")
    if _ui_cats:
        CATEGORIES = [c.strip() for c in _ui_cats.split(",") if c.strip()]
    else:
        CATEGORIES = [
            "cs.AI", "cs.LG", "cs.CL", "cs.CV", "cs.RO",
            "stat.ML"
        ]
    
    @classmethod
    def get_ideas_per_category(cls) -> int:
        return max(1, round(cls.MAX_IDEAS / len(cls.CATEGORIES)) + 1)

    @classmethod
    def reload(cls):
        """Reload config from disk (used after settings change via UI)."""
        if os.path.exists(cls.CONFIG_FILE):
            with open(cls.CONFIG_FILE, "r") as f:
                try:
                    cls._yaml_data = yaml.safe_load(f) or {}
                except:
                    return
        
        _llm = cls._yaml_data.get("llm", {})
        cls.LLM_PROVIDER = _llm.get("provider", cls.LLM_PROVIDER)
        cls.LLM_API_KEY = _llm.get("api_key", cls.LLM_API_KEY)
        cls.LLM_MODEL = _llm.get("model", cls.LLM_MODEL) or cls._provider_defaults.get(cls.LLM_PROVIDER, "")
        cls.LLM_BASE_URL = _llm.get("base_url", "") or cls._provider_urls.get(cls.LLM_PROVIDER, "")
        
        if cls.LLM_PROVIDER != "gemini" and cls.LLM_BASE_URL and "chat/completions" not in cls.LLM_BASE_URL:
            cls.LLM_BASE_URL = cls.LLM_BASE_URL.rstrip("/") + "/chat/completions"
