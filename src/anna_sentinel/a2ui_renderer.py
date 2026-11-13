"""Google A2UI 1.0 Declarative UI Surface Renderer for Anna AI OS.
==================================================================
Transforms AST audit outcomes and QAG claim evaluations into interactive
A2UI 1.0 declarative surfaces ('Safe like data, expressive like code').
"""

from __future__ import annotations

import time
from typing import Any


def render_sentinel_surface(
    audit_result: dict[str, Any],
    qag_result: dict[str, Any] | None = None,
    surface_id: str = "anna-sentinel-surface-01",
) -> dict[str, Any]:
    """Compile audit and evaluation outcomes into an A2UI 1.0 component tree."""
    is_safe = audit_result.get("is_safe", False)
    violations = audit_result.get("violations", [])
    metrics = audit_result.get("metrics", {})

    status_color = "#10B981" if is_safe else "#EF4444"
    status_text = "PASSED: AST Secure" if is_safe else f"ALERT: {len(violations)} Violations"

    # 1. Root container
    components = [
        {
            "id": "header_card",
            "type": "card",
            "props": {
                "title": "Anna Sentinel Security & QAG Audit",
                "subtitle": f"Generated at {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
                "borderColor": status_color,
            },
        },
        {
            "id": "status_badge",
            "type": "badge",
            "props": {
                "text": status_text,
                "color": status_color,
                "variant": "filled",
            },
        },
        {
            "id": "metrics_grid",
            "type": "grid",
            "props": {
                "columns": 3,
                "items": [
                    {"label": "Elapsed Latency", "value": f"{metrics.get('elapsed_us', 0)} µs"},
                    {"label": "Nodes Analyzed", "value": str(metrics.get("nodes_visited", 0))},
                    {"label": "Token Cost", "value": "$0.0000 (0 tokens)"},
                ],
            },
        },
    ]

    # 2. Add violations list if any
    if violations:
        components.append(
            {
                "id": "violations_list",
                "type": "list",
                "props": {
                    "header": "Detected Security Breaches",
                    "items": violations,
                    "itemColor": "#EF4444",
                },
            }
        )

    # 3. Add QAG metrics if present
    if qag_result:
        components.append(
            {
                "id": "qag_scorecard",
                "type": "scorecard",
                "props": {
                    "score": qag_result.get("score", 1.0),
                    "passed": qag_result.get("passed", True),
                    "totalClaims": qag_result.get("total_claims", 0),
                    "supportedClaims": qag_result.get("supported_claims", 0),
                },
            }
        )

    # 4. Interactive Action Buttons
    components.append(
        {
            "id": "action_bar",
            "type": "action_group",
            "props": {
                "actions": [
                    {"label": "Approve Execution", "call": "anna.sentinel.approve", "disabled": not is_safe},
                    {"label": "Quarantine Code", "call": "anna.sentinel.quarantine", "disabled": is_safe},
                    {"label": "Rerun Audit", "call": "anna.sentinel.rerun", "disabled": False},
                ]
            },
        }
    )

    return {
        "version": "1.0",
        "surface_id": surface_id,
        "components": components,
        "data_model": {
            "audit": audit_result,
            "qag": qag_result or {},
        },
    }
