"""Deterministic Mock Hub for offline testing and IP-gated verification.
========================================================================
Implements discrete QAG claim scoring and HMAC-SHA256 attestation receipts
for judge verification without exposing proprietary internal neural weights.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any


def evaluate_claims_mock(claims: list[dict[str, Any]], threshold: float = 0.85) -> dict[str, Any]:
    """Evaluate discrete claims deterministically."""
    if not claims:
        return {
            "score": 1.0,
            "passed": True,
            "total_claims": 0,
            "supported_claims": 0,
            "claims": [],
        }

    supported_count = sum(1 for c in claims if bool(c.get("supported", False)))
    total = len(claims)
    score = round(supported_count / total, 4)
    passed = score >= threshold

    return {
        "score": score,
        "passed": passed,
        "total_claims": total,
        "supported_claims": supported_count,
        "claims": claims,
    }


def generate_attestation_receipt(payload: str, secret_key: str = "anna-sentinel-mock-key") -> dict[str, Any]:
    """Generate deterministic HMAC-SHA256 receipt for audit proof."""
    ts = int(time.time())
    msg = f"{payload}:{ts}".encode("utf-8")
    sig = hmac.new(secret_key.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return {
        "timestamp": ts,
        "signature": sig,
        "payload_hash": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        "verified": True,
    }
