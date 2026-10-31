# F05 Pages and offline runbook

The production frontend is a GitHub Pages project site. Its base path is
`/sdc-2026-team-project/` and its public API is
`https://kiraorder-api.replit.app/api/v1`. Build with Node 22 from a reviewed,
fixed source commit:

```sh
cd frontend
npm ci
npm test
VITE_API_BASE_URL=https://kiraorder-api.replit.app/api/v1 npm run build -- --base=/sdc-2026-team-project/
cd ..
python3 scripts/verify_pages_dist.py frontend/dist --output /path/to/private/build-manifest.json
```

Record the source commit, build command, Node version, build time, previous and
new `gh-pages` commits, and the deployed URL. Verify the Pages root and
`#/workspace` in a fresh browser after publication. Compare the fetched HTML
and referenced asset SHA-256 values with the build manifest; a passing frontend
CI job alone does not prove that Pages serves this build. Preserve the previous
Pages commit for rollback. Do not force-push or replace the repository's other
Pages evidence files.

## Offline demonstration

Copy the **same verified `dist` directory** into a folder named
`sdc-2026-team-project` inside an offline bundle. Start a local static server
from the bundle's parent directory:

```sh
python3 -m http.server 8765 --bind 127.0.0.1
```

Open `http://127.0.0.1:8765/sdc-2026-team-project/#/workspace` and keep
**LOCAL DEMO** visible. This mode uses synthetic browser data and offline
matching; it does not prove real API permissions, live AI extraction, server
inventory, or persistent delivery orders. A real workflow requires the public
API and an authorized session token supplied privately through Connect API.
Never put session tokens in the bundle, URL, screenshots, video, or VITE
variables. The introduction may load a remote background video; start the
offline demonstration directly at the workspace.

## First-use trial protocol

Before each trial, fix one task ID, a synthetic input, the tenant, the gold
SKU/unit/quantity, and the expected terminal state: owner pending or regular
approval with a DO. Record the source/data version and whether the participant
has prior exposure or overlaps a later timed trial. Give each of four first
users 12 minutes for the task and 2 minutes for review/handoff. Stop at 12
minutes; an unfinished attempt is a timeout. If a hint is needed, record the
result as assisted. Record actual terminal state, elapsed seconds, and any
technical interruption. A facilitator, gold-standard reviewer, and real
participants must provide the observations; do not infer a usability pass from
automated browser checks.
