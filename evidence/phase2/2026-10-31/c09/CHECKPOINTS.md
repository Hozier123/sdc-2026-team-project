# C09 manual UI checkpoint map

Executor: Ye. Independent reviewer per plan: Zhou. Review status: PENDING.

The executor authorized publishing these 12 original UI screenshots in this review PR. Filenames below link to the images in this directory.

| Checkpoint | Screenshot | Observation |
| --- | --- | --- |
| T2 workspace and clerk role | [01-t2-workspace.png](01-t2-workspace.png); [02-clerk-permissions.png](02-clerk-permissions.png) | Kilat company label, Order clerk, green API indicator. No raw /me response captured. |
| T2 saved order and baseline | [03-t2-draft-created.png](03-t2-draft-created.png); [04-t2-saved-ready-baseline.png](04-t2-saved-ready-baseline.png) | Kedai Kilat 01, Tier A, Liquid soap 2 btl 1L input, saved v1, 2 btl at RM12, RM24 total, stock 40. UI label: AI extraction. |
| Delivery order | [05-t2-delivery-order.png](05-t2-delivery-order.png) | DO_20261030_7ACFA8AF, 2 btl at RM12, RM24 total, USR_T2_CLERK, saved v1, read-only. |
| Current-order audit | [06-t2-approval-trail.png](06-t2-approval-trail.png) | Inventory deduct and Approve, USR_T2_CLERK, 31 Oct 2026 02:47 MYT. No changed fields. |
| Fresh stock comparison | [07-fresh-draft-stock-after-approval.png](07-fresh-draft-stock-after-approval.png) | New unapproved draft shows 38 btl, versus baseline 40. Same-day order check also present. UI evidence only. |
| Stock auxiliary cleanup | [08-stock-verification-draft-closed.png](08-stock-verification-draft-closed.png) | Closed with explicit verification reason. |
| Missing pack size | [09-t2-pack-ambiguity-blocked.png](09-t2-pack-ambiguity-blocked.png) | Unselected 1L/RM12/38 and 5L/RM45/20 candidates, pack-size and same-day checks; Resolve checks control. |
| Ambiguity auxiliary cleanup | [10-pack-ambiguity-draft-closed.png](10-pack-ambiguity-draft-closed.png) | Closed with explicit test reason. |
| T1 access to T2 order | [11-t1-cross-tenant-order-not-found.png](11-t1-cross-tenant-order-not-found.png) | Sinaran Food Supply identity; target approved T2 draft returns RESOURCE_NOT_FOUND in UI, no order content displayed. |
| T1 access to T2 DO | [12-t1-cross-tenant-delivery-not-found.png](12-t1-cross-tenant-delivery-not-found.png) | Sinaran Food Supply identity; target DO returns RESOURCE_NOT_FOUND in UI, no delivery content displayed. |

## Evidence boundaries

This is a manual UI acceptance sequence, not independent signoff or direct backend/DB proof. No raw HTTP responses, HTTP status captures, deployment SHAs, DB queries, or concurrency checks were collected. The approved order's stored SKU/pack snapshot was not exposed by the change-only audit dialog. Its original input specifies 1L; price and stock agree with the separately displayed 1L candidate, but the stored SKU still lacks direct confirmation. The DO line description also omits the pack size. The AI extraction label alone does not prove provider execution.
