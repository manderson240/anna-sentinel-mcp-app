#!/usr/bin/env python3
"""Pack a PyInstaller binary into the archive Anna's binary distribution expects.

Usage: package_executa.py <binary> <platform-key> <out-dir>
Archive layout: manifest.json at the root and the binary under bin/.
"""

from __future__ import annotations

import json
import sys
import tarfile
import zipfile
from pathlib import Path

NAME = "anna-sentinel"


def main(binary: str, platform: str, out_dir: str) -> Path:
    exe = ".exe" if platform.startswith("windows") else ""
    version = json.loads((Path(__file__).resolve().parents[1] / "executas" / NAME / "executa.json").read_text())["version"]
    entry = f"bin/{NAME}{exe}"
    manifest = json.dumps(
        {"name": NAME, "version": version, "runtime": {"binary": {"entrypoint": entry, "permissions": {entry: "0o755"}}}},
        indent=2,
    )
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    if exe:
        archive = out / f"{NAME}-{platform}.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("manifest.json", manifest)
            z.write(binary, entry)
    else:
        archive = out / f"{NAME}-{platform}.tar.gz"
        manifest_file = out / "manifest.json"
        manifest_file.write_text(manifest)
        with tarfile.open(archive, "w:gz") as t:
            t.add(manifest_file, "manifest.json")
            t.add(binary, entry)
        manifest_file.unlink()
    return archive


if __name__ == "__main__":
    print(main(*sys.argv[1:4]))
