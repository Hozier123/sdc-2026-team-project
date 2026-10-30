# C08 WAREHOUSE 权限矩阵（API 层）

- 执行时间：2026-10-30T16:28:14+08:00 — 2026-10-30T16:28:28+08:00（UTC+8）
- Base URL：`https://kiraorder-api.replit.app/api/v1`
- 用例：41/41 通过

| # | 用例 | 角色 | 请求 | 期望 | 实际 | 结果 |
|---|---|---|---|---|---|---|
| 1 | `identity.me_t1_warehouse` | T1_WAREHOUSE | `GET /me` | [200] | 200 | PASS |
| 2 | `identity.me_t1_clerk` | T1_CLERK | `GET /me` | [200] | 200 | PASS |
| 3 | `identity.me_t2_warehouse` | T2_WAREHOUSE | `GET /me` | [200] | 200 | PASS |
| 4 | `identity.me_no_token` | - | `GET /me` | [401] | 401 | PASS |
| 5 | `identity.me_bad_token` | BAD | `GET /me` | [401] | 401 | PASS |
| 6 | `read.customers` | T1_WAREHOUSE | `GET /customers` | [403] | 403 | PASS |
| 7 | `read.drafts_list` | T1_WAREHOUSE | `GET /orders/drafts` | [403] | 403 | PASS |
| 8 | `read.draft_detail` | T1_WAREHOUSE | `GET /orders/drafts/DRF_39D4D66CACC440A594B1C1AEBEF151B9` | [403] | 403 | PASS |
| 9 | `read.approvals_list` | T1_WAREHOUSE | `GET /approvals` | [403] | 403 | PASS |
| 10 | `read.approval_detail` | T1_WAREHOUSE | `GET /approvals/APR_C08_PROBE` | [403] | 403 | PASS |
| 11 | `read.activity` | T1_WAREHOUSE | `GET /activity` | [403] | 403 | PASS |
| 12 | `read.audit_detail` | T1_WAREHOUSE | `GET /orders/DO_20261029_453C4BC2/audit-detail` | [403] | 403 | PASS |
| 13 | `read.delivery_order` | T1_WAREHOUSE | `GET /delivery-orders/DO_20261029_453C4BC2` | [403] | 403 | PASS |
| 14 | `read.ai_status` | T1_WAREHOUSE | `GET /ai/status` | [200] | 200 | PASS |
| 15 | `read.warehouse_do` | T1_WAREHOUSE | `GET /warehouse/delivery-orders/DO_20261029_453C4BC2` | [200] | 200 | PASS |
| 16 | `read.warehouse_do_missing` | T1_WAREHOUSE | `GET /warehouse/delivery-orders/DO_C08_PROBE` | [404] | 404 | PASS |
| 17 | `read.warehouse_list_absent` | T1_WAREHOUSE | `GET /warehouse/delivery-orders` | [404] | 404 | PASS |
| 18 | `read.clerk_do_full` | T1_CLERK | `GET /delivery-orders/DO_20261029_453C4BC2` | [200] | 200 | PASS |
| 19 | `write.parse_draft` | T1_WAREHOUSE | `POST /orders/parse-draft` | [403] | 403 | PASS |
| 20 | `write.save_lines` | T1_WAREHOUSE | `PUT /orders/drafts/DRF_C08_PROBE/lines` | [403] | 403 | PASS |
| 21 | `write.approve` | T1_WAREHOUSE | `POST /orders/DRF_C08_PROBE/approve` | [403] | 403 | PASS |
| 22 | `write.decide` | T1_WAREHOUSE | `POST /approvals/APR_C08_PROBE/decide` | [403] | 403 | PASS |
| 23 | `write.discard` | T1_WAREHOUSE | `POST /orders/drafts/DRF_C08_PROBE/discard` | [403] | 403 | PASS |
| 24 | `write.clarification_copied` | T1_WAREHOUSE | `POST /orders/drafts/DRF_C08_PROBE/clarification-copied` | [403] | 403 | PASS |
| 25 | `cross.clerk_warehouse_view` | T1_CLERK | `GET /warehouse/delivery-orders/DO_20261029_453C4BC2` | [403] | 403 | PASS |
| 26 | `cross.owner_warehouse_view` | T1_OWNER | `GET /warehouse/delivery-orders/DO_20261029_453C4BC2` | [403] | 403 | PASS |
| 27 | `tenant.t2_on_t1_do` | T2_WAREHOUSE | `GET /warehouse/delivery-orders/DO_20261029_453C4BC2` | [404] | 404 | PASS |
| 28 | `tenant.t2_override_param` | T2_WAREHOUSE | `GET /warehouse/delivery-orders/DO_20261029_453C4BC2?tenant_id=T1` | [404] | 404 | PASS |
| 29 | `tenant.t1_override_param` | T1_WAREHOUSE | `GET /warehouse/delivery-orders/DO_20261029_453C4BC2?tenant_id=T2` | [200] | 200 | PASS |
| 30 | `tenant.t2_header_override` | T2_WAREHOUSE | `GET /warehouse/delivery-orders/DO_20261029_453C4BC2` | [404] | 404 | PASS |
| 31 | `override.me_query` | T1_WAREHOUSE | `GET /me?role=OWNER&user_id=USR_T1_OWNER&tenant_id=T2` | [200] | 200 | PASS |
| 32 | `override.me_headers` | T1_WAREHOUSE | `GET /me` | [200] | 200 | PASS |
| 33 | `method.delete_warehouse_do` | T1_WAREHOUSE | `DELETE /warehouse/delivery-orders/DO_20261029_453C4BC2` | [405] | 405 | PASS |
| 34 | `method.post_warehouse_do` | T1_WAREHOUSE | `POST /warehouse/delivery-orders/DO_20261029_453C4BC2` | [405] | 405 | PASS |
| 35 | `method.patch_delivery_order` | T1_WAREHOUSE | `PATCH /delivery-orders/DO_20261029_453C4BC2` | [405] | 405 | PASS |
| 36 | `method.put_approval` | T1_WAREHOUSE | `PUT /approvals/APR_C08_PROBE` | [405] | 405 | PASS |
| 37 | `method.delete_draft` | T1_WAREHOUSE | `DELETE /orders/drafts/DRF_C08_PROBE` | [405] | 405 | PASS |
| 38 | `method.get_parse` | T1_WAREHOUSE | `GET /orders/parse-draft` | [405] | 405 | PASS |
| 39 | `auth.unauth_warehouse_do` | - | `GET /warehouse/delivery-orders/DO_20261029_453C4BC2` | [401] | 401 | PASS |
| 40 | `auth.unauth_customers` | - | `GET /customers` | [401] | 401 | PASS |
| 41 | `write.ai_wake` | T1_WAREHOUSE | `POST /ai/wake` | [403] | 403 | PASS |

失败用例：无
