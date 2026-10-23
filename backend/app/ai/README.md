# AI core modules (ported)

Ported from AI handoff dated 2026-10-23 into the backend application package.

## Included

```text
adapter.py    OrderAiAdapter / H1 / H5 / FieldEvidence
extractor.py  RunPod OpenAI-compatible client + fallback
fallback.py   deterministic RapidFuzz fallback + lexicons
prompt.py     LLM prompt and response models
__init__.py   fallback exports
```

## Intentionally not ported

```text
warmup.py
  The AI handoff version has known defects and must not be mounted.
  Backend AI status/wake is owned by app.ai_status (B29).

privacy/pii.py
  Backend PII masking is owned by app.pii.
```

No `/ai/*` or `/api/v1/extract` route is added by this package. It is an
in-process module called from the parse-draft pipeline.

Runtime dependency added: `rapidfuzz==3.14.6`.

`catalog.py` builds the per-tenant `family_id -> aliases` mapping from
`product_families` and `family_aliases`. It is the catalog injected into
`OrderAiAdapter.adapt`; it does not contain hard-coded family IDs.

The ported tests are under `backend/tests/ai_handoff/`; the 8 warmup tests and
8 duplicate PII tests are intentionally excluded because those concerns are
covered by the existing backend B29/PII suites.
