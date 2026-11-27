"""The Anna App layout: app.json, manifest.json and the bundled Executa agree with the plugin code."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from anna_sentinel.executa_plugin import EXECUTA_MANIFEST

ROOT = Path(__file__).resolve().parents[1]
EXECUTA_DIR = ROOT / "executas" / "anna-sentinel"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_bundled_handle_resolves_to_the_executa_directory() -> None:
    app = _load(ROOT / "app.json")
    manifest = _load(ROOT / "manifest.json")
    assert app["bundled_executas"]["anna-sentinel"]["path"] == "executas/anna-sentinel"
    assert (ROOT / app["bundled_executas"]["anna-sentinel"]["path"] / "executa.json").is_file()
    assert manifest["required_executas"][0]["tool_id"] == "bundled:anna-sentinel"
    assert manifest["user_message_prefix_template"].count("{user_message}") == 1


def test_executa_manifest_file_matches_the_plugin_describe() -> None:
    assert _load(EXECUTA_DIR / "manifest.json") == EXECUTA_MANIFEST


def test_versions_agree_everywhere() -> None:
    executa = _load(EXECUTA_DIR / "executa.json")
    manifest = _load(ROOT / "manifest.json")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert f'version = "{EXECUTA_MANIFEST["version"]}"' in pyproject
    assert executa["version"] == EXECUTA_MANIFEST["version"] == _load(ROOT / "app.json")["version"]
    assert manifest["required_executas"][0]["min_version"] == EXECUTA_MANIFEST["version"]


def test_binary_urls_match_the_release_tag_and_entrypoint() -> None:
    executa = _load(EXECUTA_DIR / "executa.json")
    tag = f"v{executa['version']}"
    urls = executa["distribution"]["binary_urls"]
    assert set(urls) == {"linux-x86_64", "linux-aarch64", "darwin-arm64", "darwin-x86_64", "windows-x86_64"}
    for platform, asset in urls.items():
        assert f"/download/{tag}/anna-sentinel-{platform}." in asset["url"]
        assert asset["entrypoint"] == ("bin/anna-sentinel.exe" if platform.startswith("windows") else "bin/anna-sentinel")


def test_stdio_frames_are_single_lines_and_the_process_keeps_reading() -> None:
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "describe"},
        {"jsonrpc": "2.0", "id": 3, "method": "health"},
    ]
    proc = subprocess.run(
        [sys.executable, str(ROOT / "src" / "anna_sentinel" / "executa_plugin.py")],
        input="".join(json.dumps(r) + "\n" for r in requests),
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(ROOT / "src")},
        timeout=30,
    )
    lines = proc.stdout.splitlines()
    assert [json.loads(line)["id"] for line in lines] == [1, 2, 3]
    assert json.loads(lines[1])["result"]["name"] == "anna-sentinel"
    assert proc.stderr == ""
