#!/usr/bin/env python3
"""Anna Executa Plugin Entrypoint (JSON-RPC 2.0 over stdio: describe, invoke, health)."""

from __future__ import annotations

import json
import sys
from typing import Any

from anna_sentinel.a2ui_renderer import render_sentinel_surface
from anna_sentinel.mock_hub import generate_attestation_receipt, verify_attestation_receipt
from anna_sentinel.sentinel_server import _run_claim_check
from anna_sentinel.verifier_ast import audit_source


EXECUTA_MANIFEST: dict[str, Any] = {
    "name": "anna-sentinel",
    "display_name": "Anna Sentinel Code & Claim Verifier",
    "version": "1.1.0",
    "description": "Static AST Python code safety auditor, source-grounded claim checker, and HMAC receipt verifier.",
    "author": "Mike Anderson",
    "tools": [
        {
            "name": "audit_code",
            "description": "Audit Python code using static AST checks and return an HMAC attestation receipt.",
            "parameters": [
                {"name": "source_code", "type": "string", "description": "Python source code", "required": True}
            ],
        },
        {
            "name": "verify_claims",
            "description": "Verify claim statements against source_text.",
            "parameters": [
                {"name": "claims", "type": "array", "description": "List of claim strings", "items_type": "string", "required": True},
                {"name": "source_text", "type": "string", "description": "Ground-truth text", "required": False},
                {"name": "use_model", "type": "boolean", "description": "Ask an Ollama model instead of word overlap", "required": False},
            ],
        },
        {
            "name": "verify_receipt",
            "description": "Verify an HMAC-SHA256 attestation receipt against source_code.",
            "parameters": [
                {"name": "source_code", "type": "string", "description": "Original source", "required": True},
                {"name": "receipt", "type": "object", "description": "Receipt object", "required": True},
            ],
        },
        {
            "name": "create_a2ui_card",
            "description": "Generate a declarative JSON review card for audit and claim results.",
            "parameters": [
                {"name": "source_code", "type": "string", "description": "Python source code", "required": True},
                {"name": "source_text", "type": "string", "description": "Ground-truth text", "required": False},
                {"name": "claims", "type": "array", "description": "List of claim strings", "items_type": "string", "required": False},
            ],
        },
    ],
    "credentials": [],
    "runtime": {"type": "binary"},
}


def invoke_tool(tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute one Anna Executa tool call."""
    if tool == "audit_code":
        src = str(arguments.get("source_code", ""))
        audit_res = audit_source(src).to_dict()
        receipt = generate_attestation_receipt(src)
        return {"success": True, "data": {"audit": audit_res, "attestation": receipt}}

    if tool == "verify_claims":
        return {"success": True, "data": _run_claim_check(arguments)}

    if tool == "verify_receipt":
        src = str(arguments.get("source_code", ""))
        receipt = arguments.get("receipt") or {}
        return {"success": True, "data": {"valid": verify_attestation_receipt(src, receipt)}}

    if tool == "create_a2ui_card":
        src = str(arguments.get("source_code", ""))
        claims = arguments.get("claims", [])
        qag_res = _run_claim_check(arguments) if claims else None
        return {"success": True, "data": render_sentinel_surface(audit_source(src).to_dict(), qag_res)}

    raise ValueError(f"unknown tool: {tool}")


def handle_executa_request(req: dict[str, Any]) -> dict[str, Any]:
    """Handle one Anna Executa wire protocol request."""
    method = req.get("method")
    if method == "initialize":
        return {
            "result": {
                "protocolVersion": "2.0",
                "server_info": {"name": EXECUTA_MANIFEST["name"], "version": EXECUTA_MANIFEST["version"]},
                "capabilities": {},
            }
        }
    if method == "describe":
        return {"result": EXECUTA_MANIFEST}
    if method == "health":
        return {"result": {"status": "ready"}}
    if method == "invoke":
        params = req.get("params") or {}
        try:
            result = invoke_tool(str(params.get("tool", "")), params.get("arguments") or {})
            return {"result": result}
        except ValueError as exc:
            return {"error": {"code": -32601, "message": str(exc)}}
        except Exception as exc:  # noqa: BLE001
            return {"error": {"code": -32603, "message": str(exc)}}
    return {"error": {"code": -32601, "message": f"unknown method: {method}"}}


def main() -> None:
    """Read one JSON request per line until stdin closes. Stdout carries frames only."""
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as exc:
            resp: dict[str, Any] = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(exc)}}
        else:
            if not isinstance(req, dict):
                req = {}
            payload = handle_executa_request(req)
            resp = {"jsonrpc": "2.0", "id": req.get("id"), **payload}
        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
