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
from flask import Flask, send_from_directory

from src.web.routes.pipeline import pipeline_bp
from src.web.routes.sessions import sessions_bp
from src.web.routes.ideas    import ideas_bp
from src.web.routes.analysis import analysis_bp
from src.web.routes.settings import settings_bp
from src.web.routes.upload   import upload_bp

# ─── App factory ──────────────────────────────────────────────────────────────

def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="src/web/templates",
        static_folder="src/web/static",
    )

    # Register all blueprints
    for bp in (pipeline_bp, sessions_bp, ideas_bp, analysis_bp, settings_bp, upload_bp):
        app.register_blueprint(bp)

    @app.route("/")
    def index():
        return send_from_directory("src/web/templates", "dashboard.html")

    return app


app = create_app()

# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("  ScholarScout v1.4")
    print("  http://localhost:5050")
    print("=" * 50)

    try:
        from waitress import serve
        serve(app, host="0.0.0.0", port=5050, threads=4)
    except ImportError:
        # Waitress not installed — fall back to Flask dev server
        app.run(host="0.0.0.0", port=5050, debug=False, threaded=True)
