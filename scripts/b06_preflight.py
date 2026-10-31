"""Read-only B06 access and published-asset checks; Python 3.13 standard library.

Credentials are sent only to the fixed production API, never to redirects, Pages,
or the output. This does not parse, wake AI, approve, migrate, reset, or deploy.
"""

import argparse
import hashlib
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import uuid4

API = "https://kiraorder-api.replit.app"
PAGES = "https://hozier123.github.io/sdc-2026-team-project/"
ORIGIN = "https://hozier123.github.io"
ROOT = Path(__file__).resolve().parents[1]
ROLES = ("CLERK", "OWNER", "WAREHOUSE")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def now():
    return datetime.now(UTC).isoformat()


def git(*args):
    return subprocess.run(
        ["git", "-C", str(ROOT), *args], check=True, capture_output=True
    ).stdout


def request(url, *, token=None, method="GET", headers=None):
    if method not in ("GET", "OPTIONS"):
        raise ValueError("read-only methods required")
    if token is not None and urlparse(url).netloc != urlparse(API).netloc:
        raise ValueError("credentials may only reach the fixed production API")
    request_id = "b06-" + uuid4().hex
    sent = {"X-Request-ID": request_id, **(headers or {})}
    if token is not None:
        sent["Authorization"] = "Bearer " + token
    try:
        response = build_opener(NoRedirect()).open(
            Request(url, headers=sent, method=method), timeout=25
        )
    except HTTPError as error:
        response = error
    except (URLError, TimeoutError, OSError):
        return {"http_status": None, "error": "NETWORK_ERROR"}, b""
    with response:
        raw = response.read()
        record = {
            "http_status": response.status,
            "request_id": response.headers.get("X-Request-ID"),
            "allow_origin": response.headers.get("Access-Control-Allow-Origin"),
            "allow_headers": response.headers.get("Access-Control-Allow-Headers"),
        }
    return record, raw


def body_json(raw):
    try:
        return json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return {}


def token_candidates(paths):
    actors = {(t, r): [] for t in ("T1", "T2") for r in ROLES}
    for path in paths:
        data = json.loads(Path(path).read_text("utf-8-sig"))
        for (tenant, role), candidates in actors.items():
            token = data.get(tenant, {}).get(f"USR_{tenant}_{role}")
            if isinstance(token, str) and token and token not in candidates:
                candidates.append(token)
    return actors


def run(args):
    started = now()
    checks, evidence = {}, {}
    pages_commit = (
        git("rev-parse", "--verify", args.pages_ref + "^{commit}").decode().strip()
    )
    release_raw = git("show", f"{pages_commit}:release.json")
    release = json.loads(release_raw)
    release_record, online_release = request(PAGES + "release.json")
    checks["pages_release_matches_git"] = (
        release_record["http_status"] == 200 and online_release == release_raw
    )
    paths = git("ls-tree", "-r", "--name-only", pages_commit).decode().splitlines()
    asset_paths = [p for p in paths if p == "index.html" or p.startswith("assets/")]

    def asset_check(path):
        expected = git("show", f"{pages_commit}:{path}")
        record, actual = request(PAGES + quote(path, safe="/"))
        return {
            "path": path,
            "http_status": record["http_status"],
            "expected_sha256": hashlib.sha256(expected).hexdigest(),
            "actual_sha256": hashlib.sha256(actual).hexdigest(),
            "pass": record["http_status"] == 200 and actual == expected,
        }

    with ThreadPoolExecutor(max_workers=6) as pool:
        assets = list(pool.map(asset_check, asset_paths))
    checks["pages_assets_match_git"] = bool(assets) and all(a["pass"] for a in assets)
    index = next(a for a in assets if a["path"] == "index.html")
    checks["index_matches_release_manifest"] = (
        index["actual_sha256"] == release["index_sha256"]
    )
    evidence["pages"] = {"commit": pages_commit, "release": release, "assets": assets}
    record, raw = request(API + "/readyz")
    checks["backend_ready"] = (
        record["http_status"] == 200 and body_json(raw).get("status") == "ready"
    )
    evidence["readyz"] = {**record, "status": body_json(raw).get("status")}
    for label, token in (("missing", None), ("invalid", "b06-deliberately-invalid")):
        record, raw = request(API + "/api/v1/me", token=token)
        code = body_json(raw).get("error_code")
        checks[label + "_token_rejected"] = (
            record["http_status"] == 401 and code == "INVALID_TOKEN"
        )
        evidence[label + "_token"] = {**record, "error_code": code}
    record, _ = request(
        API + "/api/v1/me",
        method="OPTIONS",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization,x-request-id",
        },
    )
    allowed_headers = (record.get("allow_headers") or "").lower()
    checks["pages_cors"] = (
        record["http_status"] == 200
        and record["allow_origin"] == ORIGIN
        and all(key in allowed_headers for key in ("authorization", "x-request-id"))
    )
    evidence["cors"] = record
    roles = []
    actors = token_candidates(args.tokens_file)
    for (tenant, role), candidates in actors.items():
        identity = None
        for token in candidates:
            record, raw = request(
                API + "/api/v1/me", token=token, headers={"Origin": ORIGIN}
            )
            body = body_json(raw)
            if (
                record["http_status"] == 200
                and body.get("role") == role
                and body.get("tenant", {}).get("id") == tenant
                and body.get("user_id") == f"USR_{tenant}_{role}"
            ):
                identity = {
                    **record,
                    "tenant_id": tenant,
                    "role": role,
                    "user_id": body["user_id"],
                    "permissions": body.get("permissions", []),
                }
                catalog_record, catalog_raw = request(
                    API + "/api/v1/catalog/products", token=token
                )
                catalog = body_json(catalog_raw)
                catalog_ok = catalog_record["http_status"] == (
                    403 if role == "WAREHOUSE" else 200
                )
                if role == "WAREHOUSE":
                    catalog_ok = (
                        catalog_ok and catalog.get("error_code") == "FORBIDDEN_ACTION"
                    )
                else:
                    catalog_ok = catalog_ok and len(catalog.get("items", [])) == (
                        40 if tenant == "T1" else 16
                    )
                identity["catalog"] = {
                    **catalog_record,
                    "pass": catalog_ok,
                    "count": len(catalog.get("items", []))
                    if role != "WAREHOUSE"
                    else None,
                }
                break
        label = tenant + "_" + role
        checks[label + "_identity"] = (
            identity is not None
            and identity["allow_origin"] == ORIGIN
            and bool(identity["request_id"])
        )
        checks[label + "_catalog_access"] = (
            identity is not None and identity["catalog"]["pass"]
        )
        roles.append(
            identity
            or {"tenant_id": tenant, "role": role, "status": "MISSING_OR_INVALID"}
        )
    evidence["roles"] = roles
    result = {
        "task": "B06",
        "started_at_utc": started,
        "finished_at_utc": now(),
        "result": "PASS" if all(checks.values()) else "INCOMPLETE",
        "checks_passed": sum(checks.values()),
        "checks_total": len(checks),
        "checks": checks,
        "sources": {
            "main_at_check": git("rev-parse", "HEAD").decode().strip(),
            "pages_commit": pages_commit,
        },
        "scope": {
            "methods": ["GET", "OPTIONS"],
            "business_writes": 0,
            "deployments": 0,
            "migrations": 0,
            "resets": 0,
            "model_calls": 0,
            "ai_status_or_wake_calls": 0,
            "runtime_deployment_verification": "SEPARATE_REPLIT_UI_OBSERVATION",
            "business_e2e": "NOT_RERUN",
        },
        "evidence": evidence,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                k: result[k]
                for k in ("result", "checks_passed", "checks_total", "finished_at_utc")
            }
        )
    )
    return 0 if result["result"] == "PASS" else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tokens-file",
        type=Path,
        action="append",
        required=True,
        help="private T1/T2 -> USR_T1_CLERK etc. token JSON; never copied to output",
    )
    parser.add_argument("--pages-ref", default="origin/gh-pages")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("choose a new output file; historical evidence is not overwritten")
    try:
        return run(args)
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError):
        print(
            "B06 preflight could not complete; no credentials are logged.",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
