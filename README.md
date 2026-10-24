# KiraOrder for Orbyte

SDC Hackathon 2026 - Domain 2 - Orbyte Smart SME Challenge

KiraOrder helps Malaysian wholesalers turn mixed-language WhatsApp-style orders into reviewable drafts, route exceptions to the right person, and keep approval decisions traceable.

Explore the workflow through the browser-only Local Demo, using synthetic data without backend or model calls.

## Project links

- [Interactive Local Demo](https://hozier123.github.io/sdc-2026-team-project/) - no login required.
- [Pitch video and prototype demonstration](https://youtu.be/TyrASSJDIpM).
- Pitch deck: [View PDF](submission/KiraOrder_Falcons_PitchDeck_SDC2026.pdf) · [Download editable PowerPoint](submission/KiraOrder_Falcons_PitchDeck_SDC2026.pptx).
- [Submission documents, platform proofs and file hashes](submission/README.md).

## Prototype status

- **Try:** a browser-only Local Demo covering order review, owner decisions, delivery orders and warehouse views with synthetic data.
- **Evidence:** backend automated tests and standalone RunPod evaluation records are archived in the repository.
- **Pending:** integrated live-AI validation, complete workflow testing, independent UAT and real-user trials. See [implementation and evaluation status](#implementation-and-evaluation-status) for the measured results and known gaps.

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
- If the prototype cannot be reached, the [pitch and demonstration video](https://youtu.be/TyrASSJDIpM) and [pitch deck PDF](submission/KiraOrder_Falcons_PitchDeck_SDC2026.pdf) provide supporting material; they do not replace an interactive review.

### Controlled access to the real API

API review is **by arrangement with the team**. This README does not publish or provision a judge token, and no authenticated review window is guaranteed by these instructions alone.

1. Contact the team leader through the competition portal's existing team contact or an organizer-mediated private channel. Request an API review session; the team leader coordinates access with the backend maintainer. Do not exchange credentials in a public GitHub issue.
2. Before review, the team should privately provide the designated synthetic tenant, the permitted role, a working role-specific session token, the agreed review window, and a private support contact. If comparing **CLERK**, **OWNER**, and **WAREHOUSE**, request separate role-bound sessions. Do not use database credentials or a RunPod key as a frontend session token.
3. Open GitHub Pages, save or discard demo edits, and choose **Connect API**. Enter API base **https://kiraorder-api.replit.app/api/v1** and the privately supplied token in **Session token**, then click **Connect API**. The frontend verifies the session through `/me`; confirm the returned workspace and role before creating synthetic records.
4. In API mode, the backend determines identity and permissions. To review another role, reconnect using that role's supplied session; the demo role selector cannot grant API privileges. Tokens remain in the current tab's memory. Refreshing returns to Local Demo; **API connection → Return to demo** also exits the connection.
5. If the token is missing, rejected, inactive, or not supplied, use Local Demo and contact the team privately. The [backend readiness check](https://kiraorder-api.replit.app/readyz) tests service readiness, not identity, model readiness, or end-to-end order completion.

See the [deployment snapshot](#deployment-snapshot) for the recorded model configuration and fallback status. A live-AI review requires an agreed model window and a freshly verified end-to-end path. Use Local Demo if API access has not been arranged.

For implementation details and historical evidence, see the [AI sample runbook](docs/ops/ai-sample-runbook.md) and [RunPod evidence](evidence/runpod/2026-10-24/README.md). The detailed [operator guide (Chinese)](frontend/docs/KiraOrder_使用说明.md) explains individual controls; its dated deployment notes are historical, so use this root README for the current recorded deployment status.

## Architecture and deployment

The React/TypeScript frontend runs on GitHub Pages. FastAPI runs on Replit and connects to Neon PostgreSQL for workflow records. A separately configured extraction path uses the in-process RunPod adapter to call Qwen2.5-7B-Instruct-AWQ through vLLM.

Local Demo is an independent browser-only mode; the deployment and evaluation records below describe separate system components.

| Component | Host or entry point |
| --- | --- |
| Primary frontend | [GitHub Pages](https://hozier123.github.io/sdc-2026-team-project/) |
| Backend API base | `https://kiraorder-api.replit.app/api/v1` |
| Backend readiness | [`/readyz`](https://kiraorder-api.replit.app/readyz) |
| Database | Neon PostgreSQL 17; credentials are private |
| Model endpoint | `https://lx22t9308hc10c.api.runpod.ai`; [RunPod evidence](submission/RunPod_Usage_Proof_Falcons.pdf) |
| Legacy frontend | [Replit frontend](https://kiraorder-web.replit.app), retained as an older UI |

### Deployment snapshot

The deployment note dated **25 October 2026** records `AI_PROVIDER=runpod_adapter` and public parsing using fallback. The archived RunPod console snapshot dated **24 October 2026** shows zero active workers. These are recorded observations; live-AI availability requires a newly verified session.

Deployment decisions and checks are documented in [public-deployment-decision.md](docs/ops/public-deployment-decision.md) and [public-deployment-checklist.md](docs/ops/public-deployment-checklist.md).

## Run locally

Clone the repository and create a private environment file:

```powershell
git clone https://github.com/Hozier123/sdc-2026-team-project.git
cd sdc-2026-team-project
if (-not (Test-Path -LiteralPath .env)) {
    Copy-Item -LiteralPath .env.example -Destination .env
}
```

The backend uses Python 3.13 and PostgreSQL 17. Install dependencies, configure the database and run explicit migrations as described in [backend/README.md](backend/README.md). [Windows setup](docs/setup-windows.md) provides additional installation steps.

The frontend uses Node.js 22 and npm. In `frontend/`, run `npm ci` and `npm run dev` (default `http://127.0.0.1:5173/`). To connect to a local backend, set `VITE_API_BASE_URL` in `.env.local`, or enter API base `http://127.0.0.1:8000/api/v1` and the session token through **Connect API**. The current Vite configuration does not enable an API proxy. Frontend checks are `npm test` and `npm run build`; details are in [frontend/README.md](frontend/README.md).

Repository conventions, the full directory layout, Gate 0 freeze records and implementation inventory are in [development-workflow.md](docs/development-workflow.md).

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

The in-process `OrderAiAdapter` is enabled only with `AI_PROVIDER=runpod_adapter`; it requires `RUNPOD_API_KEY` and `RUNPOD_ENDPOINT_ID`. The code default is `auto` (Stub when `AI_SERVICE_URL` is absent). There is no `/api/v1/extract`; AI is invoked in-process by `parse-draft`.

Real secrets belong only in the local environment or Replit Secrets, never in code, documentation, or screenshots. Business demonstrations use only team-created synthetic data. The six-case evidence runner is documented in [docs/ops/ai-sample-runbook.md](docs/ops/ai-sample-runbook.md).

## Implementation and evaluation status

Automated tests cover identity and tenant permissions, parsing and draft rules, owner approval, delivery orders, inventory transactions, evidence export and contract regressions. See [GitHub Actions](https://github.com/Hozier123/sdc-2026-team-project/actions) for backend and frontend CI, and the [backend audit](docs/audit/backend-audit-2026-10-23.md) for implementation scope.

The latest recorded local backend **non-integration** run has **307 passed**. Full integration tests require `TEST_DATABASE_ADMIN_URL`; that result does not represent the complete integration suite.

| Evidence | Recorded result and boundary |
| --- | --- |
| AI-only production run | 23/23 LLM calls, zero fallback; accuracy remains `NOT_COMPUTED` |
| Final six-case set | 5 PASS / 1 KNOWN_LIMITATION |
| Unit-of-measure check | 24/31, with 7 known gaps |
| TEST32 workflow cases | 12 remain `NOT_RUN`; full workflow acceptance is incomplete |
| Independent UAT and real-user trials | Outstanding; UAT is planned for Phase 2 |

The [evidence index](evidence/EVIDENCE_INDEX.md) links the evaluation records. The [AI evaluation intake](docs/ops/ai-evaluation-intake.md) explains their scope. The [data-side sign-off](evidence/data-signoff/2026-10-23.md) covers seed counts and import evidence; business-field acceptance, AI accuracy and UAT require separate review.

## Submission materials

| Material | Link |
| --- | --- |
| Signed official proposal | [SDC2026_Falcons_Preliminary.pdf](submission/SDC2026_Falcons_Preliminary.pdf) |
| Signed technical and tools declaration | [SDC2026_Falcons_TechDeclaration.pdf](submission/SDC2026_Falcons_TechDeclaration.pdf) |
| Pitch deck | [PDF](submission/KiraOrder_Falcons_PitchDeck_SDC2026.pdf) · [Editable PowerPoint](submission/KiraOrder_Falcons_PitchDeck_SDC2026.pptx) |
| Pitch and prototype video | [YouTube](https://youtu.be/TyrASSJDIpM) |
| Replit usage proof | [Replit_Usage_Proof_Falcons.pdf](submission/Replit_Usage_Proof_Falcons.pdf) |
| RunPod usage proof | [RunPod_Usage_Proof_Falcons.pdf](submission/RunPod_Usage_Proof_Falcons.pdf) |
| Final file inventory and SHA-256 hashes | [submission/README.md](submission/README.md) |

The project’s GitHub repository link has been registered in the official submission portal. A [confirmation screenshot](submission/PORTAL_SUBMISSION_CONFIRMATION_2026-10-25.png) is archived. This records repository-link registration; runtime API validation is documented separately.

Use the [competition checklist](docs/competition-checklist.md) to verify that the portal repository link and linked submission materials match the intended final version.

## Platform usage

**Replit:** the backend deployment uses a self-funded Core account with Autoscale (2 vCPU / 4 GiB), region Asia. A separate member account used sponsored Replit Agent assistance for frontend development. The primary UI is on GitHub Pages. Account boundaries and the missing sponsored-account Usage screenshot are recorded in the [Replit proof](submission/Replit_Usage_Proof_Falcons.pdf) and [technical declaration](submission/SDC2026_Falcons_TechDeclaration.pdf).

**RunPod:** the Serverless Load Balancer endpoint `lx22t9308hc10c` was used to serve Qwen2.5-7B-Instruct-AWQ through vLLM on a 24 GB GPU, with approximately US$25 in sponsor credit allocated. The [usage proof](submission/RunPod_Usage_Proof_Falcons.pdf) and [original console evidence](evidence/runpod/2026-10-24/README.md) document the evaluation and shutdown snapshots. Refer to the dated [deployment snapshot](#deployment-snapshot) when interpreting availability.

## License and provenance

[Apache License 2.0](LICENSE) is retained. Initial materials came from the official SDC GitHub submission template. Third-party resources, models, sponsor resources and AI-assisted development are described in the [Technical & Tools Declaration](submission/SDC2026_Falcons_TechDeclaration.pdf), including unresolved visual-asset permission records.

Design prompt source:

- [MotionSites - signal-id](https://motionsites.ai/?prompt=signal-id): the design prompt was used with an AI tool to generate the project's frontend page.
