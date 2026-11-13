"""Unit tests for Anna Sentinel MCP server and A2UI generator."""

import json
from anna_sentinel.sentinel_server import process_request
from anna_sentinel.a2ui_renderer import render_sentinel_surface


def test_initialize():
    req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    resp = json.loads(process_request(req))
    assert resp["id"] == 1
    assert "tools" in resp["result"]["capabilities"]


def test_tools_list():
    req = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    resp = json.loads(process_request(req))
    tools = [t["name"] for t in resp["result"]["tools"]]
    assert "audit_code" in tools
    assert "verify_claims" in tools
    assert "create_a2ui_card" in tools


def test_audit_code_tool():
    req = json.dumps({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "audit_code",
            "arguments": {"source_code": "import subprocess\nsubprocess.call(['ls'])"},
        },
    })
    resp = json.loads(process_request(req))
    data = json.loads(resp["result"]["content"][0]["text"])
    assert data["audit"]["is_safe"] is False
    assert "signature" in data["attestation"]


def test_a2ui_render():
    audit_data = {"is_safe": True, "violations": [], "metrics": {"elapsed_us": 120, "nodes_visited": 10}}
    surface = render_sentinel_surface(audit_data)
    assert surface["version"] == "1.0"
    assert len(surface["components"]) >= 3
    assert any(c["type"] == "badge" for c in surface["components"])
