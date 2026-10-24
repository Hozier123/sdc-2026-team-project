# Frontend recording release gate

Status: candidate; review, CI, merge, final deployment and deployed regression are still required. Do not start formal recording from this candidate.

## Scope

This candidate carries the existing standalone frontend's workbench, copy, responsive layout and theme changes into the team repository. The final 11-file standalone change depends on presentation changes that are not yet on the team's main branch, so the team PR includes those frontend prerequisites.

All changed paths must be under `frontend/`. Preserve the team API adapter, generated contract, same-day-order workflow and clarification-copy audit callback. Do not change backend, seed data, tokens, GitHub Actions or deployment configuration.

## Gates, in order

1. Submit a separate branch and PR with `git diff --stat`, `npm test`, `npm run build`, and commit/PR links.
2. Obtain review approval for the current PR revision and passing CI before merging. Local self-checks do not substitute for reviewer approval.
3. Build again from the clean merged revision. Republish only GitHub Pages, as selected by the user; do not update Replit. Record the source commit, Pages commit and deployment result. Use the build CLI's base-path option without changing deployment configuration in this PR.
4. Verify the deployed build in Local Demo at desktop, tablet and phone widths, in dark and light themes. Check workspace, action bar, order review, owner approval and delivery order. Confirm the target demonstration order is accessible in the recording browser. Save screenshots and the tested deployment revision.
5. Mark the release ready for recording only after all preceding gates pass. Formal recording must use that final deployment and must not depend on uncommitted files.

## Feature freeze after acceptance

After the gates pass, no new features or visual refinements are permitted. Only blocker bug fixes may proceed. Every fix requires another PR, CI, deployment and deployed regression. If visible output changes, re-record the affected footage.

## Candidate validation

- `npm test`: 59 passed, 0 failed.
- `npm run build`: frozen contract type check, TypeScript and Vite passed.
- API adapter, generated contract, dependency manifests and deployment configuration remain unchanged.
- Candidate validation is not evidence that the final deployment has passed regression.
