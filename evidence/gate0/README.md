# Gate 0 confirmation evidence

This directory is deliberately separate from `../../gate0/`. Evidence may be
added without changing the byte-for-byte Gate 0 baseline.

## Imported evidence

- `确认书.md`: the four-party confirmation record supplied by the team.
- Evidence SHA-256: `D6F0494FBB5ABF81665530478E0ABF22452E2C691F205BBF928A52F164A36C76`.
- Intended Git tag after final consistency review: `gate0-baseline-v1`.

## Baseline binding

- Baseline directory: `../../gate0/`.
- Controlled-file list: `../../gate0/docs/gate0-hashes.txt`.
- Controlled-file count in the imported baseline: **73**.
- `gate0-hashes.txt` SHA-256: `6A44089C623C1B4AE8F444660DBD89422C663E7EBDD141EA6FDA549DDD833770`.
- Upstream `main` used for the import: `dca7075bf8638522fc416ff9dc08a6f88bcc6435`.

## Consistency note

The supplied confirmation record names `draft revision 2` and states that the
hash file contains 53 controlled outputs. The imported Gate 0 manifest names
`draft revision 5`, and its hash file contains 73 controlled files. The
confirmation record is preserved exactly as received; it has not been silently
rewritten. Do not create the immutable Git tag until the team confirms that the
four approvals apply to the 73-file revision 5 baseline, or supplies corrected
confirmation text.
