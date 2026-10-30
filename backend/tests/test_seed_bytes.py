"""The frozen seed bytes are load-bearing: ``app.seed`` hashes them before INSERT."""

import json
import shutil
from pathlib import Path

from app.config import REPO_ROOT
from tools.check_seed_bytes import (
    MISSING,
    OK,
    check_seed,
    main,
    sha256_hex,
    to_crlf,
)

SEED_DIR = REPO_ROOT / "data" / "seed"
MANIFEST = json.loads((SEED_DIR / "SEED_MANIFEST.json").read_text(encoding="utf-8"))
T2_CRLF_SHA256 = "8eb158bda188346f2fe3477867f9d0ad4f4e3f26fdaff9617a2d2b5bc05904bd"


def _tmp_seed_dir(tmp_path: Path) -> Path:
    seed_dir = tmp_path / "seed"
    seed_dir.mkdir()
    shutil.copyfile(SEED_DIR / "SEED_MANIFEST.json", seed_dir / "SEED_MANIFEST.json")
    for tenant in MANIFEST["tenants"]:
        shutil.copyfile(SEED_DIR / f"{tenant}_seed.sql", seed_dir / f"{tenant}_seed.sql")
    return seed_dir


def test_repository_seed_bytes_match_manifest() -> None:
    for tenant, meta in MANIFEST["tenants"].items():
        check = check_seed(SEED_DIR / f"{tenant}_seed.sql", tenant, meta["sql_sha256"])
        assert check.state == OK, check


def test_crlf_twin_still_describes_the_same_rows() -> None:
    raw = (SEED_DIR / "T2_seed.sql").read_bytes()
    twin = to_crlf(raw)
    assert (len(raw), len(twin)) == (27611, 27766)
    assert sha256_hex(twin) == T2_CRLF_SHA256


def test_crlf_copy_is_flagged_then_repaired(tmp_path: Path, capsys) -> None:
    seed_dir = _tmp_seed_dir(tmp_path)
    t2 = seed_dir / "T2_seed.sql"
    canonical = t2.read_bytes()
    t2.write_bytes(to_crlf(canonical))

    assert main(["--seed-dir", str(seed_dir)]) == 1
    assert "T2: EOL_ONLY" in capsys.readouterr().out
    assert t2.read_bytes() != canonical  # a plain check never rewrites the file

    assert main(["--seed-dir", str(seed_dir), "--fix"]) == 0
    assert "(rewritten to LF)" in capsys.readouterr().out
    assert t2.read_bytes() == canonical

    assert main(["--seed-dir", str(seed_dir), "--fix"]) == 0


def test_content_drift_is_never_silently_fixed(tmp_path: Path, capsys) -> None:
    seed_dir = _tmp_seed_dir(tmp_path)
    t2 = seed_dir / "T2_seed.sql"
    tampered = t2.read_bytes() + b"-- local edit\n"
    t2.write_bytes(tampered)

    assert main(["--seed-dir", str(seed_dir), "--fix"]) == 1
    out = capsys.readouterr().out
    assert "T2: MISMATCH" in out
    assert "not a line-ending problem" in out
    assert t2.read_bytes() == tampered


def test_missing_seed_is_reported(tmp_path: Path, capsys) -> None:
    seed_dir = _tmp_seed_dir(tmp_path)
    (seed_dir / "T1_seed.sql").unlink()

    assert main(["--seed-dir", str(seed_dir)]) == 1
    out = capsys.readouterr().out
    assert f"T1: {MISSING}" in out
    assert "T2: OK" in out
