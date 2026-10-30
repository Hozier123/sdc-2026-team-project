# KiraOrder for Orbyte · Frontend

A mixed-language order message becomes a traceable delivery order after review and human approval.

The [operator guide (Chinese)](docs/KiraOrder_%E4%BD%BF%E7%94%A8%E8%AF%B4%E6%98%8E.md) covers quick start, clerk review, owner approval, warehouse picking, API connection, and common issues.

The [guide-to-plan comparison (Chinese)](docs/KiraOrder_%E4%BD%BF%E7%94%A8%E8%AF%B4%E6%98%8E%E4%B8%8E%E6%96%B9%E6%A1%88%E7%BB%86%E8%8A%82%E5%AF%B9%E7%85%A7.md) maps the guide to the final plan, Gate 0 contracts, and implementation, identifying incomplete features and integration work.

This README preserves frontend development and validation checkpoints. For the latest recorded public deployment, review access, and limitations, use the [root README](../README.md).

## Start

Node.js 22 and npm are required. Run `npm ci` on first use, then:

```sh
npm run dev
```

Open http://127.0.0.1:5173/ in a browser. On macOS, you can also double-click the [launcher](%E5%90%AF%E5%8A%A8%20KiraOrder.command).

- Current introduction: `/`, using `PlanetGreeting` for 3D language orbits and scroll-driven storytelling. Click or tap the page to enter the workspace; an entry hint remains at the bottom. Enter / Space also enters; scrolling or swiping continues the story.
- The original 70% scale introduction remains at `/intro.html` for compatibility. Fonts, scripts, and backgrounds have been split into local static assets. Both entries keep the workspace at normal scale.
- Direct workspace entry: `/#/workspace`.
- Production build: `npm run build`; build preview: `npm run preview`.
- Automated regression: `npm test`. API tests use frozen Gate 0 synthetic response fixtures in `tests/fixtures`. Request texts are masked; business source materials are not packaged into the website.
- Type contract: `npm run types:check` verifies generated types against frozen OpenAPI; `npm run types:generate` regenerates them. Builds automatically detect type drift.
- Without a real backend: run `npm run mock:api` to start the local fixture service. Through **Connect API**, connect to `http://127.0.0.1:4191/api/v1` using the fixed synthetic identifiers `fixture-clerk` / `fixture-owner` / `fixture-warehouse`. The UI shows **FIXTURE MOCK**. It returns only fixed snapshots and does not parse real orders or call AI. Scenario switching and acceptance are documented in the [frontend independent development record (Chinese)](docs/%E5%89%8D%E7%AB%AF%E7%8B%AC%E7%AB%8B%E5%BC%80%E5%8F%91%E4%B8%8E%E9%AA%8C%E6%94%B6_2026-10-22.md).

## Implemented features

- Streamlined workspace with new-order entry, four order counters, queue, next-order suggestion, and activity. Introductory banners, slogan, and process guidance are on the introduction page.
- Inbox search and status filters; mixed-language order creation; customer tier and credit context.
- Product specification, quantity, stock, unit, and price review; explicit blocking issues; clarification-message copying.
- Target-product selection for price conditions, manual unit price and reason, owner submission, direct approval, and final delivery orders.
- Owner approval snapshots, stock checks, approval and reasoned rejection, and terminal-state locking.
- Delivery-order printing / PDF saving, customer reply copying, activity timelines, and per-field change records.
- Customer-specific phrase memory; separately filtered read-only warehouse views; mobile layouts, focus management, and reduced-motion support.
- Unsaved-change protection; version conflicts, stock changes, and duplicate-approval handling; local refresh recovery.
- Independent activity, approval, and AI-status loading with local retries; writes disabled while saving; inline invalid-quantity checks.
- Conflict recovery explicitly separates retaining edits from discarding them. Retained edits require renewed review and save. Warehouse lines merge by product, unit, and picking requirements.
- Persistent **Privacy & data** entry; per-session automatic warm-up for permitted real sessions and manual wake-up; formal authentication-error prompts; approval/audit before_value and after_value mapping; manual unit prices normalized to two decimal places in requests.

## Demo mode

The default **LOCAL DEMO** separates the UI from the demonstration-data service. Synthetic customers and products exercise business rules without calling AI. Parsing displays **Offline match · non-AI**.

The role selector in the top-right header switches between clerk, owner, and warehouse. The left workspace selector switches between food-wholesale and hardware examples. The warehouse can use `DO-T1-0001` to inspect the initial picking list.

Demo data is stored only in this browser under `kiraorder.demo.v1.T1` / `kiraorder.demo.v1.T2`. Phone numbers, emails, and identity numbers in input are masked before saving. Customer messages and replies are not sent automatically. The demo catalogue matcher uses limited rules; unfamiliar text requires human confirmation and does not replace formal multilingual extraction.

## Connect to a backend

Click **Connect API** in the sidebar and enter a complete API base URL, such as `http://127.0.0.1:8000/api/v1`, and a session Bearer token. User, tenant, and permissions come from `/me`; no self-declared role request headers are sent. Remote APIs require HTTPS; local development can use HTTP.

The session token stays only in memory. Refreshing returns to Local Demo; tokens are not written to files, URLs, or localStorage. The API must allow this frontend's CORS origin and expose `X-Request-ID` for error tracing. Optional `.env.local` setting `VITE_API_BASE_URL` provides only the default URL; **never place secrets in VITE environment variables**.

In a real connection, amounts, status, stock, and `allowed_actions` come entirely from the backend. Only isolated `src/lib/demo.ts` reproduces business rules for demonstration. Normal approval sends only `expected_version`; save quantity/price changes with `PUT lines` first, without deprecated `confirmed_items`.

### Historical backend integration checkpoint

Real backend integration was exercised with PostgreSQL 17.10 and FastAPI at `127.0.0.1:8000`, using frozen contract `1.3.0-gate0-v4`: `GET /me` returned 200, with identity, tenant, role, and permissions supplied by the server. `POST /orders/parse-draft` returned 200, with phone numbers masked by the server to `[REDACTED_PHONE]` before storage. Warehouse parsing returned 403 `FORBIDDEN_ACTION`; an invalid token returned 401 `INVALID_TOKEN`.

At that checkpoint, only part of the contract was implemented. These routes still returned 404: `GET /orders/drafts`, `GET /orders/drafts/{draft_id}`, `GET /customers`, `GET /activity`, `GET /orders/{do_number}/audit-detail`, `GET /warehouse/delivery-orders/{do_number}`, `GET /ai/status`, and `POST /ai/wake`. The full UI workflow depended on completing them. These are historical results, not a fresh assessment of current main.

The P0 contract has no DO-list endpoint; the frontend builds its index from `do_number` in draft summaries and uses the formal DO-read endpoint for details. The warehouse searches by DO number. Real mode does not expose catalogue search, manual line creation, or discard operations without a contract. Local Demo supports explicitly closing an unsubmitted draft.

## Layout

```text
src/App.tsx                        App shell, overview, routes, and connection settings
src/components/orders.tsx          New orders, review, and issue resolution
src/components/fulfillment.tsx     Approval, delivery orders, warehouse, and audit
src/components/ui.tsx              Modals, status indicators, and shared components
src/lib/types.ts                   Gate 0 data shapes and writable projections
src/lib/api.ts                     Real API adapter
src/lib/demo.ts                    Isolated Local Demo data service
src/lib/review.ts                  Picking merge, quantity checks, routes, edit recovery
src/components/PlanetGreeting.tsx  Current 3D introduction, loaded on demand
public/intro.html                  Original 70% scale compatibility entry
public/intro-scene.html            Original starfield scene with split assets
public/assets/intro-fonts.css       Local compressed fonts; no third-party font requests
public/assets/nebula.png           Visual asset extracted from the introduction HTML
scripts/package_delivery.py        Delivery packaging with file-integrity manifest
contracts/gate0.openapi.json       Frozen machine contract, without source documents
src/lib/gate0.generated.ts         Generated types, excluded from the runtime bundle
src/lib/wire.ts                    Contract-field to UI-model adaptation
scripts/fixture_api.mjs            Local fixed-snapshot API, not a production backend
```

See `docs/IMPLEMENTATION_PLAN.md` for the phased plan and `docs/VALIDATION.md` for delivery validation. Source materials and confirmation packages were not modified or uploaded in that work.

Demo role switching illustrates interaction, not real authentication. Browser-local demo records do not provide production permission isolation. Production deployment requires backend token verification, tenant isolation, warehouse field filtering, and approval transactions.

## Review fixes and packaging

The [per-issue repair record (Chinese)](docs/%E5%AE%A1%E6%A0%B8%E9%97%AE%E9%A2%98%E4%BF%AE%E5%A4%8D%E7%BB%93%E6%9E%9C_2026-10-22.md) documents fixes. Local mock-interface verification is not real backend or real AI integration.

Run `npm test` and `npm run build`, then `python3 scripts/package_delivery.py` to create the delivery ZIP in the project parent directory. `DELIVERY_MANIFEST.json` records each delivered file's SHA-256. Packaging verifies every file and excludes dependencies, private environment files, and source materials.

The current 3D page retains remote background video and poster assets from the original implementation; they may be unavailable offline. Business pages do not depend on them. The original 70% compatibility page uses local fonts and backgrounds.

The recorded independent frontend checkpoint passed 55 automated tests, generated-type checks, and the production build. Real API sessions with WAKE_AI permission automatically warm up once on entry; Local Demo and warehouse roles do not. At that checkpoint, real `/me` and `parse-draft` integration was complete, list/detail routes still awaited backend completion, and extraction remained Stub (`ai_mode=FALLBACK`) without live AI. Later deployment and integration updates are in the root README.

## Previews

- [Desktop overview](docs/previews/homepage-desktop.png)
- [Mobile overview](docs/previews/homepage-mobile.png)
- [Introduction · 70%](docs/previews/intro-70-percent.png)

## Frontend upgrade (2026-10-30)

Version 1.5.0 adds explicit Demo/API connection status, memory-only sessions with reconnect after reload, per-order extraction mode, linked activity views, and warehouse response redaction checks. The review form and delivery document now have improved readability; only receipt content uses Times New Roman, preserving the logo.

Use Node 22 (`.nvmrc`), then `npm ci`, `npm test`, and `npm run build`. Public production defaults in `.env.production` target `/sdc-2026-team-project/` and the public API. Override `VITE_PAGES_BASE` for other hosting paths. Session tokens must never be placed in VITE variables or committed env files.

See [integration and compatibility checks](docs/FRONTEND_UPGRADE_INTEGRATION_2026-10-30.md) for the verification scope and remaining live acceptance. Source submission does not publish the production site.
