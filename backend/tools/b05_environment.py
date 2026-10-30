"""Create and operate fresh, loopback-only B05 environments; never accept an external DSN."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import time
from contextlib import contextmanager, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

import httpx
import psycopg
from psycopg import sql

from app.config import REPO_ROOT, Settings
from tools.reset_demo import main as reset_main

ROOT = REPO_ROOT
SIDES = ("protected", "firstuse")
ROLES = ("CLERK", "OWNER", "WAREHOUSE")
FLAGS = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
TABLES = (
    "inventory",
    "alias_cache",
    "family_aliases",
    "uom_aliases",
    "approval_requests",
    "orders",
    "delivery_orders",
    "audit_logs",
    "draft_versions",
    "inbound_messages",
    "activity_log",
    "field_diffs",
)


class EnvironmentError(RuntimeError):
    """A deliberately credential-free operator error."""


def require(value, message):
    if not value:
        raise EnvironmentError(message)


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text("utf-8"))


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", "utf-8")
    temporary.replace(path)


def home():
    return ROOT / ".tmp" / "b05-environments"


def sources():
    paths = list((ROOT / "backend/app").rglob("*.py"))
    paths += list((ROOT / "gate0").rglob("*.sql"))
    paths += list((ROOT / "frontend/src").rglob("*"))
    paths += [
        ROOT / p
        for p in (
            "backend/tools/b05_environment.py",
            "backend/tools/reset_demo.py",
            "backend/tools/verify_b05_environment.py",
            "backend/tools/run_workflow.py",
            "backend/tools/export_trial_record.py",
            "data/seed/T1_seed.sql",
            "data/seed/SEED_MANIFEST.json",
            "frontend/package.json",
            "frontend/package-lock.json",
        )
    ]
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(paths) if p.is_file()}


def side_binding(side):
    return {
        k: side.get(k)
        for k in (
            "database",
            "template",
            "pg_port",
            "api_port",
            "identity",
            "seed_sha256",
            "seed_version",
        )
    }


def load(path=None):
    path = Path(path or read(home() / "latest.json")["state"]).resolve()
    require(
        path.is_relative_to(home().resolve()) and path.name == "environment.json",
        "state must be a B05 environment.json under this checkout's .tmp/b05-environments",
    )
    state = read(path)
    require(re.fullmatch(r"b05-env-[0-9a-f]{12}", path.parent.name), "invalid B05 directory")
    require(state["env_id"] == path.parent.name, "environment identity mismatch")
    require(state["schema"] == "b05-owned-environment-v1", "invalid environment schema")
    owner = read(path.parent / "owner.json")
    require(
        owner["env_id"] == state["env_id"] and owner["nonce"] == state["nonce"],
        "B05 ownership marker mismatch",
    )
    require(set(state["sides"]) == set(SIDES), "both isolated sides required")
    suffix = state["env_id"].removeprefix("b05-env-")
    ports = [state["frontend_port"]]
    for name in SIDES:
        side = state["sides"][name]
        require(
            side["database"] == f"kiraorder_demo_b05_{name}_{suffix}",
            "database is not this environment's generated target",
        )
        require(
            side["template"] == f"kiraorder_b05_{name}_seed_{suffix}",
            "template is not this environment's generated template",
        )
        require(owner["bindings"][name] == side_binding(side), "pinned side binding changed")
        require(
            (path.parent / name).resolve().is_relative_to(path.parent),
            "side directory escapes owned environment",
        )
        require(
            (path.parent / name / "data").resolve().is_relative_to(path.parent / name),
            "database directory escapes owned side",
        )
        ports += [side["pg_port"], side["api_port"]]
    require(all(type(p) is int and 1024 <= p <= 65535 for p in ports), "invalid ports")
    require(len(set(ports)) == len(ports), "all database/API/frontend ports must differ")
    require(owner["postgres_bin"] == state["postgres_bin"], "PostgreSQL binaries changed")
    return path, state


def require_sources(state):
    require(state["source_files"] == sources(), "source binding changed; create a new environment")
    if state.get("frontend_build"):
        require(
            all(
                sha(ROOT / "frontend/dist" / name) == digest
                for name, digest in state["frontend_build"].items()
            ),
            "frontend build changed; create a new environment",
        )


@contextmanager
def operation(path):
    lock = path.parent / "operation.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise EnvironmentError(
            "another B05 operation owns the lock; inspect it before retrying"
        ) from None
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump({"pid": os.getpid(), "started_at": now()}, handle)
        yield
    finally:
        lock.unlink()


def private(state_path):
    return read(state_path.parent / "credentials.private.json")


def url(path, state, name, database=None):
    side = state["sides"][name]
    password = private(path)[name]["postgres_password"]
    return (
        f"postgresql://b05_admin:{quote(password, safe='')}@127.0.0.1:"
        f"{side['pg_port']}/{database or side['database']}"
    )


def api_base(state, name):
    return f"http://127.0.0.1:{state['sides'][name]['api_port']}"


def binary(state, name):
    return Path(state["postgres_bin"]) / (name + (".exe" if os.name == "nt" else ""))


def pg_control(path, state, name, action, initialize=False):
    folder = path.parent / name
    data = folder / "data"
    if initialize:
        require(not data.exists(), "refuse to overwrite PostgreSQL data")
        command = [
            str(binary(state, "initdb")),
            "-D",
            str(data),
            "-U",
            "b05_admin",
            "--auth=scram-sha-256",
            "--encoding=UTF8",
            "--locale=C",
            "--pwfile",
            str(folder / "postgres-password.private.txt"),
        ]
        result = subprocess.run(command, capture_output=True, creationflags=FLAGS, timeout=60)
        (folder / "initdb.log").write_bytes(result.stdout + result.stderr)
        require(result.returncode == 0, "initdb failed; inspect the owned private initdb.log")
    status = subprocess.run(
        [str(binary(state, "pg_ctl")), "-D", str(data), "status"],
        capture_output=True,
        creationflags=FLAGS,
        timeout=15,
    )
    if (action == "start" and status.returncode == 0) or (
        action == "stop" and status.returncode != 0
    ):
        return
    args = [str(binary(state, "pg_ctl")), "-D", str(data), "-w"]
    if action == "start":
        args += [
            "-l",
            str(folder / "postgres.log"),
            "-o",
            f"-h 127.0.0.1 -p {state['sides'][name]['pg_port']}",
            "start",
        ]
    else:
        args += ["-m", "fast", "stop"]
    with (folder / "control.log").open("ab") as log:
        result = subprocess.run(
            args, stdout=log, stderr=subprocess.STDOUT, creationflags=FLAGS, timeout=45
        )
    require(result.returncode == 0, f"owned {name} PostgreSQL {action} failed")


def identity(path, state, name, verify=True):
    with psycopg.connect(url(path, state, name), connect_timeout=3) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        row = conn.execute(
            "SELECT current_database(),inet_server_port(),"
            "(pg_control_system()).system_identifier::text,"
            "current_setting('data_directory')"
        ).fetchone()
    actual = {"database": row[0], "port": row[1], "system_identifier": row[2]}
    require(
        Path(row[3]).resolve() == (path.parent / name / "data").resolve(),
        "connected PostgreSQL is not this owned data directory",
    )
    if verify:
        require(actual == state["sides"][name]["identity"], "database identity mismatch")
    return actual


def child_env():
    env = os.environ.copy()
    for key in list(env):
        if key.upper().startswith(("AI_", "RUNPOD_", "KIRAORDER_AI_", "PG")) or key in {
            "DATABASE_URL",
            "RESET_ADMIN_DATABASE_URL",
            "MODEL_NAME",
            "LLM_TIMEOUT_S",
        }:
            env.pop(key, None)
    env.update(
        AI_PROVIDER="stub",
        PYTHONUTF8="1",
        PYTHONIOENCODING="utf-8",
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONPATH=str(ROOT / "backend"),
    )
    return env


def process_command(pid):
    if os.name == "nt":
        command = (
            f"$p=Get-CimInstance Win32_Process -Filter 'ProcessId = {int(pid)}'; "
            "if($null -ne $p){$p|Select-Object ParentProcessId,CommandLine|"
            "ConvertTo-Json -Compress}"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            creationflags=FLAGS,
            timeout=20,
        )
        require(result.returncode == 0, "cannot check process ownership")
        if not result.stdout.strip():
            return None
        info = json.loads(result.stdout)
        command_line = info["CommandLine"] or ""
        parent = info["ParentProcessId"]
    else:
        proc = Path("/proc") / str(pid)
        if not proc.exists():
            return None
        command_line = (proc / "cmdline").read_bytes().replace(b"\0", b" ").decode()
        parent = int((proc / "stat").read_text().split()[3])
    return parent, command_line


def owned_process(pid, path, side):
    info = process_command(pid)
    if info is None:
        return None
    parent, command_line = info
    require(
        "tools.b05_environment" in command_line
        and str(path) in command_line
        and "_serve" in command_line
        and f"--side {side}" in command_line,
        "refuse to signal a process not owned by this B05 environment",
    )
    return parent


def stop_frontend(path):
    marker = path.parent / "frontend-process.json"
    if marker.exists():
        pid = read(marker)["pid"]
        info = process_command(pid)
        if info is not None:
            require(
                str(path.parent / "frontend.cjs") in info[1],
                "refuse to signal an unowned frontend process",
            )
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.3)
        marker.unlink()


def start_frontend(path, state):
    require_sources(state)
    vite = ROOT / "frontend/node_modules/vite/bin/vite.js"
    require(
        vite.is_file() and (ROOT / "frontend/dist/index.html").is_file(),
        "build this checkout's frontend first: npm ci, then npm run build",
    )
    require(shutil.which("node") is not None, "Node.js is required for the frontend")
    marker = path.parent / "frontend-process.json"
    require(not marker.exists(), "frontend marker exists; stop this environment before restarting")
    state["frontend_build"] = {
        p.relative_to(ROOT / "frontend/dist").as_posix(): sha(p)
        for p in sorted((ROOT / "frontend/dist").rglob("*"))
        if p.is_file()
    }
    save(path, state)
    script = path.parent / "frontend.cjs"
    args = [
        str(vite),
        "preview",
        "--host",
        "127.0.0.1",
        "--port",
        str(state["frontend_port"]),
        "--strictPort",
    ]
    script.write_text(
        "process.chdir(" + json.dumps(str(ROOT / "frontend")) + ");\n"
        "process.argv=[process.execPath,..." + json.dumps(args) + "];\n"
        "import(require('url').pathToFileURL(" + json.dumps(str(vite)) + ").href);\n",
        "utf-8",
    )
    with (path.parent / "frontend.log").open("ab") as log:
        process = subprocess.Popen(
            [shutil.which("node"), str(script)],
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=FLAGS,
            env=child_env(),
        )
    save(marker, {"pid": process.pid})
    try:
        with httpx.Client(timeout=2, trust_env=False) as client:
            for _ in range(50):
                require(process.poll() is None, "owned frontend exited; inspect frontend.log")
                try:
                    response = client.get(f"http://127.0.0.1:{state['frontend_port']}/")
                    if response.status_code == 200:
                        require(
                            sha(ROOT / "frontend/dist/index.html")
                            == hashlib.sha256(response.content).hexdigest(),
                            "wrong frontend server",
                        )
                        return
                except httpx.HTTPError:
                    pass
                time.sleep(0.2)
        raise EnvironmentError("frontend startup timed out")
    except Exception:
        stop_frontend(path)
        raise


def api_identity(path, state, name):
    with httpx.Client(timeout=3, trust_env=False) as client:
        response = client.get(api_base(state, name) + "/__b05_identity")
        response.raise_for_status()
        value = response.json()
    require(
        value["environment_id"] == state["env_id"]
        and value["side"] == name
        and value["database"] == state["sides"][name]["identity"],
        "API target mismatch",
    )
    return value


def stop_api(path, state, name):
    marker = path.parent / name / "api-process.json"
    if not marker.exists():
        return
    info = read(marker)
    for pid in dict.fromkeys((info["pid"], info["launcher_pid"])):
        if owned_process(pid, path, name) is not None:
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.3)
    marker.unlink()


def start_side(path, state, name):
    require_sources(state)
    require(state["status"] == "READY", "environment is not ready")
    pg_control(path, state, name, "start")
    identity(path, state, name)
    marker = path.parent / name / "api-process.json"
    if marker.exists():
        info = read(marker)
        if owned_process(info["pid"], path, name) is not None:
            api_identity(path, state, name)
            return
        marker.unlink()
    with (marker.parent / "api.log").open("ab") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "tools.b05_environment",
                "--state",
                str(path),
                "_serve",
                "--side",
                name,
            ],
            cwd=ROOT / "backend",
            env=child_env(),
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=FLAGS,
        )
    save(marker, {"pid": process.pid, "launcher_pid": process.pid})
    try:
        for _ in range(100):
            require(process.poll() is None, "owned API exited; inspect its private api.log")
            try:
                value = api_identity(path, state, name)
                parent = owned_process(value["pid"], path, name)
                require(
                    value["pid"] == process.pid or parent == process.pid,
                    "API is not the launched interpreter or its child",
                )
                save(marker, {"pid": value["pid"], "launcher_pid": process.pid})
                return
            except httpx.HTTPError:
                time.sleep(0.2)
        raise EnvironmentError("owned API startup timed out")
    except Exception:
        stop_api(path, state, name)
        raise


def serve(path, state, name):
    require_sources(state)
    identity(path, state, name)
    import uvicorn

    from app.ai.adapter import OrderAiAdapter
    from app.ai.extractor import RunPodExtractor
    from app.extraction.runpod_adapter import RunPodAdapterProvider
    from app.main import create_app

    extractor = RunPodExtractor()
    require(not extractor.api_key and not extractor.api_url, "remote AI must be absent")
    origin = f"http://127.0.0.1:{state['frontend_port']}"
    app = create_app(
        Settings(
            _env_file=None,
            database_url=url(path, state, name),
            ai_provider="stub",
            cors_allow_origins=origin,
        )
    )
    app.state.extraction_provider = RunPodAdapterProvider(OrderAiAdapter(extractor=extractor))
    instance = uuid4().hex

    @app.get("/__b05_identity", include_in_schema=False)
    def get_identity():
        return {
            "environment_id": state["env_id"],
            "side": name,
            "pid": os.getpid(),
            "instance": instance,
            "database": identity(path, state, name),
            "mode_policy": "OFFLINE_FALLBACK",
            "remote_ai_configured": False,
            "cache_scope": "this API process and this side's database; no shared Redis",
        }

    uvicorn.run(app, host="127.0.0.1", port=state["sides"][name]["api_port"], log_level="info")


def replace_session_hashes(seed_text, tokens):
    for role in ROLES:
        pattern = (
            rf"(INSERT INTO users .*?VALUES \('USR_T1_{role}', 'T1', '[^']+', ')[a-f0-9]{{64}}(')"
        )
        digest = hashlib.sha256(tokens[role].encode()).hexdigest()
        seed_text, count = re.subn(pattern, lambda m, value=digest: m[1] + value + m[2], seed_text)
        require(count == 1, "canonical T1 user seed structure changed")
    return seed_text


def reset_args(path, state, out, mode):
    side = state["sides"]["firstuse"]
    return [
        mode,
        "--admin-url",
        url(path, state, "firstuse", "postgres"),
        "--template",
        side["template"],
        "--target",
        side["database"],
        "--tenant",
        "T1",
        "--expect-seed-version",
        side["seed_version"],
        "--expect-seed-sha256",
        side["seed_sha256"],
        "--log-dir",
        str(out / "logs"),
        "--evidence-dir",
        str(out / "evidence"),
    ]


def snapshot(path, state, name):
    actual = identity(path, state, name)
    with psycopg.connect(url(path, state, name), connect_timeout=3) as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        tables = {
            table: [
                r[0]
                for r in conn.execute(
                    sql.SQL("SELECT to_jsonb(t) FROM {} t ORDER BY to_jsonb(t)::text").format(
                        sql.Identifier(table)
                    )
                )
            ]
            for table in TABLES
        }
    checkpoints = path.parent / "checkpoints"
    hashes = {
        p.relative_to(checkpoints).as_posix(): sha(p)
        for p in sorted(checkpoints.rglob("*"))
        if p.is_file()
    }
    return {
        "database": actual,
        "tables": tables,
        "checkpoints": hashes if name == "protected" else {},
    }


def create(pg_bin):
    for name in ("initdb", "pg_ctl", "postgres"):
        require(
            (pg_bin / (name + (".exe" if os.name == "nt" else ""))).is_file(),
            "PostgreSQL initdb/pg_ctl/postgres binaries are required",
        )
    version = subprocess.run(
        [str(pg_bin / ("postgres.exe" if os.name == "nt" else "postgres")), "--version"],
        capture_output=True,
        text=True,
        timeout=10,
        creationflags=FLAGS,
    )
    require(
        version.returncode == 0 and re.search(r"\b17\.", version.stdout),
        "this delivery requires PostgreSQL 17 binaries",
    )
    env_id = "b05-env-" + uuid4().hex[:12]
    folder = home() / env_id
    folder.mkdir(parents=True, exist_ok=False)
    path = folder / "environment.json"
    used = set()

    def port():
        while True:
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                value = sock.getsockname()[1]
            if value not in used:
                used.add(value)
                return value

    suffix = env_id.removeprefix("b05-env-")
    state = {
        "schema": "b05-owned-environment-v1",
        "env_id": env_id,
        "nonce": uuid4().hex,
        "created_at": now(),
        "status": "CREATING",
        "postgres_bin": str(pg_bin.resolve()),
        "frontend_port": port(),
        "source_files": sources(),
        "sides": {},
        "actual_participant_trials": "NOT_RUN",
        "kind": "TECHNICAL_ENVIRONMENT_DELIVERY",
    }
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=FLAGS,
        )
        state["source_commit"] = revision.stdout.strip() if revision.returncode == 0 else None
    except FileNotFoundError:
        state["source_commit"] = None
    credentials = {}
    for name in SIDES:
        (folder / name).mkdir()
        credentials[name] = {
            "postgres_password": secrets.token_urlsafe(30),
            "tokens": {role: "b05_" + secrets.token_urlsafe(32) for role in ROLES},
        }
        (folder / name / "postgres-password.private.txt").write_text(
            credentials[name]["postgres_password"] + "\n", "utf-8"
        )
        (folder / name / "postgres-password.private.txt").chmod(0o600)
        state["sides"][name] = {
            "database": f"kiraorder_demo_b05_{name}_{suffix}",
            "template": f"kiraorder_b05_{name}_seed_{suffix}",
            "pg_port": port(),
            "api_port": port(),
            "identity": None,
            "seed_version": "B05-" + suffix,
        }
    save(folder / "credentials.private.json", credentials)
    (folder / "credentials.private.json").chmod(0o600)

    def persist():
        save(path, state)
        save(
            folder / "owner.json",
            {
                "env_id": env_id,
                "nonce": state["nonce"],
                "postgres_bin": state["postgres_bin"],
                "bindings": {name: side_binding(s) for name, s in state["sides"].items()},
            },
        )

    persist()
    canonical = ROOT / "data/seed/T1_seed.sql"
    require(
        sha(canonical)
        == read(ROOT / "data/seed/SEED_MANIFEST.json")["tenants"]["T1"]["sql_sha256"],
        "canonical seed hash mismatch",
    )
    try:
        for name in SIDES:
            side = state["sides"][name]
            seed = folder / name / "seed.private.sql"
            seed.write_text(
                replace_session_hashes(canonical.read_text("utf-8"), credentials[name]["tokens"]),
                "utf-8",
            )
            side["seed_sha256"] = sha(seed)
            pg_control(path, state, name, "start", initialize=True)
            args = [
                "--init-template",
                "--admin-url",
                url(path, state, name, "postgres"),
                "--template",
                side["template"],
                "--target",
                side["database"],
                "--tenant",
                "T1",
                "--seed-sql",
                str(seed),
                "--seed-version",
                side["seed_version"],
                "--seed-sha256",
                side["seed_sha256"],
                "--log-dir",
                str(folder / name / "init-logs"),
                "--evidence-dir",
                str(folder / name / "init-evidence"),
            ]
            with redirect_stdout(io.StringIO()):
                require(reset_main(args) == 0, "new owned template initialization failed")
            with psycopg.connect(url(path, state, name, "postgres"), autocommit=True) as conn:
                conn.execute(
                    sql.SQL("CREATE DATABASE {} TEMPLATE {}").format(
                        sql.Identifier(side["database"]), sql.Identifier(side["template"])
                    )
                )
            side["identity"] = identity(path, state, name, verify=False)
            persist()
        require(
            state["sides"]["protected"]["identity"]["system_identifier"]
            != state["sides"]["firstuse"]["identity"]["system_identifier"],
            "clusters must differ",
        )
        state["baseline"] = {name: snapshot(path, state, name) for name in SIDES}
        state["status"] = "READY"
        persist()
    finally:
        for name in SIDES:
            if (folder / name / "data/PG_VERSION").exists():
                pg_control(path, state, name, "stop")
    save(home() / "latest.json", {"state": str(path)})
    return path, state


def check(path, state):
    require_sources(state)
    credentials = private(path)
    report = {
        "kind": "TECHNICAL_ENVIRONMENT_CHECK",
        "actual_participant_trials": "NOT_RUN",
        "checks": {},
        "identities": {},
    }
    for name in SIDES:
        value = api_identity(path, state, name)
        report["identities"][name] = value
        report["checks"][name + "_fallback"] = value["mode_policy"] == "OFFLINE_FALLBACK"
        tokens = credentials[name]["tokens"]
        other = credentials[SIDES[1 - SIDES.index(name)]]["tokens"]
        with httpx.Client(timeout=5, trust_env=False) as client:
            base = api_base(state, name) + "/api/v1"
            for role in ROLES:
                response = client.get(
                    base + "/me", headers={"Authorization": "Bearer " + tokens[role]}
                )
                report["checks"][name + "_role_" + role] = (
                    response.status_code == 200
                    and response.json()["role"] == role
                    and response.json()["tenant"]["id"] == "T1"
                )
            response = client.get(
                base + "/me", headers={"Authorization": "Bearer " + other["CLERK"]}
            )
            report["checks"][name + "_rejects_other_side_token"] = response.status_code == 401
            origin = f"http://127.0.0.1:{state['frontend_port']}"
            response = client.options(
                base + "/me", headers={"Origin": origin, "Access-Control-Request-Method": "GET"}
            )
            report["checks"][name + "_frontend_cors"] = (
                response.status_code == 200
                and response.headers.get("access-control-allow-origin") == origin
            )
    report["status"] = "PASS" if all(report["checks"].values()) else "FAIL"
    save(path.parent / "latest-check.json", report)
    require(report["status"] == "PASS", "environment identity/role/CORS check failed")
    return report


def reset_firstuse(path, state, apply=False):
    require_sources(state)
    identity(path, state, "firstuse")
    identity(path, state, "protected")
    protected_api = api_identity(path, state, "protected")
    firstuse_api = api_identity(path, state, "firstuse")
    before = {name: snapshot(path, state, name) for name in SIDES}
    out = path.parent / "reset-evidence" / ("reset-" + uuid4().hex[:12])
    save(out / "before.json", before)
    side = state["sides"]["firstuse"]
    require(
        sha(path.parent / "firstuse/seed.private.sql") == side["seed_sha256"],
        "private first-use seed changed",
    )
    if apply:
        stop_api(path, state, "firstuse")
    output = io.StringIO()
    with redirect_stdout(output):
        code = reset_main(reset_args(path, state, out, "--apply" if apply else "--dry-run"))
    (out / "core-reset.stdout.json").write_text(output.getvalue(), "utf-8")
    require(code == 0, "first-use reset failed; preserve evidence and inspect owned logs")
    if apply:
        start_side(path, state, "firstuse")
    after = {name: snapshot(path, state, name) for name in SIDES}
    checks = {
        "protected_all_tables_and_checkpoints_unchanged": before["protected"] == after["protected"],
        "protected_api_pid_instance_unchanged": protected_api
        == api_identity(path, state, "protected"),
        "firstuse_restored" if apply else "firstuse_unchanged": after["firstuse"]
        == (state["baseline"]["firstuse"] if apply else before["firstuse"]),
        "firstuse_api_restarted" if apply else "firstuse_api_unchanged": (
            firstuse_api["instance"] != api_identity(path, state, "firstuse")["instance"]
        )
        == apply,
    }
    report = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "apply": apply,
        "target": side["database"],
        "checks": checks,
        "actual_participant_trials": "NOT_RUN",
    }
    save(out / "after.json", after)
    save(out / "result.json", report)
    require(report["status"] == "PASS", "reset verification failed; keep all evidence and backups")
    return {"report": str(out / "result.json"), **report}


def public_manifest(path, state):
    return {
        "environment_id": state["env_id"],
        "kind": state["kind"],
        "status": state["status"],
        "frontend_url": f"http://127.0.0.1:{state['frontend_port']}/#/workspace",
        "sides": {
            name: {
                "database": side["database"],
                "postgres_port": side["pg_port"],
                "api_base": api_base(state, name) + "/api/v1",
                "identity": side["identity"],
            }
            for name, side in state["sides"].items()
        },
        "mode": "LOCAL_SYNTHETIC_T1_FALLBACK",
        "actual_participant_trials": "NOT_RUN",
        "cache_isolation": "separate API processes and database alias caches; no shared Redis",
        "reset_target": "generated firstuse database only",
        "state_file": str(path),
        "source_commit": state.get("source_commit"),
        "source_manifest_sha256": hashlib.sha256(
            json.dumps(state.get("source_files", {}), sort_keys=True).encode()
        ).hexdigest(),
        "credentials": "credentials.private.json beside the state; never publish it",
    }


def handoff(path, manifest):
    lines = [
        "# B05 isolated local environment",
        "",
        "Kind: technical environment delivery.",
        "Actual participant trials: NOT_RUN. No participant/timing denominator.",
        "",
        "Frontend: " + manifest["frontend_url"],
        "",
        "| Side | Database | API |",
        "| --- | --- | --- |",
    ]
    for name, side in manifest["sides"].items():
        lines.append(f"| {name} | {side['database']} | {side['api_base']} |")
    lines += [
        "",
        "Connect the frontend API connection to the firstuse API above.",
        "OWNER and CLERK use separate browser sessions and their own private tokens.",
        "Private credentials: credentials.private.json beside this file. Do not publish it.",
        "",
        "Run commands from this checkout's backend directory:",
        "",
        "```text",
    ]
    for action in ("start", "frontend", "check", "reset-firstuse", "stop"):
        lines.append(f'python -m tools.b05_environment --state "{path}" {action}')
    lines += [
        "```",
        "",
        "reset-firstuse defaults to a read-only dry run; --apply resets only",
        "this environment's generated firstuse database, retains backups, and verifies",
        "the protected side. Shared demo databases are not accepted as input.",
    ]
    (path.parent / "HANDOFF.md").write_text("\n".join(lines) + "\n", "utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path)
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("create").add_argument("--pg-bin", type=Path, required=True)
    for action in ("start", "stop", "_serve"):
        commands.add_parser(action).add_argument("--side", choices=(*SIDES, "both"), default="both")
    commands.add_parser("status")
    commands.add_parser("check")
    commands.add_parser("frontend")
    commands.add_parser("reset-firstuse").add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.action == "create":
            path, state = create(args.pg_bin)
        else:
            path, state = load(args.state)
            if args.action == "_serve":
                require(args.side in SIDES, "serve requires one side")
                serve(path, state, args.side)
                return 0
            with operation(path):
                names = SIDES if getattr(args, "side", "both") == "both" else (args.side,)
                if args.action == "start":
                    for name in names:
                        start_side(path, state, name)
                elif args.action == "stop":
                    if args.side == "both":
                        stop_frontend(path)
                    for name in names:
                        stop_api(path, state, name)
                        pg_control(path, state, name, "stop")
                elif args.action == "check":
                    print(json.dumps(check(path, state)))
                    return 0
                elif args.action == "frontend":
                    start_frontend(path, state)
                elif args.action == "reset-firstuse":
                    print(json.dumps(reset_firstuse(path, state, args.apply)))
                    return 0
        manifest = public_manifest(path, state)
        save(path.parent / "environment-public.json", manifest)
        handoff(path, manifest)
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 0
    except EnvironmentError as exc:
        print(json.dumps({"status": "REFUSED_OR_FAILED", "reason": str(exc)}), file=sys.stderr)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "FAILED",
                    "error_type": type(exc).__name__,
                    "reason": "details suppressed; inspect owned private logs",
                }
            ),
            file=sys.stderr,
        )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
