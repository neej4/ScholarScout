"""
ScholarScout Web Server
=======================
Entry point for the Flask application.

Routes are split into Blueprints under src/web/routes/:
  pipeline.py  — /api/run, /api/stop, /api/status, /api/stream, /api/results
  sessions.py  — /api/sessions, /api/sessions/<index>
  ideas.py     — /api/quick, /api/regenerate
  analysis.py  — /api/deepdive, /api/novelty
  settings.py  — /api/settings (GET/POST), /api/settings/test,
                  /api/clear-cache, /api/clear-sessions
"""
import os
from flask import Flask, send_from_directory, render_template_string

from src.web.routes.pipeline import pipeline_bp
from src.web.routes.sessions import sessions_bp
from src.web.routes.ideas    import ideas_bp
from src.web.routes.analysis import analysis_bp
from src.web.routes.capability import capability_bp
from src.web.routes.settings import settings_bp
from src.web.routes.upload   import upload_bp

# ─── App factory ──────────────────────────────────────────────────────────────

def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="src/web/templates",
        static_folder="src/web/static",
    )

    # Security: limit upload size to 5MB
    app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

    # Register all blueprints
    for bp in (pipeline_bp, sessions_bp, ideas_bp, analysis_bp, capability_bp, settings_bp, upload_bp):
        app.register_blueprint(bp)

    @app.route("/")
    def index():
        # Read version from VERSION file — injected into dashboard JS
        # so CURRENT_VERSION never needs to be hardcoded in the HTML.
        version_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "VERSION")
        try:
            app_version = open(version_file).read().strip()
        except Exception:
            app_version = "0.0.0"

        html = open(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "src/web/templates/dashboard.html"),
            encoding="utf-8"
        ).read()

        # Replace the hardcoded CURRENT_VERSION placeholder with the real version
        html = html.replace("__APP_VERSION__", app_version)
        return html

    return app


app = create_app()

# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _version_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "VERSION")
    try:
        _app_ver = open(_version_file).read().strip()
    except Exception:
        _app_ver = "0.0.0"

    # Default: bind to localhost only. Set SCOUT_HOST=0.0.0.0 for LAN access.
    _host = os.environ.get("SCOUT_HOST", "127.0.0.1")
    _port = int(os.environ.get("SCOUT_PORT", "5050"))

    print("=" * 50)
    print(f"  ScholarScout v{_app_ver}")
    print(f"  http://{_host}:{_port}")
    print("=" * 50)

    # Startup health check & cache hygiene
    try:
        from src.core.health import run_health_check, print_health_report, run_cache_hygiene
        results = run_health_check()
        print_health_report(results)
        hygiene = run_cache_hygiene()
        if hygiene["expired"] > 0:
            print(f"  Cache cleanup: removed {hygiene['expired']} expired papers "
                  f"({hygiene['total_after']} remaining)")
    except Exception as e:
        print(f"  Health check skipped: {e}")

    print("=" * 50)

    try:
        from waitress import serve
        serve(app, host=_host, port=_port, threads=4)
    except ImportError:
        # Waitress not installed — fall back to Flask dev server
        app.run(host=_host, port=_port, debug=False, threaded=True)
