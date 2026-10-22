"""Build a private-source-free delivery ZIP and verify every archived file hash."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import zipfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    root = Path(__file__).resolve().parents[1]
    output = root.parent / "KiraOrder_前端交付.zip"
    directories = {"src", "public", "dist", "tests", "docs", "scripts", "contracts"}
    top_files = {"README.md", "package.json", "package-lock.json", "index.html",
                 "tsconfig.json", "vite.config.ts", ".gitignore", "启动 KiraOrder.command"}
    files = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if path.is_symlink() or not path.is_file():
            continue
        if rel.parts[0] not in directories and str(rel) not in top_files:
            continue
        if any(part.startswith(".env") or part in {"node_modules", ".git", "__pycache__", ".DS_Store"} for part in rel.parts):
            continue
        if path.suffix in {".pyc", ".tsbuildinfo"}:
            continue
        files.append(path)
    built_index = root / "dist/index.html"
    inputs = [p for p in files if p.relative_to(root).parts[0] in {"src", "public", "contracts"}
              or p.name in {"index.html", "package.json", "package-lock.json", "vite.config.ts"}
              and p.parent == root]
    if not built_index.exists() or any(p.stat().st_mtime > built_index.stat().st_mtime + 1 for p in inputs):
        raise SystemExit("Run npm run build after the latest source changes before packaging.")
    manifest = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files": {str(p.relative_to(root)): digest(p.read_bytes()) for p in files},
    }
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    (root / "DELIVERY_MANIFEST.json").write_bytes(manifest_bytes)
    temporary = output.with_suffix(".tmp.zip")
    with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, Path(root.name) / path.relative_to(root))
        archive.writestr(f"{root.name}/DELIVERY_MANIFEST.json", manifest_bytes)
    with zipfile.ZipFile(temporary) as archive:
        assert archive.testzip() is None
        for name, expected in manifest["files"].items():
            assert digest(archive.read(f"{root.name}/{name}")) == expected, name
    temporary.replace(output)
    print(json.dumps({"archive": str(output), "files": len(files) + 1,
                      "sha256": digest(output.read_bytes()), "manifest_verified": True}, ensure_ascii=False))


if __name__ == "__main__":
    main()
