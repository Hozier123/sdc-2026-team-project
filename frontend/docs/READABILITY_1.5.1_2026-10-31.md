# Candidate and order-field readability — 1.5.1

Candidate pack sizes/grades now use 18px full-ink text instead of the legacy 11px caption. Quantity, unit, available stock, tier price and subtotal values use 18px instead of 16px; their value rows align at 46px. Existing 14px field labels, right-aligned subtotals and amber insufficient-stock values are retained. Long values can wrap on narrow screens.

The existing Marcellus Regular face is retained. Price-adjustment inputs remain at their earlier 16px scale; receipt typography is unchanged.

## Integration

This change applies the local readability follow-up to team main at `5733304`. It preserves the catalog client, approval-context handling, backend integrations and other work merged after PR #74. Only the candidate specification class, scoped review styles and documentation are changed. No backend, contract, workflow or dependency changes are needed.

The application and package versions remain **1.5.1**, as requested. Older 1.4.0 screenshots are the visual comparison; field contrast and 14px/16px field typography were already improved in PR #74. This update adds the remaining 18px specification/value treatment rather than repeating the earlier implementation.

## Verification

- Clean Node 22 install; all 74 current frontend tests passed.
- Full contract type check, TypeScript and production build passed with version 1.5.1.
- Actual components checked in dark/light themes at 1440, 768 and 390px: specifications and all five field values measured 18px, labels 14px, value rows 46px, no horizontal overflow. Measured text contrast stayed above 4.5:1 in all six cases.
- Scoped review-style taste lint: 0 FAIL, 0 WARN. Prior local taste browser review of these same styles reported 0 FAIL and 5 retained WARN in each theme, for existing heading/ID hierarchy, semantic selection/status borders and independent column heights. The latest-main integration was rechecked through the actual-component measurements above; this is not a new full-site audit.
- Private screenshots, browser storage, local QA pages and credentials are excluded from the source submission.

The browser preview uses synthetic Demo data and establishes layout/readability, not production business acceptance. This source submission does not merge the PR or deploy the production site.
