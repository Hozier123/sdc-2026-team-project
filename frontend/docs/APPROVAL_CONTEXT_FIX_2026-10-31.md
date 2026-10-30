# Approval request context and price-summary fixes

## Behavior

Approval rows now show the full submission date and time in MYT, a short draft ID, the saved version, and the requester. The detail header repeats the same draft ID and timestamp. The existing API supplies `requested_at`, so the label is **Submitted**; this change does not claim to add the order creation time or fetch each draft separately.

The low-price reason summary now reads the live backend's `tier_unit_price` and `effective_unit_price`. It retains compatibility with `tier_price` and `applied_price` used by the frozen fixtures and local demo. Missing or invalid values render as a dash instead of an invented RM0.00. For the reported example, the summary displays RM19.00 to RM17.00.

## Validation

- Node 22.22.1: 63 tests passed, including four regression tests for midnight/date formatting, same-customer request identities, live/legacy price fields, and missing versus zero prices.
- Standard production build passed, including the unchanged frozen-contract type check.
- Real-browser checks at 1440, 768, and 390 pixels used two synthetic requests for the same customer at the same clock time on different dates. Both dates and draft IDs remained visible; metadata rendered at 13px; the settled document width matched the viewport at all three sizes.
- The rendered detail summary showed RM19.00 to RM17.00 with the live backend field names.
- Source lint retained its baseline decorative-star finding and existing label warnings outside the changed list. Before/after layout inspection retained the same existing button-effect, heading, and whitespace findings. This is a scoped information fix, not a clean-style certification or a redesign.

## Scope

Based on the current 1.4.0 frontend. No backend routes, frozen contracts, dependency files, approval permissions, pending-order data, pricing calculations, or deployment were changed. Browser checks used local synthetic data and do not complete the live C04 business acceptance. Local QA screenshots and operator screenshots are not part of this code change.
