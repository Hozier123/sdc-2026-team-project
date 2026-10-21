"""Offline bootstrap helper: install pinned Python wheels without pip's temp directory.

Usage:
  py -3 scripts/install_python_wheels.py <wheelhouse> <target>

This is intentionally a small wheel extractor, not a package resolver. The
wheelhouse must already contain the pinned requirements and their transitive
wheels (Gate 0's bootstrap creates it from a verified mirror or local cache).
It is used only when GATE0_WHEELHOUSE is set; the normal path is pip.
"""

import shutil
import sys
import zipfile
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: install_python_wheels.py <wheelhouse> <target>", file=sys.stderr)
        return 2
    wheelhouse = Path(sys.argv[1])
    target = Path(sys.argv[2])
    wheels = sorted(wheelhouse.glob("*.whl"))
    if not wheels:
        print(f"no wheels found in {wheelhouse}", file=sys.stderr)
        return 2

    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)

    for whl in wheels:
        with zipfile.ZipFile(whl) as archive:
            for info in archive.infolist():
                name = info.filename
                marker = ".data/purelib/"
                if marker not in name:
                    marker = ".data/platlib/"
                if marker in name:
                    rel = name.split(marker, 1)[1]
                elif ".data/" in name:
                    continue
                else:
                    rel = name
                if not rel or rel.endswith("/"):
                    continue
                dest = target / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(archive.read(info))
    print(f"INSTALLED_WHEELS={len(wheels)} TARGET={target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
