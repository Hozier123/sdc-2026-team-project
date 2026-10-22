"""Import only the public machine contract and synthetic fixtures; leave Gate 0 untouched."""
from pathlib import Path
import hashlib
import json
import sys
import yaml

root = Path(__file__).resolve().parents[1]
source = Path(sys.argv[1]).resolve()
raw = (source / "contracts/openapi.yaml").read_bytes()
schema = yaml.safe_load(raw)
target = root / "contracts"
target.mkdir(exist_ok=True)
(target / "gate0.openapi.json").write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n")
names = ["save_lines_ready", "save_lines_insufficient_stock_200", "approve_200",
         "approval_detail", "decide_rejected", "warehouse_delivery_order", "customers_list",
         "already_approved_409", "save_lines_target_required", "save_lines_price_mismatch_422",
         "error_catalog"]
hashes = {}
for name in names:
    data = (source / f"contracts/fixtures/{name}.json").read_bytes()
    (root / f"tests/fixtures/{name}.json").write_bytes(data)
    hashes[name + ".json"] = hashlib.sha256(data).hexdigest()
(target / "provenance.json").write_text(json.dumps({
    "contract_version": schema["info"]["version"],
    "source": "Gate 0 canonical machine contract (read-only import)",
    "source_yaml_sha256": hashlib.sha256(raw).hexdigest(),
    "snapshot_sha256": hashlib.sha256((target / "gate0.openapi.json").read_bytes()).hexdigest(),
    "fixtures_sha256": hashes,
    "note": "Only machine schemas and synthetic responses are imported; no source documents or credentials."
}, ensure_ascii=False, indent=2) + "\n")
print(f"Imported {len(schema['paths'])} paths and {len(names)} synthetic fixtures.")
