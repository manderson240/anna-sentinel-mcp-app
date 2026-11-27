# Privacy

Anna Sentinel does not keep your data. It has no database, no account and no analytics.

## What it receives

Code snippets, claim strings, source text and receipts that you or Anna pass to its four tools. It reads them, returns a result and forgets them when the call ends. It writes nothing to disk.

## What it sends

Nothing leaves the process in the default setup. The one exception is `verify_claims` with `use_model=true`. Then the claims and the source text are sent to the Ollama server at `OLLAMA_BASE_URL`, which is `http://127.0.0.1:11434` unless you change it. If you point that variable at a remote host, your text goes to that host. I run no server of my own and I receive nothing.

## Receipts

Each audited snippet gets a SHA-256 hash and an HMAC-SHA256 signature. Both are computed locally. The key comes from `ANNA_SENTINEL_SECRET_KEY`. If you do not set it, a fixed development key is used, so anyone can forge such a receipt. A receipt shows that this code produced a result for this snippet. It does not hide the snippet.

## Logs

The plugin writes no logs. Anna may keep its own traces of tool calls under its own terms.

## Contact

Open an issue at https://github.com/manderson240/anna-sentinel-mcp-app/issues.
