import json
from pathlib import Path


ROOT = Path(__file__).parents[2]


def test_demo_path_is_explicitly_deferred_without_skipping_gate0_checks():
    """Gate 0 contains contracts only; the executable 18-step path starts in P0-A."""
    manifest = json.loads((ROOT / "baseline-manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "GATE0_DRAFT_AWAITING_CROSS_FUNCTIONAL_SIGNOFF"
    assert not (ROOT / "app").exists()
    assert not (ROOT / "src" / "kiraorder").exists()
