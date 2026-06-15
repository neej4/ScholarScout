"""
Helpers for analysis routes.

These utilities keep request validation and LLM-output sanitization in pure-Python
functions so we can test them without importing Flask route modules.
"""

from __future__ import annotations

from typing import Any


def normalize_refine_messages(messages: Any, limit: int = 10) -> list[dict[str, str]]:
    """Validate and normalize chat history for /api/refine.

    Returns a cleaned list of {role, content} messages limited to user/assistant roles.
    Raises ValueError on malformed payloads so the route can return 400 instead of 500.
    """
    if not isinstance(messages, list) or not messages:
        raise ValueError("messages must be a non-empty array")

    cleaned: list[dict[str, str]] = []
    for idx, msg in enumerate(messages[-limit:]):
        if not isinstance(msg, dict):
            raise ValueError(f"messages[{idx}] must be an object")
        role = msg.get("role")
        content = msg.get("content")
        if role not in ("user", "assistant"):
            raise ValueError(f"messages[{idx}].role must be 'user' or 'assistant'")
        if not isinstance(content, str) or not content.strip():
            raise ValueError(f"messages[{idx}].content must be a non-empty string")
        cleaned.append({"role": role, "content": content.strip()})

    if not cleaned:
        raise ValueError("messages must contain at least one valid chat turn")
    return cleaned


def sanitize_roadmap_graph(data: Any) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Normalize roadmap JSON produced by the LLM.

    Invalid node/edge entries are dropped instead of crashing the endpoint.
    """
    if not isinstance(data, dict):
        raise ValueError("roadmap payload must be a JSON object")

    raw_nodes = data.get("nodes")
    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise ValueError("roadmap payload must include a non-empty nodes array")

    nodes: list[dict[str, Any]] = []
    for idx, raw_node in enumerate(raw_nodes):
        if not isinstance(raw_node, dict):
            continue
        node_id = str(raw_node.get("id") or f"node_{idx}").strip()
        label = str(raw_node.get("label") or "Unnamed").strip()
        if not node_id:
            node_id = f"node_{idx}"
        if not label:
            label = "Unnamed"

        tier = raw_node.get("tier", 0)
        try:
            tier = int(tier)
        except (TypeError, ValueError):
            tier = 0
        tier = max(0, min(3, tier))

        nodes.append(
            {
                "id": node_id,
                "label": label,
                "type": str(raw_node.get("type") or "milestone").strip() or "milestone",
                "description": str(raw_node.get("description") or "").strip(),
                "resources": str(raw_node.get("resources") or "").strip(),
                "duration": str(raw_node.get("duration") or "").strip(),
                "tier": tier,
            }
        )

    if not nodes:
        raise ValueError("roadmap payload contains no valid nodes")

    node_ids = {node["id"] for node in nodes}
    raw_edges = data.get("edges", [])
    if not isinstance(raw_edges, list):
        raw_edges = []

    edges: list[dict[str, str]] = []
    for raw_edge in raw_edges:
        if not isinstance(raw_edge, dict):
            continue
        src = str(raw_edge.get("from") or "").strip()
        dst = str(raw_edge.get("to") or "").strip()
        if src in node_ids and dst in node_ids:
            edge: dict[str, str] = {"from": src, "to": dst}
            label = str(raw_edge.get("label") or "").strip()
            if label:
                edge["label"] = label
            edges.append(edge)

    return nodes, edges
