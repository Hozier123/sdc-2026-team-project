"""Preflight: the frozen seed SQL bytes must match SEED_MANIFEST.json.

``app.seed`` and ``tools.reset_demo`` hash the raw bytes of the seed file before
they insert anything, so a CRLF working copy fails the load with
"seed SQL checksum does not match" even though every row is identical. The
frozen T2 file is 27,611 B / ``134EFD…`` at LF; its CRLF twin is 27,766 B /
``8EB158…``. ``Get-FileHash`` reports a mismatch in both cases and cannot say
whether the data changed or only the line endings.

Git already pins ``data/seed/*.sql`` to ``text eol=lf`` (see ``.gitattributes``),
but checkouts made before that rule, editors, and ``Set-Content`` can still
rewrite a working copy.

Usage (from ``backend/``)::

    python -m tools.check_seed_bytes            # check every tenant
    python -m tools.check_seed_bytes --fix      # rewrite EOL-only drift as LF
    python -m tools.check_seed_bytes --json     # machine-readable report

Exit codes: 0 = every file matches the manifest, 1 = drift (including an EOL-only
copy when ``--fix`` was not requested), 2 = the manifest or seed directory is
unusable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Sequence

from app.config import REPO_ROOT

DEFAULT_SEED_DIR = REPO_ROOT / "data" / "seed"
MANIFEST_NAME = "SEED_MANIFEST.json"

OK = "OK"
EOL_ONLY = "EOL_ONLY"
MISMATCH = "MISMATCH"
MISSING = "MISSING"


@dataclass(frozen=True)
class SeedCheck:
    tenant: str
    path: Path
    state: str
    size: int
    sha256: str | None
    expected_sha256: str
    eol: str
    repaired: bool = False

    @property
    def ok(self) -> bool:
        return self.state == OK


def sha256_hex(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().lower()


def to_lf(raw: bytes) -> bytes:
    return raw.replace(b"\r\n", b"\n")


def to_crlf(raw: bytes) -> bytes:
    return to_lf(raw).replace(b"\n", b"\r\n")


def eol_style(raw: bytes) -> str:
    """Classify a file as LF, CRLF, MIXED, or EMPTY by its newline bytes."""
    if not raw:
        return "EMPTY"
    crlf = raw.count(b"\r\n")
    bare_lf = raw.count(b"\n") - crlf
    bare_cr = raw.count(b"\r") - crlf
    if bare_cr or (crlf and bare_lf):
        return "MIXED"
    return "CRLF" if crlf else "LF"


def manifest_variant(raw: bytes, expected_sha256: str) -> bytes | None:
    """Return the LF/CRLF variant of ``raw`` that matches the manifest, if any."""
    for candidate in (to_lf(raw), to_crlf(raw)):
        if sha256_hex(candidate) == expected_sha256:
            return candidate
    return None


def check_seed(path: Path, tenant: str, expected_sha256: str) -> SeedCheck:
    expected = expected_sha256.strip().lower()
    try:
        raw = path.read_bytes()
    except OSError:
        return SeedCheck(tenant, path, MISSING, 0, None, expected, "MISSING")
    actual = sha256_hex(raw)
    state = OK
    if actual != expected:
        state = EOL_ONLY if manifest_variant(raw, expected) is not None else MISMATCH
    return SeedCheck(tenant, path, state, len(raw), actual, expected, eol_style(raw))


def repair_seed(check: SeedCheck) -> SeedCheck:
    """Rewrite an EOL-only copy with the manifest bytes; never touch real drift."""
    if check.state != EOL_ONLY:
        return check
    canonical = manifest_variant(check.path.read_bytes(), check.expected_sha256)
    if canonical is None:  # pragma: no cover - state already proved the variant exists
        return check
    tmp = check.path.with_name(check.path.name + ".eol-tmp")
    tmp.write_bytes(canonical)
    os.replace(tmp, check.path)
    fixed = check_seed(check.path, check.tenant, check.expected_sha256)
    return replace(fixed, repaired=fixed.state == OK)


def describe(check: SeedCheck) -> str:
    if check.state == MISSING:
        return f"{check.tenant}: {MISSING:<9} {check.path}"
    actual = (check.sha256 or "-")[:12]
    line = f"{check.tenant}: {check.state:<9} {check.size:>7,} B  {check.eol:<5} sha256={actual}..."
    details: list[str] = []
    if check.state != OK:
        details.append(f"manifest={check.expected_sha256[:12]}...")
    if check.repaired:
        details.append("(rewritten to LF)")
    return f"{line}  {'  '.join(details)}" if details else line


def load_expected(manifest_path: Path) -> dict[str, str]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    tenants = manifest["tenants"]
    expected = {str(tenant): str(tenants[tenant]["sql_sha256"]) for tenant in tenants}
    if not expected:
        raise ValueError("manifest lists no tenants")
    return expected


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--seed-dir", type=Path, default=DEFAULT_SEED_DIR)
    parser.add_argument(
        "--fix",
        action="store_true",
        help="rewrite EOL-only drift with the manifest bytes (never touches real drift)",
    )
    parser.add_argument("--json", action="store_true", help="print a JSON report")
    args = parser.parse_args(argv)

    seed_dir = args.seed_dir.expanduser().resolve()
    manifest_path = seed_dir / MANIFEST_NAME
    try:
        expected = load_expected(manifest_path)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"cannot use {manifest_path}: {exc}", file=sys.stderr)
        return 2

    checks = [
        check_seed(seed_dir / f"{tenant}_seed.sql", tenant, sha256)
        for tenant, sha256 in sorted(expected.items())
    ]
    if args.fix:
        checks = [repair_seed(check) if check.state == EOL_ONLY else check for check in checks]

    all_ok = all(check.ok for check in checks)
    if args.json:
        print(
            json.dumps(
                {
                    "seed_dir": str(seed_dir),
                    "manifest": str(manifest_path),
                    "ok": all_ok,
                    "checks": [
                        {
                            "tenant": check.tenant,
                            "state": check.state,
                            "path": str(check.path),
                            "size": check.size,
                            "sha256": check.sha256,
                            "expected_sha256": check.expected_sha256,
                            "eol": check.eol,
                            "repaired": check.repaired,
                        }
                        for check in checks
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0 if all_ok else 1

    for check in checks:
        print(describe(check))
    print(
        f"{sum(check.ok for check in checks)}/{len(checks)} seed files match {manifest_path.name}"
    )
    if any(check.state == EOL_ONLY for check in checks):
        print("EOL-only drift: rows are unchanged, only line endings differ.")
        print("Re-run with --fix to write the manifest bytes back.")
    for check in checks:
        if check.state in (MISMATCH, MISSING):
            print(f"{check.tenant}: this is not a line-ending problem; restore the file from git.")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
