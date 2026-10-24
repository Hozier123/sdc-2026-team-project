# Gate 0 confirmation evidence

This directory is deliberately separate from `../../gate0/`. Evidence may be
added without changing the byte-for-byte Gate 0 baseline.

## Imported evidence

- [Four-party confirmation record](%E7%A1%AE%E8%AE%A4%E4%B9%A6.md) supplied by the team.
- Evidence SHA-256: `ED0366A7FE23B7114741D2AC2C5A681B1425DB9F6C94B817579B816F2F82E48E`.
- Frozen Git tag: [`gate0-baseline-v1`](https://github.com/Hozier123/sdc-2026-team-project/tree/gate0-baseline-v1).
- Tag commit: `3478c31fbbcaf295130e87a992ccdff1a4fabf8e`.

## Baseline binding

- Baseline directory: `../../gate0/`.
- Controlled-file list: `../../gate0/docs/gate0-hashes.txt`.
- Controlled-file count in the imported baseline: **73**.
- `gate0-hashes.txt` SHA-256: `6A44089C623C1B4AE8F444660DBD89422C663E7EBDD141EA6FDA549DDD833770`.
- Upstream `main` used for the import: `dca7075bf8638522fc416ff9dc08a6f88bcc6435`.

## Confirmation binding

Following the team's explicit authorization, the four confirmation blocks are
bound to `gate0-v4` / `draft revision 5`, all 73 controlled files, and the
`gate0-hashes.txt` SHA-256 shown above. The originally supplied confirmation
times and role-specific approval statements are retained.

The pending-signoff status inside `gate0/docs/gate0-signoff.md` and
`gate0/baseline-manifest.json` records the preparation snapshot. Final approval
is recorded in this external evidence and the frozen tag. Preserve the snapshot
bytes and the tag target; subsequent evidence may be appended outside `gate0/`.
