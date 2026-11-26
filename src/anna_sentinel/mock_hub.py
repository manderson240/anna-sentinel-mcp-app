"""Claim Verification & HMAC-SHA256 Receipt Signing / Verification for Anna Sentinel."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any


_STOPWORDS = frozenset(
    {
        "the", "and", "for", "with", "that", "this", "from", "was", "were",
        "are", "have", "has", "had", "not", "into", "over", "under", "than",
    }
)


def _secret_key(secret_key: str | None = None) -> bytes:
    val = secret_key or os.getenv("ANNA_SENTINEL_SECRET_KEY", "anna-sentinel-dev-key")
    return val.encode("utf-8")


def _tokenize(text: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return {t for t in tokens if len(t) >= 3 and t not in _STOPWORDS}


def _negation_mismatch(claim: str, source_text: str) -> bool:
    neg_words = ("not", "never", "no", "failed", "False", "denied", "rejected")
    claim_neg = any(re.search(rf"\b{w}\b", claim, re.IGNORECASE) for w in neg_words)
    src_neg = any(re.search(rf"\b{w}\b", source_text, re.IGNORECASE) for w in neg_words)
    return claim_neg != src_neg


def _ollama_entailment(claim: str, source_text: str, model: str) -> bool | None:
    url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/") + "/api/chat"
    payload = json.dumps(
        {
            "model": model,
            "stream": False,
            "messages": [
                {
                    "role": "system",
                    "content": 'Return ONLY {"supported": true} or {"supported": false} checking if SOURCE entails CLAIM.',
                },
                {
                    "role": "user",
                    "content": f"SOURCE:\n{source_text[:3000]}\n\nCLAIM:\n{claim}",
                },
            ],
            "options": {"temperature": 0.0},
        }
    ).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content = data["message"]["content"]
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end > start:
            parsed = json.loads(content[start : end + 1])
            if isinstance(parsed.get("supported"), bool):
                return bool(parsed["supported"])
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, ValueError, json.JSONDecodeError):
        return None
    return None


def verify_claims_against_source(
    claims: list[str],
    source_text: str,
    *,
    threshold: float = 0.85,
    min_overlap: float = 0.6,
    use_model: bool = False,
    model: str = "deepseek-v4.1-flash:cloud",
) -> dict[str, Any]:
    """Verify claim strings against actual source text with optional Ollama entailment check."""
    src_tokens = _tokenize(source_text)
    evaluated: list[dict[str, Any]] = []
    supported_count = 0

    for claim in claims:
        c_tokens = _tokenize(claim)
        overlap = len(c_tokens & src_tokens) / len(c_tokens) if c_tokens else 0.0
        neg_conflict = _negation_mismatch(claim, source_text)
        model_verdict = _ollama_entailment(claim, source_text, model) if use_model else None
        if model_verdict is not None:
            supported = model_verdict and not neg_conflict
        else:
            supported = (overlap >= min_overlap) and not neg_conflict
        if supported:
            supported_count += 1
        evaluated.append(
            {
                "text": claim,
                "supported": supported,
                "token_overlap": round(overlap, 4),
                "negation_conflict": neg_conflict,
                "method": "ollama" if model_verdict is not None else "deterministic-overlap",
            }
        )

    total = len(claims)
    score = round(supported_count / total, 4) if total > 0 else 1.0
    return {
        "score": score,
        "passed": score >= threshold,
        "total_claims": total,
        "supported_claims": supported_count,
        "claims": evaluated,
    }


def evaluate_claims_mock(claims: list[dict[str, Any]], threshold: float = 0.85) -> dict[str, Any]:
    """Evaluate pre-labeled discrete claim objects deterministically."""
    total = len(claims)
    supported_count = sum(1 for c in claims if bool(c.get("supported", False)))
    score = round(supported_count / total, 4) if total > 0 else 1.0
    return {
        "score": score,
        "passed": score >= threshold,
        "total_claims": total,
        "supported_claims": supported_count,
        "claims": claims,
    }


def generate_attestation_receipt(payload: str, secret_key: str | None = None) -> dict[str, Any]:
    """Generate HMAC-SHA256 attestation receipt for an audited payload."""
    ts = int(time.time())
    payload_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    msg = f"{payload_hash}:{ts}".encode("utf-8")
    sig = hmac.new(_secret_key(secret_key), msg, hashlib.sha256).hexdigest()
    return {
        "timestamp": ts,
        "signature": sig,
        "payload_hash": payload_hash,
        "verified": True,
    }


def verify_attestation_receipt(
    payload: str,
    receipt: dict[str, Any],
    secret_key: str | None = None,
) -> bool:
    """Cryptographically verify a generated HMAC-SHA256 attestation receipt."""
    ts = receipt.get("timestamp")
    sig = str(receipt.get("signature", ""))
    claimed_hash = str(receipt.get("payload_hash", ""))
    if not isinstance(ts, int) or not sig or not claimed_hash:
        return False
    expected_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    if not hmac.compare_digest(claimed_hash, expected_hash):
        return False
    msg = f"{expected_hash}:{ts}".encode("utf-8")
    expected_sig = hmac.new(_secret_key(secret_key), msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected_sig)
