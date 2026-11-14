"""Model Context Protocol (MCP) JSON-RPC 2.0 stdio server for Anna AI OS.
========================================================================
Exposes 3 tools to Anna AI OS:
1. `audit_code` -> Runs sub-millisecond AST static verifier.
2. `verify_claims` -> Evaluates discrete QAG claims.
3. `create_a2ui_card` -> Emits declarative Google A2UI 1.0 component tree.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

from anna_sentinel.a2ui_renderer import render_sentinel_surface
from anna_sentinel.mock_hub import evaluate_claims_mock, generate_attestation_receipt
from anna_sentinel.verifier_ast import audit_source

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [sentinel] %(message)s", stream=sys.stderr)
log = logging.getLogger("anna.sentinel")

JSONRPC_VERSION = "2.0"


def handle_initialize(req_id: Any) -> dict[str, Any]:
    return {
        "jsonrpc": JSONRPC_VERSION,
        "id": req_id,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "anna-sentinel-mcp-app", "version": "1.0.0"},
        },
    }


def handle_tools_list(req_id: Any) -> dict[str, Any]:
    tools = [
        {
            "name": "audit_code",
            "description": "Performs static AST security verification in <0.2ms with zero token cost.",
            "inputSchema": {
                "type": "object",
                "properties": {"source_code": {"type": "string", "description": "Python code to audit"}},
                "required": ["source_code"],
            },
        },
        {
            "name": "verify_claims",
            "description": "Evaluates discrete factual claims via Question-Answer Generation (QAG) arithmetic.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "claims": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string"},
                                "supported": {"type": "boolean"},
                            },
                            "required": ["text", "supported"],
                        },
                    }
                },
                "required": ["claims"],
            },
        },
        {
            "name": "create_a2ui_card",
            "description": "Generates declarative Google A2UI 1.0 JSON surfaces for interactive user review.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "source_code": {"type": "string"},
                    "claims": {"type": "array"},
                },
                "required": ["source_code"],
            },
        },
    ]
    return {"jsonrpc": JSONRPC_VERSION, "id": req_id, "result": {"tools": tools}}


def handle_tools_call(req_id: Any, params: dict[str, Any]) -> dict[str, Any]:
    name = params.get("name")
    args = params.get("arguments", {})

    if name == "audit_code":
        src = args.get("source_code", "")
        res = audit_source(src)
        receipt = generate_attestation_receipt(src)
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": req_id,
            "result": {
                "content": [
                    {"type": "text", "text": json.dumps({"audit": res.to_dict(), "attestation": receipt}, indent=2)}
                ]
            },
        }

    elif name == "verify_claims":
        claims = args.get("claims", [])
        qag_res = evaluate_claims_mock(claims)
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": req_id,
            "result": {"content": [{"type": "text", "text": json.dumps(qag_res, indent=2)}]},
        }

    elif name == "create_a2ui_card":
        src = args.get("source_code", "")
        claims = args.get("claims", [])
        audit_res = audit_source(src).to_dict()
        qag_res = evaluate_claims_mock(claims) if claims else None
        surface = render_sentinel_surface(audit_res, qag_res)
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": req_id,
            "result": {"content": [{"type": "text", "text": json.dumps(surface, indent=2)}]},
        }

    return {
        "jsonrpc": JSONRPC_VERSION,
        "id": req_id,
        "error": {"code": -32601, "message": f"Method '{name}' not found"},
    }


def process_request(line: str) -> str | None:
    """Process a single JSON-RPC line."""
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        return json.dumps({"jsonrpc": JSONRPC_VERSION, "id": None, "error": {"code": -32700, "message": "Parse error"}})

    req_id = data.get("id")
    method = data.get("method")

    if method == "initialize":
        return json.dumps(handle_initialize(req_id))
    elif method == "tools/list":
        return json.dumps(handle_tools_list(req_id))
    elif method == "tools/call":
        return json.dumps(handle_tools_call(req_id, data.get("params", {})))
    elif method == "notifications/initialized":
        return None  # No response for notifications

    return json.dumps({"jsonrpc": JSONRPC_VERSION, "id": req_id, "error": {"code": -32601, "message": "Method not found"}})


def main() -> None:
    log.info("Starting anna-sentinel-mcp-app JSON-RPC server on stdio...")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        resp = process_request(line)
        if resp:
            sys.stdout.write(resp + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
