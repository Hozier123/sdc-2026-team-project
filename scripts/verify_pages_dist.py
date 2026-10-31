#!/usr/bin/env python3
"""Check a Pages build and record its public, reproducible file hashes."""

import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dist", type=Path)
    parser.add_argument("--base", default="/sdc-2026-team-project/")
    parser.add_argument("--api", default="https://kiraorder-api.replit.app/api/v1")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    dist = args.dist.resolve()
    base = args.base
    if not base.startswith("/") or not base.endswith("/") or ".." in base or "//" in base:
        parser.error("--base must be an absolute project path ending in /")
    html = (dist / "index.html").read_text(encoding="utf-8")
    if 'href="/assets/' in html or 'src="/assets/' in html or "/kiraorder/" in html:
        raise SystemExit("FAIL: index.html contains an incorrect asset prefix")
    urls = re.findall(r'(?:src|href)="([^"]+)"', html)
    local_assets = []
    for url in urls:
        parsed = urlsplit(url)
        if parsed.scheme or parsed.netloc or not parsed.path.startswith(base):
            raise SystemExit(f"FAIL: asset is outside Pages base: {url}")
        relative = parsed.path[len(base):]
        path = (dist / relative).resolve()
        if not path.is_relative_to(dist) or not path.is_file():
            raise SystemExit(f"FAIL: missing build asset: {relative}")
        local_assets.append(relative)
    js_files = sorted((dist / "assets").glob("*.js"))
    if not js_files or not any(args.api in path.read_text(encoding="utf-8") for path in js_files):
        raise SystemExit("FAIL: production API URL is missing from built JavaScript")
    files = sorted(path for path in dist.rglob("*") if path.is_file())
    manifest = {
        "status": "PASS",
        "base_path": base,
        "api_url": args.api,
        "index_sha256": sha256(dist / "index.html"),
        "entry_assets": local_assets,
        "files": {str(path.relative_to(dist)): sha256(path) for path in files},
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "files": len(files), "entry_assets": len(local_assets), "index_sha256": manifest["index_sha256"]}))


if __name__ == "__main__":
    main()
