# Frontend upgrade and compatibility review

The 1.5.0 frontend makes connection state, extraction mode, approval checks and order activity easier to inspect. Product fields and price-adjustment controls have stronger contrast and larger text. Receipt content uses Times New Roman on screen and in print; its existing logo retains the brand fonts.

## Integration scope

- Integrated onto team `main` at `0a255df`, rather than replacing the frontend with a standalone repository snapshot.
- All changes are confined to `frontend/`. Backend code, root workflows, submission materials and shared evidence are unchanged.
- Preserved the team's Gate 0 v4 contract, provenance, fixtures and generated types, including `AMBIGUOUS_QUANTITY`.
- Preserved the team's B01 polling while AI status is `WARMING`, plus same-day-order handling, clarification-copy recording and discard endpoints.
- Production build defaults are public API/base-path values only. `.env.production` is narrowly allowed by the frontend ignore rules; other env files remain ignored. Hosting paths can be overridden through `VITE_PAGES_BASE`.
- Session tokens remain in memory. Reload requires reconnection; failed connections do not silently select Demo. Real company, role and permissions come from `/me`.
- Warehouse responses with fields outside the backend's current redacted schema block the view. This frontend check does not replace server-side redaction.

## Verification before submission

| Check | Result |
| --- | --- |
| Clean Node 22 installation | `npm ci --no-audit --no-fund` passed in the integration worktree |
| Frontend tests | 64 passed, 0 failed |
| Full production build | Contract generation check, TypeScript and Vite passed |
| Latest backend schema comparison | 19 synthetic exchanges captured from the actual `HttpService`; matched current FastAPI route methods, request bodies and response schemas |
| Backend selected tests | 62 passed, 5 database tests deselected; contract fixtures, CORS and AI status tests |
| Dependency consistency | Python `pip check` passed |
| Frozen assets | No changes to team contracts, fixtures or generated contract types |

The 19 schema checks cover identity, customers, draft list/detail, parse, save with exact decimal pricing and a same-day resolution, direct approval, escalation (202), approvals, rejection, delivery, warehouse, activity, audit, AI status/wake, clarification-copy recording and discard. Synthetic responses are a schema comparison, not real business execution. A route summary is recorded in [the compatibility result](API_COMPATIBILITY_2026-10-30.json).

The preceding local visual review used desktop/tablet/phone widths (1440/768/390). Connection labels/body/actions are 14px and inputs 16px; review labels are 14px and values 16px. Product-field contrast measured 14.56:1 in dark mode and 14.61:1 in light mode. Browser platform-font checks confirmed Times New Roman in receipt content and the retained brand fonts in the logo. Taste review reported no failures across connection, review, same-day and receipt screens; remaining warnings concern established display typography/layout and the explicitly preserved logo/dialog treatment. Local screenshots and browser storage are excluded from this submission.

## Remaining acceptance and publishing boundary

The PR runs the team's existing frontend CI and PostgreSQL-backed backend CI. Their results must be assessed for this PR revision. Local non-database tests and synthetic schema checks do not establish production CORS, real role-token access, real RunPod extraction, T2 completion, inventory transaction correctness or live deployment compatibility.

The catalog/manual zero-line flow remains gated; it is not enabled without the required backend acceptance. This change introduces no new backend endpoint or state-machine transition.

This is a source-code submission. It does not merge `main`, publish GitHub Pages, alter backend deployment, reset business data or use a force push. A separate deployment should verify the actual hosting prefix and public API connection.
