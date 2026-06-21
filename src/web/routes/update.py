"""App update routes for staged ZIP-based updates."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

from flask import Blueprint, jsonify, request


update_bp = Blueprint("update", __name__)

_base_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
_data_dir = _base_dir / "data"
_status_file = _data_dir / "update_status.json"


def _read_status() -> dict:
    try:
        return json.loads(_status_file.read_text(encoding="utf-8"))
    except Exception:
        return {"state": "idle", "progress": 0, "message": ""}


def _safe_release_url(zip_url: str) -> bool:
    parsed = urlparse(str(zip_url or "").strip())
    if parsed.scheme != "https":
        return False
    return parsed.netloc in {"github.com", "api.github.com", "codeload.github.com"}


def _requested_port() -> int:
    host = request.host or "127.0.0.1:5050"
    try:
        return int(host.rsplit(":", 1)[1])
    except Exception:
        return 5050


@update_bp.route("/api/update/status")
def api_update_status():
    return jsonify(_read_status())


@update_bp.route("/api/update", methods=["POST"])
def api_update():
    body = request.get_json(silent=True) or {}
    version = str(body.get("version", "")).strip()
    zip_url = str(body.get("zip_url", "")).strip()

    if not version or not zip_url:
        return jsonify({"error": "version and zip_url are required"}), 400
    if not _safe_release_url(zip_url):
        return jsonify({"error": "Unsupported update source"}), 400

    status = _read_status()
    if status.get("state") == "running":
        return jsonify({"status": "already_running"}), 409

    _data_dir.mkdir(parents=True, exist_ok=True)
    _status_file.write_text(
        json.dumps({"state": "running", "progress": 1, "message": "Update requested"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    updater_path = _base_dir / "src" / "core" / "updater.py"
    preferred_port = _requested_port() + 1

    creationflags = 0
    for flag_name in ("CREATE_NEW_PROCESS_GROUP", "DETACHED_PROCESS"):
        creationflags |= int(getattr(subprocess, flag_name, 0))

    subprocess.Popen(
        [sys.executable, str(updater_path), str(_base_dir), version, zip_url, str(_status_file), str(preferred_port)],
        cwd=str(_base_dir),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )
    return jsonify({"status": "started", "status_url": "/api/update/status", "preferred_port": preferred_port})
