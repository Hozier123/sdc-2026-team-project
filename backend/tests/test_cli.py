import json
import os
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, build_opener

import pytest

from app.config import REPO_ROOT

BACKEND = REPO_ROOT / "backend"


def run_migration(env):
    return subprocess.run(
        [sys.executable, "-m", "app.migrations"],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def test_cli_missing_url_fails_cleanly():
    env = os.environ.copy()
    env["DATABASE_URL"] = ""  # Override any repository .env value.
    result = run_migration(env)
    assert result.returncode == 1
    assert "DATABASE_URL must be a PostgreSQL URL" in result.stderr
    assert "Traceback" not in result.stderr


def test_cli_connection_error_does_not_leak_credentials():
    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))
        env = os.environ.copy()
        env["DATABASE_URL"] = (
            f"postgresql://user:cli_secret@127.0.0.1:{reserved.getsockname()[1]}/db"
        )
        result = run_migration(env)
    assert result.returncode == 1
    assert "database error" in result.stderr
    assert "cli_secret" not in result.stderr + result.stdout
    assert "Traceback" not in result.stderr


@pytest.mark.integration
def test_uvicorn_startup_and_migration_command(db_settings):
    env = os.environ.copy()
    env["DATABASE_URL"] = db_settings.database_url.get_secret_value()
    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))
        port = reserved.getsockname()[1]
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "error",
        ],
        cwd=BACKEND,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    opener = build_opener(ProxyHandler({}))

    def probe(path):
        return opener.open(f"http://127.0.0.1:{port}{path}", timeout=2)

    try:
        deadline = time.monotonic() + 15
        while True:
            assert process.poll() is None, "Uvicorn exited during startup"
            try:
                with probe("/healthz") as response:
                    assert response.status == 200
                    assert json.load(response) == {"status": "ok"}
                break
            except URLError:
                if time.monotonic() >= deadline:
                    pytest.fail("Uvicorn did not become live")
                time.sleep(0.1)
        with pytest.raises(HTTPError) as not_ready:
            probe("/readyz")
        assert not_ready.value.code == 503
        not_ready.value.close()
        first = run_migration(env)
        assert first.returncode == 0, first.stderr
        result = json.loads(first.stdout)
        assert result["status"] == "applied"
        assert (result["table_count"], result["trigger_count"], result["trigger_event_count"]) == (
            18,
            6,
            12,
        )
        second = run_migration(env)
        assert second.returncode == 0, second.stderr
        assert json.loads(second.stdout)["status"] == "already_applied"
        with probe("/readyz") as response:
            assert response.status == 200
            assert json.load(response) == {"status": "ready"}
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
