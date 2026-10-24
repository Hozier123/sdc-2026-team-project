# Canonical six samples — source of truth

The single source of truth for the six canonical samples is:

```text
docs/ai_contract/samples/{normal,ambiguous,condition,empty,multi_candidate,multi_line}.json
```

This directory stores only the **blob SHA-256 manifest**. It does not duplicate the JSON files, avoiding two competing versions.

Scoring scope:

```text
family_scored=false
GENERIC_CONTRACT_SAMPLE
Score only span / qty / uom / pack_size / conditions
```

For reproduction, verify the source files against the blob hashes in `SHA256.txt`. Run the six samples directly from `docs/ai_contract/samples/`; do not obtain a second copy from this directory.

Final six-case evidence is `evidence/he_6cases_final_2026-10-24.txt`. Its header references the same source paths and SHA values.
