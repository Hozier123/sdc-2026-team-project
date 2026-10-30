"""Mis-target, credential and process-ownership controls for the B05 environment kit."""

import copy
import hashlib
import json

import pytest

from tools import b05_environment as env


@pytest.fixture
def owned(tmp_path, monkeypatch):
    monkeypatch.setattr(env, "ROOT", tmp_path)
    identifier = "b05-env-0123456789ab"
    folder = env.home() / identifier
    folder.mkdir(parents=True)
    path = folder / "environment.json"
    state = {
        "schema": "b05-owned-environment-v1",
        "env_id": identifier,
        "nonce": "owned",
        "postgres_bin": "/owned/pg",
        "frontend_port": 24000,
        "sides": {},
        "status": "READY",
        "kind": "TECHNICAL_ENVIRONMENT_DELIVERY",
    }
    for i, name in enumerate(env.SIDES):
        state["sides"][name] = {
            "database": f"kiraorder_demo_b05_{name}_0123456789ab",
            "template": f"kiraorder_b05_{name}_seed_0123456789ab",
            "pg_port": 24001 + i * 2,
            "api_port": 24002 + i * 2,
            "identity": {"system_identifier": str(i)},
            "seed_version": "pinned",
            "seed_sha256": "a" * 64,
        }
    env.save(path, state)
    env.save(
        folder / "owner.json",
        {
            "env_id": identifier,
            "nonce": "owned",
            "postgres_bin": state["postgres_bin"],
            "bindings": {n: env.side_binding(s) for n, s in state["sides"].items()},
        },
    )
    return path, state


def test_owned_profile_loads(owned):
    path, expected = owned
    assert env.load(path)[1] == expected


@pytest.mark.parametrize(
    "key,value",
    [
        ("database", "existing_shared_demo"),
        ("template", "existing_shared_seed"),
        ("pg_port", 5432),
        ("api_port", 8000),
        ("identity", {"system_identifier": "foreign"}),
        ("seed_version", "different"),
        ("seed_sha256", "b" * 64),
    ],
)
def test_tampered_target_binding_rejected_before_any_connection(owned, monkeypatch, key, value):
    path, state = owned
    state["sides"]["firstuse"][key] = value
    env.save(path, state)
    monkeypatch.setattr(env.psycopg, "connect", lambda *a, **k: pytest.fail("must not connect"))
    with pytest.raises(env.EnvironmentError):
        env.load(path)


def test_external_profile_path_is_rejected(owned):
    path, _ = owned
    with pytest.raises(env.EnvironmentError, match="state must"):
        env.load(path.parent.parent.parent / "foreign.json")


def test_changed_owner_nonce_is_rejected(owned):
    path, _ = owned
    owner = env.read(path.parent / "owner.json")
    owner["nonce"] = "other"
    env.save(path.parent / "owner.json", owner)
    with pytest.raises(env.EnvironmentError, match="ownership"):
        env.load(path)


def test_shared_ports_are_rejected_even_if_owner_was_copied(owned):
    path, state = owned
    state["sides"]["firstuse"]["pg_port"] = state["sides"]["protected"]["pg_port"]
    owner = env.read(path.parent / "owner.json")
    owner["bindings"]["firstuse"] = env.side_binding(state["sides"]["firstuse"])
    env.save(path, state)
    env.save(path.parent / "owner.json", owner)
    with pytest.raises(env.EnvironmentError, match="ports must differ"):
        env.load(path)


def test_inherited_database_and_remote_ai_settings_are_removed(monkeypatch):
    for key in (
        "DATABASE_URL",
        "RESET_ADMIN_DATABASE_URL",
        "RUNPOD_API_KEY",
        "AI_API_KEY",
        "KIRAORDER_AI_FORCE_MODE",
        "PGHOST",
        "PGPASSWORD",
        "MODEL_NAME",
    ):
        monkeypatch.setenv(key, "must-not-inherit")
    cleaned = env.child_env()
    assert all(value != "must-not-inherit" for value in cleaned.values())
    assert cleaned["AI_PROVIDER"] == "stub"


def test_sessions_are_replaced_exactly_and_canonical_seed_is_not_modified():
    seed = (env.ROOT / "data/seed/T1_seed.sql").read_text("utf-8")
    tokens = {role: "unique-" + role for role in env.ROLES}
    replaced = env.replace_session_hashes(seed, tokens)
    for token in tokens.values():
        assert hashlib.sha256(token.encode()).hexdigest() in replaced
        assert token not in replaced
    assert replaced != seed
    with pytest.raises(env.EnvironmentError):
        env.replace_session_hashes("no user seed here", tokens)


def test_reset_command_has_no_external_target_or_url_flags(owned):
    for flag in ("--target", "--admin-url", "--api-base", "--allow-any-target", "--side"):
        with pytest.raises(SystemExit) as exc:
            env.main(["reset-firstuse", flag, "shared-demo"])
        assert exc.value.code == 2


def test_reset_arguments_always_target_generated_firstuse(owned, monkeypatch):
    path, state = owned
    monkeypatch.setattr(
        env, "private", lambda p: {n: {"postgres_password": "private-secret"} for n in env.SIDES}
    )
    args = env.reset_args(path, state, path.parent / "evidence", "--apply")
    assert args[args.index("--target") + 1] == state["sides"]["firstuse"]["database"]
    assert args[args.index("--template") + 1] == state["sides"]["firstuse"]["template"]
    assert state["sides"]["protected"]["database"] not in args


def test_source_drift_stops_start_before_pg_control(owned, monkeypatch):
    path, state = owned
    state["source_files"] = {"old.py": "a"}
    monkeypatch.setattr(env, "sources", lambda: {"new.py": "b"})
    monkeypatch.setattr(env, "pg_control", lambda *a, **k: pytest.fail("must not start"))
    with pytest.raises(env.EnvironmentError, match="source binding"):
        env.start_side(path, state, "firstuse")


def test_wrong_protected_identity_stops_reset_before_any_mutation(owned, monkeypatch):
    path, state = owned
    monkeypatch.setattr(env, "require_sources", lambda s: None)

    def check_identity(p, s, name):
        if name == "protected":
            raise env.EnvironmentError("database identity mismatch")

    monkeypatch.setattr(env, "identity", check_identity)
    monkeypatch.setattr(env, "reset_main", lambda *a: pytest.fail("must not reset"))
    monkeypatch.setattr(env, "stop_api", lambda *a: pytest.fail("must not signal"))
    with pytest.raises(env.EnvironmentError, match="identity mismatch"):
        env.reset_firstuse(path, state, apply=True)


def test_foreign_pid_is_never_signalled(owned, monkeypatch):
    path, state = owned
    env.save(path.parent / "firstuse/api-process.json", {"pid": 9001, "launcher_pid": 9001})
    monkeypatch.setattr(env, "process_command", lambda pid: (1, "unrelated application"))
    monkeypatch.setattr(env.os, "kill", lambda *a: pytest.fail("must not signal"))
    with pytest.raises(env.EnvironmentError, match="not owned"):
        env.stop_api(path, state, "firstuse")


def test_operation_lock_rejects_overlap_and_is_released(owned):
    path, _ = owned
    with env.operation(path), pytest.raises(env.EnvironmentError, match="another B05 operation"):
        with env.operation(path):
            pytest.fail("must not acquire overlapping operation")
    assert not (path.parent / "operation.lock").exists()


def test_foreign_frontend_pid_is_never_signalled(owned, monkeypatch):
    path, _ = owned
    env.save(path.parent / "frontend-process.json", {"pid": 9001})
    monkeypatch.setattr(env, "process_command", lambda pid: (1, "node shared-demo.js"))
    monkeypatch.setattr(env.os, "kill", lambda *a: pytest.fail("must not signal"))
    with pytest.raises(env.EnvironmentError, match="unowned frontend"):
        env.stop_frontend(path)


def test_public_manifest_never_contains_private_tokens_or_passwords(owned, monkeypatch):
    path, state = owned
    monkeypatch.setattr(
        env, "private", lambda p: pytest.fail("public output must not read secrets")
    )
    value = env.public_manifest(path, state)
    assert value["actual_participant_trials"] == "NOT_RUN"
    assert "postgresql://" not in json.dumps(value)
    assert set(value["sides"]) == set(env.SIDES)


def test_owned_profile_is_not_mutated_by_loading(owned):
    path, state = owned
    before = copy.deepcopy(state)
    env.load(path)
    assert env.read(path) == before
