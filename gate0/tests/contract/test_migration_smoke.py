import json
import os
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).parents[2]


def test_migration_executes_in_empty_pglite_postgresql_runtime():
    node = os.environ.get("GATE0_NODE") or shutil.which("node")
    assert node, "Node.js is required; set GATE0_NODE or add node to PATH"
    module = os.environ.get("GATE0_PGLITE_MODULE")
    assert module or (ROOT / "node_modules" / "@electric-sql" / "pglite").is_dir(), (
        "PGlite 0.5.10 is required; run npm install or set GATE0_PGLITE_MODULE"
    )
    result = subprocess.run(
        [node, str(ROOT / "scripts" / "verify_migration_pglite.cjs")],
        cwd=ROOT,
        env=os.environ.copy(),
        check=True,
        capture_output=True,
        text=True,
    )
    summary = json.loads(result.stdout)
    assert summary["pglite_version"] == "0.5.10"
    assert summary["table_count"] == 18
    assert summary["approval_guard_events"] == ["DELETE", "UPDATE"]
