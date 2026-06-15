"""Structural tests for the CapabilityScout backend route wiring."""

from pathlib import Path


ROOT = Path(__file__).parent.parent


def test_preview_server_registers_capability_blueprint():
    preview = (ROOT / "preview_server.py").read_text(encoding="utf-8")
    assert "from src.web.routes.capability import capability_bp" in preview
    assert "capability_bp" in preview


def test_capability_route_exposes_api_endpoint():
    route_file = ROOT / "src" / "web" / "routes" / "capability.py"
    content = route_file.read_text(encoding="utf-8") if route_file.exists() else ""
    assert '@capability_bp.route("/api/capability", methods=["POST"])' in content
    assert "run_capability_pipeline" in content
