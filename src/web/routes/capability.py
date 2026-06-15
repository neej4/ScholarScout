"""CapabilityScout web route: run the capability-matching flow synchronously."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Optional

from flask import Blueprint, jsonify, request

capability_bp = Blueprint("capability", __name__)

_base_dir = Path(__file__).resolve().parents[3]
_capability_src = _base_dir.parent / "capabilityscout" / "src"
if str(_capability_src) not in sys.path:
    sys.path.insert(0, str(_capability_src))

CapabilityProfile = None
CapabilityValidationError = ValueError
ScholarScoutCoreShim = None
run_capability_pipeline = None
_CAPABILITY_IMPORT_ERROR: Optional[Exception] = None

try:
    from capabilityscout import (  # type: ignore  # noqa: E402
        CapabilityProfile,
        CapabilityValidationError,
        ScholarScoutCoreShim,
        run_capability_pipeline,
    )
except Exception as exc:  # pragma: no cover - exercised in integration/CI environments
    _CAPABILITY_IMPORT_ERROR = exc


@capability_bp.route("/api/capability", methods=["POST"])
def api_capability():
    if _CAPABILITY_IMPORT_ERROR is not None:
        return jsonify({
            "error": "Capability mode is unavailable because capabilityscout is not installed.",
            "details": str(_CAPABILITY_IMPORT_ERROR),
        }), 503

    body = request.get_json(silent=True) or {}
    selected_categories = body.get("field_focus") or body.get("categories") or []
    profile_data = dict(body.get("profile") or {})
    if selected_categories and not profile_data.get("field_focus"):
        profile_data["field_focus"] = selected_categories

    try:
        max_papers_per_field = max(3, int(body.get("max_papers_per_field", 12)))
        n = max(1, min(int(body.get("max_ideas", 8)), 20))
        language = str(body.get("language", "en") or "en")
        research_context = str(body.get("research_context", "") or "")
        approach = str(body.get("approach", "any") or "any")

        profile = CapabilityProfile.from_dict(profile_data)
        core = ScholarScoutCoreShim(
            research_context=research_context,
            language=language,
            approach=approach,
        )

        data_dir = _base_dir / "data"
        output_path = data_dir / f"capability_snapshot_{int(time.time())}.json"
        result = run_capability_pipeline(
            profile,
            core=core,
            max_papers_per_field=max_papers_per_field,
            n=n,
            language=language,
            output_path=output_path,
        )
        return jsonify(result)
    except (CapabilityValidationError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Capability mode failed: {exc}"}), 500
