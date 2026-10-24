# KiraOrder for Orbyte

SDC Hackathon 2026 - Domain 2 - Orbyte Smart SME Challenge

## Project Links

- Live Prototype: https://hozier123.github.io/sdc-2026-team-project/
- Backend API: https://kiraorder-api.replit.app/api/v1
- Backend Health Check: https://kiraorder-api.replit.app/readyz
- Pitch Video & Prototype Demonstration: https://youtu.be/TyrASSJDIpM
- Pitch Deck: [KiraOrder Falcons Pitch Deck](submission/KiraOrder_Falcons_PitchDeck_SDC2026.pptx)

## Judge's quick-start guide

### Open the current prototype

Open the [current frontend](https://hozier123.github.io/sdc-2026-team-project/), then click or tap the introduction, or press **Enter / Space**, to enter. To skip the introduction, [open the workspace directly](https://hozier123.github.io/sdc-2026-team-project/#/workspace). On a phone, use the top-left menu to open the sidebar.

Start with **LOCAL DEMO**. It requires no account, password, token, installation, backend connection, or running GPU. The Replit backend URL is an API, and the legacy Replit frontend is an older UI; use GitHub Pages for this walkthrough.

### Switch roles and workspaces

Select **Bintang Wholesale** in the workspace selector. Open the role selector in the top-right header (it displays a label such as **Order clerk · demo**) and choose a role:

| Demo role | What to review |
| --- | --- |
| **Order clerk** | Create and check drafts, resolve issues, approve routine orders, and send exceptions to the owner. |
| **Owner** | Review saved approval requests, approve an order, or reject it with a reason. |
| **Warehouse** | Find a delivery order by its DO number and check picking information without prices or customer contact details. |

Save or discard edits before switching roles or workspaces. Keep the same workspace while following one order. Role switching is a Local Demo feature; connected API permissions come from the authenticated backend session.

### Walkthrough A: create a routine order

1. Choose **Bintang Wholesale** and **Order clerk · demo**.
2. Open **New order** and select **Restoran Ali** as the customer.
3. Choose **The everyday order** sample, or paste the following synthetic message:

   ```text
   Tepung 4 ctn
   Minyak 2 ctn
   ```

4. Click **Create order draft**. Check products, specifications, quantities, units, prices, stock, and total.
5. Resolve any highlighted issues. If you edit anything, click **Save changes** and recheck the saved result.
6. Click **Approve & generate DO** when available. If the page instead offers **Send to owner**, follow the approval steps below.
7. Record the generated DO number. Try **Print / save as PDF**, **Copy customer reply**, and **View change record**. Copying a reply does not send it to a customer.

If approval is unavailable, check unsaved edits, unresolved issues, stock, and the selected role. Owner approval does not bypass stock or unresolved blocking issues.

### Walkthrough B: review an owner exception

In a fresh Local Demo, switch to **Owner · demo**, open **Owner approvals**, and select a seeded pending request. Review its saved snapshot and escalation reason. Use **Approve & generate DO**, or **Reject with reason** followed by **Reject order**.

To create a new price exception yourself:

1. Switch to **Order clerk · demo**, choose **Restoran Ali**, and create a draft from the **A price to decide** sample: `Tepung 5 ctn, kalau RM95 boleh?`.
2. In **Customer conditions**, choose **Accept a requested discount**. Select the flour line, enter **95.00** as the price per catalogue unit, and give a synthetic test reason.
3. Click **Record decision**, then **Save changes**. Check the saved price and total, then click **Send to owner**.
4. Switch to **Owner · demo**, open **Owner approvals**, and select the request you just submitted. Approve it or reject it with a reason.

Requests awaiting owner approval cannot be edited directly. A rejected order is closed; create a new draft if a revised order is needed.

### Walkthrough C: check warehouse picking

1. Switch to **Warehouse · demo** in the same workspace.
2. Enter the DO number generated above, or use the seeded **DO-T1-0001** in Bintang Wholesale.
3. Click **Find picking list** and check the product, quantity, unit, and picking requirements. Use **Print picking list** if needed.

Warehouse checkboxes are temporary on-page checks. They do not submit shipment, deduct stock again, or persist picking progress after refresh.

### Local Demo boundaries and recovery

- **LOCAL DEMO / Offline match · non-AI** uses browser-side catalogue rules and synthetic data. It does not call the backend or an LLM and does not establish live AI accuracy, database persistence, tenant isolation, or production authentication.
- Saved demo orders and stock changes remain in the current browser; they do not sync to other devices. Unsaved edits may be lost on refresh. Use a new private/incognito session for a fresh demo, and allow site storage.
- Use **A specification to clarify** to inspect an ambiguous product, or **Check before promising** to inspect insufficient stock. Follow the displayed issues before approving.
- Messages are pasted manually. Clarifications and customer replies are copied drafts, not automatic WhatsApp messages. Use synthetic data only.
- If the prototype cannot be reached, the [pitch and demonstration video](https://youtu.be/TyrASSJDIpM) and [pitch deck](submission/KiraOrder_Falcons_PitchDeck_SDC2026.pptx) provide supporting material; they do not replace an interactive review.

### Controlled access to the real API

API review is **by arrangement with the team**. This README does not publish or provision a judge token, and no authenticated review window is guaranteed by these instructions alone.

1. Contact the team leader through the competition portal's existing team contact or an organizer-mediated private channel. Request an API review session; the team leader coordinates access with the backend maintainer. Do not exchange credentials in a public GitHub issue.
2. Before review, the team should privately provide the designated synthetic tenant, the permitted role, a working role-specific session token, the agreed review window, and a private support contact. If comparing **CLERK**, **OWNER**, and **WAREHOUSE**, request separate role-bound sessions. Do not use database credentials or a RunPod key as a frontend session token.
3. Open GitHub Pages, save or discard demo edits, and choose **Connect API**. Enter API base **https://kiraorder-api.replit.app/api/v1** and the privately supplied token in **Session token**, then click **Connect API**. The frontend verifies the session through `/me`; confirm the returned workspace and role before creating synthetic records.
4. In API mode, the backend determines identity and permissions. To review another role, reconnect using that role's supplied session; the demo role selector cannot grant API privileges. Tokens remain in the current tab's memory. Refreshing returns to Local Demo; **API connection → Return to demo** also exits the connection.
5. If the token is missing, rejected, inactive, or not supplied, use Local Demo and contact the team privately. The [backend readiness check](https://kiraorder-api.replit.app/readyz) tests service readiness, not identity, model readiness, or end-to-end order completion.

The recorded public configuration uses `runpod_adapter` with RunPod **Active=0**, so public parsing falls back. Do not assume an LLM was used or a complete live workflow passed because a page or health check loaded. A live-AI review requires the team to arrange an active model window and verify the path first; no such new verification was performed when writing this guide. Review the displayed mode and errors, and stop for team assistance if required catalogue data or model services are unavailable.

For implementation details and historical evidence, see the [AI sample runbook](docs/ops/ai-sample-runbook.md) and [RunPod evidence](evidence/runpod/2026-10-24/README.md). The detailed [operator guide (Chinese)](frontend/docs/KiraOrder_使用说明.md) explains individual controls; its dated deployment notes are historical, so use this root README for the current recorded deployment status.

**Current status: Gate 0 is frozen (`1.3.0-gate0-v4`). The frontend is deployed on GitHub Pages, the backend on Replit, and PostgreSQL on Neon. Official AI-only evidence records 23/23 LLM calls with 0 fallback; the final six-case set records 5 PASS / 1 KNOWN_LIMITATION. UOM remains 24/31 with 7 known gaps. The TEST32 v5 freeze manifest was reviewed by He and Zhan and merged, but 12 workflow cases remain `NOT_RUN`. RunPod is currently `Active=0`, so public parse falls back and is not an integrated live-AI demonstration. The signed official proposal and tools declaration are in [`submission/`](submission/); the supplied slide deck and pitch video are linked below; UAT and the portal upload remain outstanding. Local tests and a public deployment do not equal full acceptance, and they do not mean the competition submission is complete.**

The data-side seed-count sign-off is dated 2026-10-23 and was signed by Zhou Jingxi. Its scope is limited to seed counts and import evidence; business-field acceptance, AI accuracy, and UAT remain separate. See [evidence/data-signoff/2026-10-23.md](evidence/data-signoff/2026-10-23.md). AI evaluation boundaries are documented in [docs/ops/ai-evaluation-intake.md](docs/ops/ai-evaluation-intake.md).

## Project information

| Item | Value |
| --- | --- |
| Product | KiraOrder for Orbyte |
| Registered team name | Falcons |
| Track | Domain 2 - Orbyte Smart SME Challenge |
| SDG | SDG 8, with emphasis on 8.2 and 8.3 |
| Team leader and university | Zhou Jingxi, Xiamen University Malaysia |
| Members and roles | He Minghao (backend, rules, deployment); Xiong Peicheng (AI, RunPod, deployment); Ye Lianghui (frontend); Zhou Jingxi (data, quality, evaluation); Zhan Zhengrong (manual baseline, materials, submission integration) |
| Repository | https://github.com/Hozier123/sdc-2026-team-project |
| Frontend | https://hozier123.github.io/sdc-2026-team-project/ |
| Backend API | https://kiraorder-api.replit.app/api/v1 |
| Backend health check | https://kiraorder-api.replit.app/readyz |

The intended solution converts mixed-language WhatsApp orders received by Malaysian wholesalers into reviewed, human-approved, traceable delivery orders. Uncertain information is routed to the appropriate person. A public frontend/backend deployment, Local Demo, and AI-only evidence already exist. Complete E2E, independent UAT, and real-user trials are still incomplete.

## Repository layout

This structure follows Appendix B of the team's KiraOrder final execution plan v2 (2026-10-21). In this document, `kiraorder/` refers to the repository root; no additional nested folder with the same name is required.

```text
sdc-2026-team-project/
|-- .github/workflows/          # Backend/frontend CI: isolated PostgreSQL and frontend build
|-- backend/                    # FastAPI backend
|   |-- app/                    # Routes, parsing, approval, DO, AI orchestration, in-process AI adapter
|   |-- tests/                  # Unit, PostgreSQL integration, and contract regression tests
|   |-- tools/                  # Trial export and six-case AI evidence runner
|   |-- pyproject.toml
|   |-- requirements.lock       # Exact dependency constraints
|   `-- README.md               # Install, start, migration, and test instructions
|-- data/
|   |-- seed/                   # T1/T2 synthetic seeds, manifest, and hashes
|   `-- README.md               # Data-directory documentation
|-- docs/
|   |-- audit/                  # Backend audit and current-status updates
|   |-- ops/                    # Export, reset, and AI-consistency procedures
|   |-- rules/                  # v1.3 working rules
|   |-- competition-checklist.md
|   `-- setup-windows.md
|-- evidence/
|   |-- backend-foundation/     # Backend foundation test records (not business KPIs)
|   |-- gate0/                  # Gate 0 independent confirmation materials
|   |   |-- README.md
|   |   `-- (Gate 0 confirmation document; encoded link below)
|   `-- README.md               # Baseline, test results, and screenshot archive
|-- frontend/                   # Frontend: React + TypeScript + Vite
|   |-- src/                    # App shell, page components, API client, generated contract types
|   |-- tests/                  # Automated regression and frozen Gate 0 synthetic fixtures
|   |-- contracts/              # Frozen OpenAPI snapshot and provenance hashes
|   |-- scripts/                # Contract type generation, fixture server, delivery packaging
|   |-- docs/                   # Frontend notes, review, and acceptance records
|   `-- README.md               # Start, backend connection, and verification instructions
|-- gate0/                      # Gate 0 specification and machine-contract baseline
|-- scripts/                    # Evaluation, initialization, and demo-reset helpers
|   `-- .gitkeep
|-- submission/                 # Official competition submission materials
|   |-- README.md
|   |-- SDC2026_Falcons_Preliminary.pdf  # Signed preliminary proposal
|   |-- SDC2026_Falcons_TechDeclaration.pdf  # Signed tools declaration and platform evidence
|   `-- KiraOrder_Falcons_PitchDeck_SDC2026.pptx  # Pitch deck
|-- tests/                      # Test code, test data, and frozen-set records
|   `-- .gitkeep
|-- .env.example                # Configuration variable names with empty values
|-- .gitattributes              # PDFs treated as binary
|-- .gitignore
|-- LICENSE                     # Apache License 2.0
`-- README.md
```

The tree above lists the main directories and entry files. GitHub may collapse a path that has only one subdirectory, such as `src/pages`; it still represents two nested directories.

A `.gitkeep` file only keeps an otherwise empty directory in Git and can be removed after real files are added. `data/README.md` and `frontend/README.md` document their directories and also make `data/` and `frontend/` visible at the repository root. The frontend project lives directly under `frontend/`, and the backend directly under `backend/`.

`gate0/` is kept as one unit containing the specification, machine contracts, migrations, and verification tools. It is not split into business directories and must not be silently changed after freezing. The four-party confirmation materials are stored separately under `evidence/gate0/` and are linked to the corresponding Git tag through controlled manifest hashes.

Gate 0 is frozen at [`gate0-baseline-v1`](https://github.com/Hozier123/sdc-2026-team-project/tree/gate0-baseline-v1), commit `3478c31fbbcaf295130e87a992ccdff1a4fabf8e`, corresponding to internal `gate0-v4 / draft revision 5`. The formal four-party confirmation is in the [Gate 0 confirmation](evidence/gate0/%E7%A1%AE%E8%AE%A4%E4%B9%A6.md) and the [evidence binding notes](evidence/gate0/README.md). The pending-signature state in `gate0/docs/gate0-signoff.md` and the manifest preserves the preparation snapshot; final confirmation is based on the external evidence and the tag above. Maintenance notes do not rewrite the frozen snapshot or move the tag.

The later v1.3 working documents 01-04 are under `docs/rules/` and are updated with the backend implementation. The v1.2 originals under `gate0/external-inputs/protected/` remain in place.

## Environment and operation

A runnable backend service and frontend workspace already exist. Do not run the old `python src/main.py`. The old root `src/`, `runpod/`, example tests, demo-only `requirements.txt`, and `.replit` were removed from the current version; history remains in earlier commits.

Clone the repository first:

```powershell
git clone https://github.com/Hozier123/sdc-2026-team-project.git
cd sdc-2026-team-project
if (-not (Test-Path -LiteralPath .env)) {
    Copy-Item -LiteralPath .env.example -Destination .env
}
```

Members who already have a local copy should preserve their changes and run `git pull --ff-only`. The real `.env` file is ignored by Git.

The backend uses Python 3.13 and PostgreSQL 17. Dependency installation, explicit migration commands, `/healthz` and `/readyz`, and the full test procedure are in [backend/README.md](backend/README.md). Installation and collaboration notes are in [docs/setup-windows.md](docs/setup-windows.md); historical baseline records are in the [backend foundation validation record](evidence/backend-foundation/README.md), and current completion status and boundaries are in the [backend audit report](docs/audit/backend-audit-2026-10-23.md).

The frontend uses Node.js 22 and npm. From `frontend/`, run `npm ci` and `npm run dev` (default `http://127.0.0.1:5173/`). To connect to the real backend, enter API base `http://127.0.0.1:8000/api/v1` and the session Bearer token, or set the default through `VITE_API_BASE_URL` in `.env.local`. Frontend tests and build are `npm test` and `npm run build`; CI is in `.github/workflows/frontend.yml`, with details in [frontend/README.md](frontend/README.md).

Established development and deployment approach:

- Development: the frontend connects directly to FastAPI through `VITE_API_BASE_URL`; the current Vite configuration does not enable an API proxy.
- Frontend deployment: GitHub Pages at `https://hozier123.github.io/sdc-2026-team-project/`; the Replit frontend is legacy/old UI.
- Backend deployment: Replit Core, Autoscale, public `https://kiraorder-api.replit.app`; database Neon PostgreSQL 17.11.
- AI: the code default is `AI_PROVIDER=auto`; the current public configuration is `runpod_adapter` with RunPod `Active=0`, so public parse falls back and is not an integrated live-AI demonstration.
- A public deployment exists; do not treat local `npm run dev` as deployed.
- Decisions are in [docs/ops/public-deployment-decision.md](docs/ops/public-deployment-decision.md); the checklist is in [docs/ops/public-deployment-checklist.md](docs/ops/public-deployment-checklist.md).

## Configuration

`.env.example` lists the configuration variable names with empty values. The backend reads:

```text
DATABASE_URL
AI_PROVIDER (auto | stub | http | runpod_adapter; default auto)
AI_SERVICE_URL / AI_HEALTH_URL / AI_WAKE_URL
AI_API_KEY / AI_TIMEOUT_S
RUNPOD_API_KEY / RUNPOD_ENDPOINT_ID / RUNPOD_MODEL_NAME / LLM_TIMEOUT_S
AI_WAKE_RATE_LIMIT_S / AI_WARMUP_GRACE_S
CORS_ALLOW_ORIGINS
```

The in-process `OrderAiAdapter` is enabled only with `AI_PROVIDER=runpod_adapter`; it requires `RUNPOD_API_KEY` and `RUNPOD_ENDPOINT_ID`. The code default is `auto` (Stub when `AI_SERVICE_URL` is absent). The current public deployment uses `runpod_adapter`, and public parse falls back when RunPod `Active=0`. There is no `/api/v1/extract`; AI is invoked in-process by `parse-draft`.

Real secrets belong only in the local environment or Replit Secrets, never in code, documentation, or screenshots. Business demonstrations use only team-created synthetic data. The six-case evidence runner is documented in [docs/ops/ai-sample-runbook.md](docs/ops/ai-sample-runbook.md).

## Current implementation and acceptance boundaries

```text
Implemented and covered by automated tests:
identity/tenant permissions, seed, PII masking, parse, catalogue resolution,
customer memory, field evidence, draft save/status, conditions and clarification,
trilingual replies, approval/DO/inventory transactions, customer/draft/approval/
activity/audit/warehouse reads, AI status and wake-up, in-process RunPod adapter
(disabled by default), six-case evidence runner, three checks_enabled soft checks,
concurrency/rollback, export evidence binding, and contract fixture regression.
```

CI (Backend foundation + Frontend) passes on the current `main`; the latest local backend non-integration suite recorded **307 passed**. Full integration tests require `TEST_DATABASE_ADMIN_URL`, so 307 must not be presented as the complete integration result. The following external boundaries remain open:

- RunPod is currently `Active=0`, so public parse falls back; live model quality and latency require a new active window for online verification.
- AI-only evidence completed 23/23 LLM calls, but accuracy remains `NOT_COMPUTED`; UOM is 24/31 with 7 known gaps.
- The 12 TEST32 workflow cases remain `NOT_RUN`; complete E2E is not available.
- Independent UAT and real-user trial records from the frontend and data owners are still incomplete.
- The supplied slide deck and pitch video are linked below; the signed proposal and tools declaration are in `submission/`. Portal submission remains to be confirmed.

The v1.3 working documents 01-04 are under `docs/rules/` and are updated with the implementation; frozen originals are not rewritten.

## Required links and formal materials

| Item | Link or status |
| --- | --- |
| Prototype / accessible build | https://hozier123.github.io/sdc-2026-team-project/ |
| Replit project / deployment | Backend https://kiraorder-api.replit.app; legacy frontend https://kiraorder-web.replit.app |
| RunPod endpoint | https://lx22t9308hc10c.api.runpod.ai; currently `Active=0`; see `evidence/runpod/2026-10-24/` |
| Slide deck | [KiraOrder Falcons Pitch Deck](submission/KiraOrder_Falcons_PitchDeck_SDC2026.pptx) |
| YouTube pitch and prototype demo | https://youtu.be/TyrASSJDIpM |
| Official proposal | [`submission/SDC2026_Falcons_Preliminary.pdf`](submission/SDC2026_Falcons_Preliminary.pdf) — signed 2026/10/25 |
| Technical and tools declaration | [`submission/SDC2026_Falcons_TechDeclaration.pdf`](submission/SDC2026_Falcons_TechDeclaration.pdf) — signed 2026/10/25 |
| Platform-use proof | Reproduced in `submission/SDC2026_Falcons_TechDeclaration.pdf` Appendices B–D; screenshots archived under `evidence/runpod/2026-10-24/` |

Official file names use the actual team name:

- `SDC2026_TeamName_Preliminary.pdf`
- `SDC2026_TeamName_TechDeclaration.pdf`

## Replit usage

The backend uses Replit Core, Autoscale (2 vCPU / 4 GiB), region Asia, with public domain `https://kiraorder-api.replit.app`. The primary frontend deployment has moved to GitHub Pages; `https://kiraorder-web.replit.app` remains as a legacy/old UI and is not the final review entry point. Replit Core is self-funded by He Minghao. Ye Lianghui's Replit Agent usage is covered by platform sponsor/credit; details are in the Technical & Tools Declaration.

## RunPod usage

The RunPod Serverless Load Balancer endpoint is `lx22t9308hc10c`, serving Qwen2.5-7B-Instruct-AWQ through vLLM on a 24 GB GPU. It is currently `Active=0` with 0 workers, and public parse falls back. Usage proof is in `evidence/runpod/2026-10-24/`, including overview, workers-zero, and shutdown logs. RunPod has approximately US$25 of sponsor credit; 0 workers must not be described as continuous availability.

## Submission check

See [docs/competition-checklist.md](docs/competition-checklist.md). A completed directory template does not mean the competition materials are complete, and uploading to GitHub does not mean the official entry has been submitted. Verify the runnable prototype and supplied documentation, platform proof, slides, and video; open review access as required, and submit the entry on the official site.

## License and provenance

[Apache License 2.0](LICENSE) is retained. Initial materials came from the official SDC GitHub submission template; this directory follows Appendix B of the team's final execution plan. The final submission must declare the template, third-party resources, and actual use of AI-assisted tools.
