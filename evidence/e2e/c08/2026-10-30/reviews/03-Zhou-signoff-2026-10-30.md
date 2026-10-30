# C08 独立复核 v2（复签）

- 复核人：Zhou Jingxi
- 时间：2026-10-30 16:40（UTC+8）
- 对象：`C08_API_evidence_2026-10-30` v2（response SHA 口径修正后）
- 结论：**通过，可改 SIGNED_OFF 并开 Draft PR。**

## 一、修正项复核

- v1 问题：`matrix.response_sha256` 是压缩 canonical JSON 哈希，`responses/*.json` 是 pretty-print，字节不一致。
- v2 修正：`responses/*.json` 改为 HTTP 原始响应字节，不 pretty-print、不加换行。
- 复核结果：**41/41 条** response 文件的 SHA-256 与 `matrix.response_sha256` 一致，字节数与 `response_bytes` 一致。
- 三个指定样例：
  - `read.warehouse_do`：`ae6635391d33d4dcb8b9b2fd0390729e08d8605a818f6c6e1de599491a9c47c7` / 347 B
  - `read.clerk_do_full`：`ea3662ed8e8094dc048a9c843c30c7b84d20386b0e3622af5abcd000bd0574c0` / 1147 B
  - `write.approve`：`87dea7807c2e6e135586ff0cade5ef5a1ce22fc8b3a4168b562089ce69ec6dfe` / 93 B

## 二、清单与包完整性

| 项 | 结果 |
|---|---|
| `evidence/SHA256.txt` | 5,603 B，SHA-256 `F626BDCB4FCAC91747319221201E49203256955B486AFB7FD2E9CAFB83250F03` |
| evidence 文件 | **57/57** 逐文件哈希一致（56 + `reviews/02-Zhou-review-2026-10-30.md`） |
| `PACK_SHA256.txt` | SHA256.txt `F626…`、脚本 `A9A33…`、HANDOFF `18E07…`、hash_tree `D3190…` 全部一致 |
| ZIP 外层 | 1,910,949 B / `6E0E2B1AE44D7ECB5272C14427E83E13CBACB9A3CEE3C8A97C18AB9B974215DD` 为 He 提供；本轮目录无 ZIP 本体，整包哈希未就地复算 |
| 旧包 `C17B…` | 已被 v2 取代，保留旧档，不删除 |
| 安全扫描 | 无 token、Bearer、数据库连接串或真实 PII |

## 三、API 与浏览器结论（延续 v1）

- API 41/41，0 失败；write 7 条全 403；tenant/override/method 符合预期。
- 投影：CLERK 14 顶层 → WAREHOUSE 4；`final_total_rm=70.80` 不在仓库响应。
- field-scan 0 命中；无批量列举路由。
- 浏览器两张与 v1 相同：f8ff1d7 构建、Ah Kow/Warehouse、同 DO、无价格/电话/原消息；403 图含完整 URL + `FORBIDDEN_ACTION`。
- `acceptance.json` 仍为 `overall_status=NOT_SIGNED_OFF`，未提前改状态。

## 四、签署意见

- response SHA 口径修正：**通过**。
- C08 API 层：**通过**。
- C08 浏览器层：**通过**。
- 证据包：**可签 SIGNED_OFF**。
- 后续：He 修改 `acceptance.json` 的 `independent_review_status` / `overall_status`，按 HANDOFF 第 3 节开 Draft PR；PR 正文不要写“全通过”，写“API PASS + 浏览器已补 + Zhou 复签”。

复核人：Zhou Jingxi
时间：2026-10-30 16:40（UTC+8）
