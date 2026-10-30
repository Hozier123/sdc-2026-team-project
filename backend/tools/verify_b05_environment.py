"""Synthetic environment acceptance only: no participants, timing study or shared demo access."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from uuid import uuid4

from tools import b05_environment as env
from tools.run_workflow import Driver


def driver(path, state, name, route, folder, *, resume=False):
    if resume:
        case = env.read(folder / "case.json")
    else:
        case = env.read(env.ROOT / f"docs/ops/b04-cases/{route}.json")
        case["case_id"] = "B05-ENV-TECHNICAL-" + name.upper()
        case["allowed_ai_modes"] = ["FALLBACK"]
        case["token_env"] = {role: f"B05_ENV_{name.upper()}_{role}" for role in env.ROLES}
        if route == "owner-approve":
            case["save"]["lines"][0].update(
                save_to_alias_cache=True,
                alias_scope="CUSTOMER",
                override_reason="B05 environment synthetic technical fixture",
            )
    for role, token in env.private(path)[name]["tokens"].items():
        os.environ[case["token_env"][role]] = token
    return Driver(
        case,
        env.api_base(state, name) + "/api/v1",
        folder.parent,
        run_id=folder.name,
        environment=state["env_id"],
        resume=resume,
    )


def stock(snapshot):
    return {r["product_id"]: r["available_qty"] for r in snapshot["tables"]["inventory"]}


def verify(path, state):
    env.require_sources(state)
    for name in env.SIDES:
        env.start_side(path, state, name)
    for name in env.SIDES:
        env.require(
            env.snapshot(path, state, name) == state["baseline"][name],
            "technical verification requires a fresh environment; never replay a used fixture",
        )
    out = path.parent / "technical-verification" / ("check-" + uuid4().hex[:12])
    out.mkdir(parents=True)
    checks = {}
    checks["identities_roles_cors"] = env.check(path, state)["status"] == "PASS"
    protected_folder = path.parent / "checkpoints" / "protected-driver"
    protected = driver(path, state, "protected", "owner-approve", protected_folder)
    try:
        paused = protected.execute(until="saved")
        env.require(paused["status"] == "CHECKPOINT", "protected save did not pause")
        saved = protected.state["steps"]["save"]["body"]
        response = protected.call(
            "approve",
            "CLERK",
            "POST",
            "/orders/" + saved["draft_id"] + "/approve",
            {"expected_version": saved["version"]},
            expected=(202,),
        )
        protected.state.update(status="CHECKPOINT", approval_id=response["body"]["approval_id"])
        protected.checkpoint()
        env.save(
            protected_folder / "next-step.json",
            {
                "next_execution": "owner_review_then_owner_decide",
                "approval_id": response["body"]["approval_id"],
                "draft_version": saved["version"],
            },
        )
    finally:
        protected.client.close()
    before = env.snapshot(path, state, "protected")
    checks["nonempty_protected_pending_alias_checkpoint"] = (
        len(before["tables"]["alias_cache"]) == 3
        and len(before["tables"]["approval_requests"]) == 1
        and before["tables"]["approval_requests"][0]["status"] == "PENDING"
        and bool(before["checkpoints"])
    )
    firstuse = driver(path, state, "firstuse", "direct", out / "firstuse-driver")
    try:
        result = firstuse.execute()
    finally:
        firstuse.client.close()
    checks["firstuse_synthetic_do_created"] = result["status"] == "API_PASS"
    written = env.snapshot(path, state, "firstuse")
    checks["firstuse_write_is_real"] = len(written["tables"]["delivery_orders"]) == 1
    dry = env.reset_firstuse(path, state, apply=False)
    checks["dry_run_preserves_both_sides"] = dry["status"] == "PASS"
    reset = env.reset_firstuse(path, state, apply=True)
    checks["firstuse_reset_and_scoped_api_restart"] = reset["status"] == "PASS"
    after_reset = env.snapshot(path, state, "protected")
    checks["all_12_protected_tables_and_checkpoint_bytes_unchanged"] = before == after_reset
    checks["firstuse_exact_initial_state_restored"] = (
        env.snapshot(path, state, "firstuse") == state["baseline"]["firstuse"]
    )
    env.save(out / "protected-before.json", before)
    env.save(out / "protected-after-reset.json", after_reset)
    resumed = driver(path, state, "protected", "owner-approve", protected_folder, resume=True)
    try:
        completed = resumed.execute()
    finally:
        resumed.client.close()
    final = env.snapshot(path, state, "protected")
    delta = {
        key: stock(final)[key] - qty
        for key, qty in stock(before).items()
        if stock(final)[key] != qty
    }
    checks["original_checkpoint_resume_pass"] = completed["status"] == "API_PASS"
    checks["resume_stock_only_expected_minus_2"] = delta == {"SKU_GULA_1KG": -2}
    checks["resume_one_new_do_and_unchanged_aliases"] = (
        len(final["tables"]["delivery_orders"]) == 1
        and final["tables"]["alias_cache"] == before["tables"]["alias_cache"]
    )
    env.save(out / "protected-after-resume.json", final)
    report = {
        "kind": "SYNTHETIC_ENVIRONMENT_DELIVERY_ACCEPTANCE",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "environment_id": state["env_id"],
        "checks": checks,
        "participant_trials": "NOT_RUN",
        "participant_count": 0,
        "included_in_participant_denominator": False,
        "measured_timing_benefit": None,
        "reset_evidence": reset["report"],
        "stock_delta": delta,
        "source_files": state["source_files"],
        "recorded_at": env.now(),
    }
    env.save(out / "result.json", report)
    env.save(path.parent / "technical-acceptance.json", report)
    env.require(all(checks.values()), "synthetic environment acceptance failed; preserve evidence")
    return {
        "status": report["status"],
        "checks_passed": sum(checks.values()),
        "checks_total": len(checks),
        "report": str(out / "result.json"),
        "participant_trials": "NOT_RUN",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path)
    args = parser.parse_args(argv)
    try:
        path, state = env.load(args.state)
        with env.operation(path):
            print(json.dumps(verify(path, state)))
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "FAILED",
                    "error_type": type(exc).__name__,
                    "reason": str(exc)
                    if isinstance(exc, env.EnvironmentError)
                    else "details suppressed; inspect owned technical evidence",
                }
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
