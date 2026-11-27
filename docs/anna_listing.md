# Anna Marketplace listing text

These are the values I enter on the Listing tab of the Anna Developer Console. Field names and limits come from the organizer's page https://anna.partners/developers/apps/app-listing.md

| Field | Value |
|---|---|
| Name (1 to 120 chars) | Anna Sentinel |
| Slug (3 to 80 chars, cannot change later) | anna-sentinel |
| Category | developer-tools |
| Short description (160 chars max) | Check Python code and claims before an agent acts on them. |
| Homepage URL | https://github.com/manderson240/anna-sentinel-mcp-app |
| Support URL | https://github.com/manderson240/anna-sentinel-mcp-app/issues |
| Privacy URL | https://github.com/manderson240/anna-sentinel-mcp-app/blob/main/PRIVACY.md |
| Logo | docs/anna_sentinel_logo.png, uploaded with the Upload logo button |
| Cover and screenshots | optional, not prepared |

## Long description

Anna Sentinel checks code and claims before an agent acts on them.

Mention it before you run a Python snippet that an agent wrote. It parses the snippet with the standard library `ast` module and flags dangerous imports and calls, such as `os`, `subprocess`, `eval` and `open`. It does not run the code.

It also compares claim strings against a source text and marks each one supported or not. The default check is word overlap plus a negation flag, so it misses antonyms. An optional mode asks a local Ollama model instead.

Each audited snippet gets a signed receipt. The receipt is an HMAC-SHA256 over the snippet hash, and the verify tool checks it later.

Limits I know about. The audit is a static check and not a sandbox. The blocklist is a list and not a proof. The offline claim check does not understand meaning. Set `ANNA_SENTINEL_SECRET_KEY` before you rely on a receipt.

Nothing is stored and nothing leaves the process unless you turn on the Ollama option. See the privacy page.

## Version

Version 1.1.2. Changelog text: First release as an installable Anna App with a bundled Executa.
