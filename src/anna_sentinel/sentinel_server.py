"""Model Context Protocol (MCP) JSON-RPC 2.0 stdio server for Anna AI OS."""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

from anna_sentinel.a2ui_renderer import render_sentinel_surface
from anna_sentinel.mock_hub import (
    evaluate_claims_mock,
    generate_attestation_receipt,
    verify_attestation_receipt,
    verify_claims_against_source,
)
from anna_sentinel.verifier_ast import audit_source


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [sentinel] %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("anna.sentinel")

JSONRPC_VERSION = "2.0"


def handle_initialize(req_id: Any) -> dict[str, Any]:
    return {
        "jsonrpc": JSONRPC_VERSION,
        "id": req_id,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "anna-sentinel-mcp-app", "version": "1.1.2"},
        },
    }


def handle_tools_list(req_id: Any) -> dict[str, Any]:
    tools = [
        {
            "name": "audit_code",
            "description": "Performs static AST security verification with no model call. The result reports elapsed_us.",
            "inputSchema": {
                "type": "object",
                "properties": {"source_code": {"type": "string", "description": "Python code to audit"}},
                "required": ["source_code"],
            },
        },
        {
            "name": "verify_claims",
            "description": "Verifies claim strings against source_text (or scores pre-labeled claims).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "source_text": {"type": "string", "description": "Ground-truth text to verify claims against"},
                    "claims": {"type": "array"},
                    "use_model": {"type": "boolean"},
                },
                "required": ["claims"],
            },
        },
        {
            "name": "verify_receipt",
            "description": "Cryptographically verifies an HMAC-SHA256 attestation receipt against source_code.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "source_code": {"type": "string"},
                    "receipt": {"type": "object"},
                },
                "required": ["source_code", "receipt"],
            },
        },
        {
            "name": "create_a2ui_card",
            "description": "Generates declarative JSON UI surfaces for interactive human review.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "source_code": {"type": "string"},
                    "source_text": {"type": "string"},
                    "claims": {"type": "array"},
                },
                "required": ["source_code"],
            },
        },
    ]
    return {"jsonrpc": JSONRPC_VERSION, "id": req_id, "result": {"tools": tools}}


def _run_claim_check(args: dict[str, Any]) -> dict[str, Any]:
    claims = args.get("claims", [])
    source_text = args.get("source_text")
    use_model = bool(args.get("use_model", False))
    if isinstance(source_text, str) and source_text.strip():
        claim_strs = [str(c.get("text", c) if isinstance(c, dict) else c) for c in claims]
        return verify_claims_against_source(claim_strs, source_text, use_model=use_model)
    dict_claims = [c if isinstance(c, dict) else {"text": str(c), "supported": False} for c in claims]
    return evaluate_claims_mock(dict_claims)


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

    if name == "verify_claims":
        qag_res = _run_claim_check(args)
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": req_id,
            "result": {"content": [{"type": "text", "text": json.dumps(qag_res, indent=2)}]},
        }

    if name == "verify_receipt":
        src = str(args.get("source_code", ""))
        receipt = args.get("receipt") or {}
        valid = verify_attestation_receipt(src, receipt)
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": req_id,
            "result": {"content": [{"type": "text", "text": json.dumps({"valid": valid}, indent=2)}]},
        }

    if name == "create_a2ui_card":
        src = args.get("source_code", "")
        claims = args.get("claims", [])
        audit_res = audit_source(src).to_dict()
        qag_res = _run_claim_check(args) if claims else None
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
        return json.dumps(
            {"jsonrpc": JSONRPC_VERSION, "id": None, "error": {"code": -32700, "message": "Parse error"}}
        )

    req_id = data.get("id")
    method = data.get("method")

    if method == "initialize":
        return json.dumps(handle_initialize(req_id))
    if method == "tools/list":
        return json.dumps(handle_tools_list(req_id))
    if method == "tools/call":
        return json.dumps(handle_tools_call(req_id, data.get("params", {})))
    if method == "notifications/initialized":
        return None

    return json.dumps(
        {"jsonrpc": JSONRPC_VERSION, "id": req_id, "error": {"code": -32601, "message": "Method not found"}}
    )


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
