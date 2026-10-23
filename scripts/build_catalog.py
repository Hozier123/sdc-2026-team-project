"""KiraOrder Product Family Catalog Builder.

Dynamically extracts product family catalog mappings from canonical tenant seed files:
- tenant_sinaran.json (T1: Sinaran Food Supply)
- tenant_kilat.json   (T2: Kilat Cleaning Supplies)

Produces a clean mapping of:
    Dict[str, List[str]] -> {family_id: [alias_1, alias_2, ...]}

Derived strictly from product_families and family_aliases without hardcoding family lists.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUTS_DIR = PROJECT_ROOT / "ai-eval-inputs-2026-10-23(1)"


def _find_inputs_dir(override: Optional[Path] = None) -> Path:
    """Resolve directory containing tenant_sinaran.json and tenant_kilat.json."""
    if override and override.is_dir():
        return override

    candidates = [
        DEFAULT_INPUTS_DIR,
        PROJECT_ROOT / "ai-eval-inputs-2026-10-23",
        PROJECT_ROOT.parent / "ai-eval-inputs-2026-10-23(1)",
        PROJECT_ROOT / "data",
    ]
    for cand in candidates:
        if (cand / "tenant_sinaran.json").is_file():
            return cand

    raise FileNotFoundError(
        f"Could not locate canonical tenant files in candidates: {candidates}. "
        "Please provide --inputs-dir."
    )


def build_catalog(
    tenant_id: str = "T1",
    inputs_dir: Optional[Path] = None,
) -> Dict[str, List[str]]:
    """Build dynamic family-to-aliases catalog for a given tenant.

    Args:
        tenant_id: Tenant identifier ("T1" or "T2").
        inputs_dir: Directory containing tenant_sinaran.json / tenant_kilat.json.

    Returns:
        Dict mapping family_id to a deduplicated list of aliases (including family_name).

    Raises:
        ValueError: If tenant_id is unsupported.
        FileNotFoundError: If the tenant seed file does not exist.
    """
    tenant_upper = tenant_id.strip().upper()
    resolved_inputs = _find_inputs_dir(inputs_dir)

    tenant_files: Dict[str, str] = {
        "T1": "tenant_sinaran.json",
        "T2": "tenant_kilat.json",
    }
    if tenant_upper not in tenant_files:
        raise ValueError(f"Unsupported tenant_id '{tenant_id}'. Expected 'T1' or 'T2'.")

    target_file = resolved_inputs / tenant_files[tenant_upper]
    if not target_file.is_file():
        raise FileNotFoundError(f"Tenant JSON file not found: {target_file}")

    data: Dict[str, Any] = json.loads(target_file.read_text(encoding="utf-8"))

    catalog: Dict[str, List[str]] = {}

    # 1. Initialize from product_families
    product_families: Sequence[Dict[str, Any]] = data.get("product_families", [])
    for pf in product_families:
        fid = pf.get("family_id")
        if not fid:
            continue
        aliases: List[str] = []
        name = pf.get("family_name")
        if name and isinstance(name, str) and name.strip():
            aliases.append(name.strip())
        catalog[fid] = aliases

    # 2. Append from family_aliases
    family_aliases: Sequence[Dict[str, Any]] = data.get("family_aliases", [])
    for fa in family_aliases:
        fid = fa.get("family_id")
        if not fid:
            continue
        if fid not in catalog:
            catalog[fid] = []

        seen_lower = {a.lower() for a in catalog[fid]}

        # phrase (original display/match string)
        phrase = fa.get("phrase")
        if phrase and isinstance(phrase, str) and phrase.strip():
            phrase_clean = phrase.strip()
            if phrase_clean.lower() not in seen_lower:
                catalog[fid].append(phrase_clean)
                seen_lower.add(phrase_clean.lower())

        # phrase_norm (normalized lower match string)
        phrase_norm = fa.get("phrase_norm")
        if phrase_norm and isinstance(phrase_norm, str) and phrase_norm.strip():
            norm_clean = phrase_norm.strip()
            if norm_clean.lower() not in seen_lower:
                catalog[fid].append(norm_clean)
                seen_lower.add(norm_clean.lower())

    return catalog


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build product family catalog from canonical tenant seed data."
    )
    parser.add_argument(
        "--tenant",
        type=str,
        default="T1",
        choices=["T1", "T2"],
        help="Target tenant ID (T1=Sinaran Food Supply, T2=Kilat Cleaning Supplies). Default: T1.",
    )
    parser.add_argument(
        "--inputs-dir",
        type=Path,
        default=None,
        help="Path to directory containing tenant_sinaran.json and tenant_kilat.json.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to save catalog JSON file. If omitted, outputs to stdout.",
    )
    args = parser.parse_args()

    try:
        catalog = build_catalog(tenant_id=args.tenant, inputs_dir=args.inputs_dir)
    except Exception as err:
        print(f"Error building catalog: {err}", file=sys.stderr)
        sys.exit(1)

    formatted_json = json.dumps(catalog, ensure_ascii=False, indent=2)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(formatted_json, encoding="utf-8")
        print(f"Catalog for {args.tenant} saved to {args.output}")
    else:
        # Stream directly to stdout
        sys.stdout.write(formatted_json + "\n")


if __name__ == "__main__":
    main()
