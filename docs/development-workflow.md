# Repository development and frozen baselines

For the product overview, judge walkthrough and current recorded deployment, see the [project README](../README.md). This page keeps repository conventions, historical setup notes and frozen-baseline provenance together.

## Repository conventions and baseline provenance

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
|   |-- SDC2026_Falcons_Final.pdf            # Signed final solution report (Phase 2)
|   |-- SDC2026_Falcons_PRD.pdf              # Updated PRD (Phase 2)
|   |-- SDC2026_Falcons_TechDeclaration.pdf  # Signed final tools declaration and platform evidence
|   |-- SDC2026_Falcons_Preliminary.pdf      # Phase 1 signed proposal (reference)
|   |-- SDC2026_Falcons_PitchDeck.pptx       # Editable final pitch deck
|   |-- SDC2026_Falcons_PitchDeck.html       # Self-contained live pitch deck
|   |-- SDC2026_Falcons_Deck_Appendix.pptx   # Technical appendix deck
|   |-- Replit_Usage_Proof_Falcons.pdf
|   |-- RunPod_Usage_Proof_Falcons.pdf
|   `-- PORTAL_SUBMISSION_CONFIRMATION_2026-10-25.png  # Phase 1 portal receipt
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

Gate 0 is frozen at [`gate0-baseline-v1`](https://github.com/Hozier123/sdc-2026-team-project/tree/gate0-baseline-v1), commit `3478c31fbbcaf295130e87a992ccdff1a4fabf8e`, corresponding to internal `gate0-v4 / draft revision 5`. The formal four-party confirmation is in the [Gate 0 confirmation](../evidence/gate0/%E7%A1%AE%E8%AE%A4%E4%B9%A6.md) and the [evidence binding notes](../evidence/gate0/README.md). The pending-signature state in `gate0/docs/gate0-signoff.md` and the manifest preserves the preparation snapshot; final confirmation is based on the external evidence and the tag above. Maintenance notes do not rewrite the frozen snapshot or move the tag.

The later v1.3 working documents 01-04 are under `docs/rules/` and are updated with the backend implementation. The v1.2 originals under `gate0/external-inputs/protected/` remain in place.

## Historical scaffold and collaboration notes

A runnable backend service and frontend workspace already exist. Do not run the old `python src/main.py`. The old root `src/`, `runpod/`, example tests, demo-only `requirements.txt`, and `.replit` were removed from the current version; history remains in earlier commits.

Members who already have a local copy should preserve their changes and run `git pull --ff-only`. The real `.env` file is ignored by Git.

## Implementation inventory

```text
Implemented and covered by automated tests:
identity/tenant permissions, seed, PII masking, parse, catalogue resolution,
customer memory, field evidence, draft save/status, conditions and clarification,
trilingual replies, approval/DO/inventory transactions, customer/draft/approval/
activity/audit/warehouse reads, AI status and wake-up, in-process RunPod adapter
(disabled by default), six-case evidence runner, three checks_enabled soft checks,
concurrency/rollback, export evidence binding, and contract fixture regression.
```

This inventory describes implemented code and automated-test scope. Acceptance boundaries and links to evaluation evidence are maintained in the project README.
