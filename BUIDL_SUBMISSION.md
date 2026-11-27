# Anna Sentinel MCP App: DoraHacks BUIDL submission

**Hackathon**: Anna AI App Builder Program (#2349)
**Track**: Anna AI Apps
**Repository**: https://github.com/manderson240/anna-sentinel-mcp-app

This is the text I paste into the DoraHacks build form, kept in the repo so it stays in step with the code.

## Form fields

### Name
```text
Anna Sentinel MCP App
```

### Brief description (119 characters)
```text
Static AST checker, source-grounded claim check and signed receipts for Anna apps, as an MCP server and Executa plugin.
```

### Tags
```text
AI Agents, MCP, Anna, Code Security, Python
```

### Team
```text
Mike Anderson
```

### Links
- GitHub: https://github.com/manderson240/anna-sentinel-mcp-app
- Demo video: https://raw.githubusercontent.com/manderson240/anna-sentinel-mcp-app/main/docs/anna_sentinel_demo.mp4

### Contact
- Telegram: `manderson240`
- Discord: `miked238725`

## Description

### Why I built this

An agent that writes or runs code needs a cheap check before it acts, and an agent that cites a source needs a check that the source says it. I wanted both as tools an Anna app can call, with a signed receipt that shows what was checked.

### How it works

`audit_code` parses Python with the standard library `ast` module and rejects dangerous imports, calls and dunder attributes, including aliased and wildcard imports. It returns the violations and an HMAC-SHA256 receipt. `verify_receipt` recomputes the hash and signature. `verify_claims` scores claims against a source text by token overlap and a negation flag, or with a model through Ollama when `use_model=true`. `create_a2ui_card` builds a JSON review card. The same tools run over MCP stdio and as an Anna Executa plugin (`describe`, `health`, `invoke`), with a Schema v4 manifest in `anna_app_manifest.json`.

### Verification

`uv run pytest -q` prints `36 passed`. Twenty-one of the tests are bypass attempts such as `import os as o`, `import io`, `f = eval` and `__subclasses__`. Others check a valid receipt, a tampered receipt, the Executa calls and the manifest keys. The Executa smoke test in the README returns two violations for `import os as o` and `o.system("id")`.

### Limits

The AST audit is static and is not a sandbox, and its module list is a blocklist. The claim check is word overlap with a negation flag, so it marks "revenue grew" as supported by "revenue fell". Receipts use a fixed development key unless `ANNA_SENTINEL_SECRET_KEY` is set. The model path needs Ollama and has no measured result here. The app is not on the Anna Marketplace and has no users. The organizer's grants need Marketplace publishing and 200 or more Qualified App monthly active users, and qualification is open until March 31, 2027. This BUIDL window closes November 30, 2026 at 15:59 UTC.

### Future roadmap

Publish the app on the Anna Marketplace, and then measure Qualified App MAU.
