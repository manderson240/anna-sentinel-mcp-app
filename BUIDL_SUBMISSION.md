# DoraHacks BUIDL Submission: Anna Sentinel MCP App

**Track**: Anna AI App Builder Program (Model Context Protocol & Agent Tools)  
**Repository**: https://github.com/manderson240/anna-sentinel-mcp-app  

This file mirrors what I entered in the DoraHacks form.

---

## Form fields

### Name
```text
Anna Sentinel MCP App
```

### Brief description (120 characters max, this one is 118)
```text
MCP server for Anna AI OS: a static AST check on agent Python code, a claim score, and a JSON review card for a human.
```

### Tags
```text
AI > AI Agents
```

### Team
```text
Mike Anderson (Solo builder, github.com/manderson240)
```

### Links
- GitHub: https://github.com/manderson240/anna-sentinel-mcp-app
- Demo video: https://github.com/manderson240/anna-sentinel-mcp-app/raw/main/docs/anna_sentinel_demo.mp4

### Contact
- Telegram: `manderson240`
- Discord: `miked238725`

---

## Description

# Anna Sentinel MCP App

### Why I built this
Agents that write and run Python need a cheap check before the code runs, and a person often has to approve the run. I wanted a tool an agent host can call over MCP that answers two questions quickly: does this code use any of a short list of dangerous calls, and what should the approval screen show. Asking a model to judge code safety costs tokens on every call, so I used Python's own `ast` module instead.

### How it works
I wrote an MCP server in plain Python with no dependencies outside the standard library. It reads JSON-RPC 2.0 requests from stdin, one per line, in `process_request()` ([`src/anna_sentinel/sentinel_server.py`](src/anna_sentinel/sentinel_server.py)) and exposes three tools:

1. `audit_code`: `audit_source()` in [`verifier_ast.py`](src/anna_sentinel/verifier_ast.py) walks the AST and flags `eval`, `exec`, `__import__`, `getattr`, `setattr`, `delattr`, any import of `subprocess` or `importlib`, `os.system` / `os.popen`, and dunder attributes used for sandbox escapes (`__class__`, `__subclasses__`, `__bases__`, `__globals__`, `__builtins__`, `__dict__`, `__code__`). Each violation has a line number. The result also carries an HMAC-SHA256 receipt from `generate_attestation_receipt()` in [`mock_hub.py`](src/anna_sentinel/mock_hub.py).
2. `verify_claims`: `evaluate_claims_mock()` counts claims the caller has marked `supported` and returns `supported / total`, passing at 0.85 or above.
3. `create_a2ui_card`: runs the audit (and the claim score if claims are given) and returns a JSON card from `render_sentinel_surface()` in [`a2ui_renderer.py`](src/anna_sentinel/a2ui_renderer.py): a status badge, latency and node count, the violation list, an optional scorecard, and Approve / Quarantine / Rerun buttons. Approve is disabled when the code is unsafe and Quarantine is disabled when it is safe.

The server never runs the code it checks.

### Anna AI App Builder Program
- The server follows the MCP stdio pattern: `initialize` (protocol version `2024-11-05`), `tools/list` with a JSON schema for each tool, and `tools/call`.
- The card buttons carry `call` names `anna.sentinel.approve`, `anna.sentinel.quarantine` and `anna.sentinel.rerun` for the host to handle. The server itself has no handler for them.
- I tested the server by piping JSON-RPC lines into it and through the unit tests.

### Limits
- The check is a short denylist, not a sandbox. `import os` on its own, `import os as o; o.system("ls")`, `os.execv`, `open`, `import socket`, `builtins.eval` and `while True: pass` all pass as safe today.
- `verify_claims` does not extract or check claims; it only counts the `supported` flags it is given.
- The receipt uses a hard-coded demo key and always reports `"verified": true`. Nothing verifies it.
- The card is my own JSON layout tagged `version: "1.0"`. I have not validated it against the A2UI schema.

### Verification
- 10 of 10 unit tests pass in 0.01 s on my machine (`tests/test_verifier_ast.py`, `tests/test_sentinel_server.py`). They cover clean code, `os.system`, `subprocess`, `eval`, a `__class__` / `__subclasses__` chain, syntax errors, `initialize`, `tools/list`, `audit_code` and the card renderer.
- On my machine the AST check on a five-line function takes about 100 to 150 µs on the first call in a fresh process and has a median of 26 µs over 1,000 repeated calls.

```bash
git clone https://github.com/manderson240/anna-sentinel-mcp-app.git
cd anna-sentinel-mcp-app
uv run pytest -q
uv run python -m anna_sentinel.sentinel_server
```

---

## Architecture diagrams

See [README.md](README.md#architecture) for the flowchart, sequence diagram, and state diagram.
