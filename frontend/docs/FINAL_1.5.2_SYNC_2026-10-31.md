# Final frontend 1.5.2 source synchronization

Date: 2026-10-31 (Asia/Shanghai).

At the #119 handoff, the supplied [frontend change summary](../../docs/CHANGELOG_1.4.0_TO_1.5.2_2026-10-31.md)
was an intake snapshot. It has since been updated with the later 1.5.2 responsive fixes.
This source note and the summary are not a GitHub Pages deployment record.

## Source alignment

- The sender's functional snapshot `ca9bac0` and team `main` commit
  `e0094f573ab00dde05402bc67a26b15f9d5d9f01` have identical Git trees.
  PR #118 already integrated the final readability/navigation work on top of the
  catalog, manual recovery, approval history and existing connection flows.
- This synchronization sets the frontend package version, lockfile root version,
  lockfile root-package version and `APP_VERSION` badge to **1.5.2**. Third-party
  dependency versions remain unchanged.
- No product behavior, API contract, frozen fixture, seed, database schema or backend
  application code changes are needed. `backend/app` and `backend/tools` match the
  verified deployed application source
  `520556cd64a7e6e6a17dfe84d0cdd386d0fef94e`; the later backend difference is test coverage.
- The old local B04 working tree has uncommitted work. Synchronization uses a clean
  worktree based on current `main`, preserving that work in its original location.

## Verification of this version

- Clean `npm ci --no-audit --no-fund`; all **79 frontend tests pass**.
- `npm run build` passes: frozen-contract type check, TypeScript and Vite, with
  `/sdc-2026-team-project/` and `https://kiraorder-api.replit.app/api/v1`.
- `scripts/verify_pages_dist.py` passes for all 31 build files, including entry assets,
  the hosting prefix and production API address.
- All **479 backend non-integration tests pass**. Ruff lint and formatting pass for
  all 102 Python files. The Gate 0 baseline remains unchanged.
- Deployed API checks pass **52/52**, including the 19 route/method pairs used by
  `HttpService`, role-derived identity, catalog field limits and Pages CORS/preflight.
- The actual TypeScript `HttpService` passes **8/8** read-only checks against the
  deployed API: identity, catalog, customers, drafts, draft detail, scoped activity,
  AI state and non-fixture connection. Session credentials are not stored in evidence.
- PostgreSQL-backed workflow checks run on a fresh local cluster with synthetic
  sessions. Their results and the final source-to-Pages binding are recorded in the
  release evidence, rather than inferred from the version string.

## Publishing and remaining scope

The previous Pages artifact was `c78c96fdf969d2d26bfafcf6aff0320c40d4ebab`,
built from `e0094f5` and displaying 1.5.1. Publishing 1.5.2 must bind the merged source
commit to `release.json` and verified asset hashes; this source note alone does not
prove that Pages has changed. The backend application does not require redeployment.

The deployed AI status observed during this check is **OFFLINE**. No model wake,
inference, production order write, stock update or reset is part of these online
checks. Existing UOM 24/31, seven known model gaps, B05 independent trials and formal
TEST32 acceptance retain their separately recorded scope.
