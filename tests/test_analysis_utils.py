"""Unit tests for pure helper functions behind analysis routes."""

from src.core.analysis_utils import normalize_refine_messages, sanitize_roadmap_graph


def test_normalize_refine_messages_accepts_valid_chat_history():
    cleaned = normalize_refine_messages(
        [
            {"role": "user", "content": "  Narrow this idea  "},
            {"role": "assistant", "content": "Focus on one dataset."},
        ]
    )
    assert cleaned == [
        {"role": "user", "content": "Narrow this idea"},
        {"role": "assistant", "content": "Focus on one dataset."},
    ]


def test_normalize_refine_messages_rejects_non_list_payload():
    try:
        normalize_refine_messages("not-a-list")
    except ValueError as e:
        assert "non-empty array" in str(e)
    else:
        raise AssertionError("Expected ValueError for invalid messages payload")


def test_normalize_refine_messages_rejects_invalid_entries():
    try:
        normalize_refine_messages([{"role": "system", "content": "x"}])
    except ValueError as e:
        assert "role" in str(e)
    else:
        raise AssertionError("Expected ValueError for invalid role")


def test_sanitize_roadmap_graph_drops_invalid_nodes_and_edges():
    nodes, edges = sanitize_roadmap_graph(
        {
            "nodes": [
                {"id": "n1", "label": "Read paper", "tier": "1"},
                "bad-node",
                {"label": "Run experiment", "tier": 9},
            ],
            "edges": [
                {"from": "n1", "to": "node_2"},
                "bad-edge",
                {"from": "n1", "to": "missing"},
            ],
        }
    )

    assert nodes == [
        {
            "id": "n1",
            "label": "Read paper",
            "type": "milestone",
            "description": "",
            "resources": "",
            "duration": "",
            "tier": 1,
        },
        {
            "id": "node_2",
            "label": "Run experiment",
            "type": "milestone",
            "description": "",
            "resources": "",
            "duration": "",
            "tier": 3,
        },
    ]
    assert edges == [{"from": "n1", "to": "node_2"}]


def test_sanitize_roadmap_graph_requires_valid_nodes():
    try:
        sanitize_roadmap_graph({"nodes": ["bad"], "edges": []})
    except ValueError as e:
        assert "no valid nodes" in str(e)
    else:
        raise AssertionError("Expected ValueError when all nodes are invalid")
