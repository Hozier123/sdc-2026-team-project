"""Run all Gate 0 contract checks and verify the frozen output hash manifest."""

import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
HASH_FILE = ROOT / "docs" / "gate0-hashes.txt"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-hash",
        action="store_true",
        help="Run semantic/DDL checks before regenerating the output hash manifest.",
    )
    args = parser.parse_args()
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    subprocess.run([sys.executable, "-m", "pytest", "tests/contract", "-q"], cwd=ROOT, env=env, check=True)
    if args.skip_hash:
        print("GATE0_VERIFY_OK tests=passed hashes=skipped")
        return
    checked = 0
    for line in HASH_FILE.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        expected, relative = line.split(maxsplit=1)
        actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest().upper()
        if actual != expected:
            raise SystemExit(f"hash mismatch: {relative}\nexpected {expected}\nactual   {actual}")
        checked += 1
    print(f"GATE0_VERIFY_OK files={checked}")


if __name__ == "__main__":
    main()
