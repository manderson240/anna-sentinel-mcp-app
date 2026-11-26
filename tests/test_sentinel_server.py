"""Unit tests for Anna Sentinel MCP server, Executa plugin, receipts, and Schema v4 manifest."""

from __future__ import annotations

import json
from pathlib import Path

from anna_sentinel.a2ui_renderer import render_sentinel_surface
from anna_sentinel.executa_plugin import handle_executa_request
from anna_sentinel.mock_hub import (
    generate_attestation_receipt,
    verify_attestation_receipt,
    verify_claims_against_source,
)
from anna_sentinel.sentinel_server import process_request


def test_initialize() -> None:
    req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    resp = json.loads(process_request(req) or "{}")
    assert resp["id"] == 1
    assert "tools" in resp["result"]["capabilities"]


def test_tools_list() -> None:
    req = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    resp = json.loads(process_request(req) or "{}")
    tools = [t["name"] for t in resp["result"]["tools"]]
    assert {"audit_code", "verify_claims", "verify_receipt", "create_a2ui_card"}.issubset(set(tools))


def test_audit_code_and_hmac_receipt_verification() -> None:
    src = "def f(x: int) -> int:\n    return x + 1\n"
    req = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "audit_code", "arguments": {"source_code": src}},
        }
    )
    resp = json.loads(process_request(req) or "{}")
    data = json.loads(resp["result"]["content"][0]["text"])
    assert data["audit"]["is_safe"] is True
    receipt = data["attestation"]
    assert verify_attestation_receipt(src, receipt) is True

    # Tampered source or signature must fail verification
    assert verify_attestation_receipt(src + " # modified", receipt) is False
    tampered = dict(receipt, signature="0" * 64)
    assert verify_attestation_receipt(src, tampered) is False


def test_verify_claims_against_source_text() -> None:
    source_text = "Anna Sentinel runs static Python AST checks locally in under one millisecond with zero tokens."
    res = verify_claims_against_source(
        [
            "Anna Sentinel runs static Python AST checks locally",
            "Anna Sentinel uses zero tokens",
            "Anna Sentinel sends code to an external paid API",
        ],
        source_text,
        threshold=0.9,
    )
    assert res["total_claims"] == 3
    assert res["supported_claims"] == 2
    assert res["passed"] is False

    mcp_req = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "verify_claims",
                "arguments": {
                    "source_text": source_text,
                    "claims": ["Anna Sentinel runs static Python AST checks locally"],
                },
            },
        }
    )
    mcp_resp = json.loads(process_request(mcp_req) or "{}")
    payload = json.loads(mcp_resp["result"]["content"][0]["text"])
    assert payload["passed"] is True


def test_executa_plugin_describe_health_and_invoke() -> None:
    desc = handle_executa_request({"jsonrpc": "2.0", "id": 1, "method": "describe"})
    assert desc["result"]["name"] == "anna-sentinel"

    health = handle_executa_request({"jsonrpc": "2.0", "id": 2, "method": "health"})
    assert health["result"]["status"] == "ready"

    inv = handle_executa_request(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "invoke",
            "params": {
                "tool": "audit_code",
                "arguments": {"source_code": "import os as o\no.system('id')"},
            },
        }
    )
    assert inv["result"]["success"] is True
    assert inv["result"]["data"]["audit"]["is_safe"] is False

    receipt = generate_attestation_receipt("x = 1")
    ver = handle_executa_request(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "invoke",
            "params": {"tool": "verify_receipt", "arguments": {"source_code": "x = 1", "receipt": receipt}},
        }
    )
    assert ver["result"]["data"]["valid"] is True


def test_anna_app_manifest_schema_v4_keys() -> None:
    manifest_path = Path(__file__).resolve().parents[1] / "anna_app_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    allowed_top_keys = {
        "schema",
        "required_executas",
        "optional_executas",
        "tags",
        "system_prompt_addendum",
        "user_message_prefix_template",
        "ui",
        "dev",
        "storage",
    }
    assert manifest["schema"] == 4
    assert set(manifest.keys()).issubset(allowed_top_keys)
    assert manifest["required_executas"][0]["tool_id"] == "anna-sentinel"


def test_a2ui_render() -> None:
    audit_data = {"is_safe": True, "violations": [], "metrics": {"elapsed_us": 120, "nodes_visited": 10}}
    surface = render_sentinel_surface(audit_data)
    assert surface["version"] == "1.0"
    assert len(surface["components"]) >= 3
    assert any(c["type"] == "badge" for c in surface["components"])


def test_mcp_and_executa_expose_the_same_tools_and_arguments() -> None:
    from anna_sentinel.executa_plugin import EXECUTA_MANIFEST

    mcp = {
        t["name"]: (set(t["inputSchema"]["properties"]), set(t["inputSchema"].get("required", [])))
        for t in json.loads(process_request(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})))["result"]["tools"]
    }
    executa = {
        t["name"]: ({p["name"] for p in t["parameters"]}, {p["name"] for p in t["parameters"] if p["required"]})
        for t in EXECUTA_MANIFEST["tools"]
    }
    assert len(mcp) == 4
    assert executa == mcp


def test_executa_create_a2ui_card_and_use_model_argument() -> None:
    inv = handle_executa_request(
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "invoke",
            "params": {"tool": "create_a2ui_card", "arguments": {"source_code": "x = 1"}},
        }
    )
    assert inv["result"]["success"] is True
    assert inv["result"]["data"]


def test_executa_manifest_has_no_email_address() -> None:
    from anna_sentinel.executa_plugin import EXECUTA_MANIFEST

    assert "@" not in json.dumps(EXECUTA_MANIFEST)
    assert EXECUTA_MANIFEST["author"] == "Mike Anderson"
