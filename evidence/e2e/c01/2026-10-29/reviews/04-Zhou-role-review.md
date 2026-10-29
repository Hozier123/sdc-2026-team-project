# Zhou C01 角色证据补判

- 复核人：Zhou Jingxi（数据与质量）
- 日期：2026-10-29
- 补判对象：He 提供的 OWNER / WAREHOUSE 网页补证
- 复核单号：DO_20261029_453C4BC2
- 结论：**OWNER / WAREHOUSE 角色证据通过；C01 业务面结论不变（通过）；C07 与第一批材料完整性仍待补。**

## 一、收到的补证材料

归档目录：`01_工作区/对齐材料/2026-10-29_He_C01角色补证/`
哈希清单：同目录 `SHA256.txt`

| 角色 | 文件 | 说明 |
|---|---|---|
| OWNER | `owner.txt` | 时间、入口、请求 ID、核对项 |
| OWNER | `owner_session.har` | 11 条请求/响应 |
| OWNER | 6 张 PNG | `/me`、DO 页、审计页、审计响应 |
| WAREHOUSE | `warehouse.txt` | 时间、入口、请求 ID、字段裁剪 |
| WAREHOUSE | `warehouse_session.har` | 8 条请求/响应 |
| WAREHOUSE | 4 张 PNG | `/me`、拣货页、响应 JSON、请求头 |

## 二、OWNER 核对

| 项 | 结果 | 证据 |
|---|---|---|
| `/me` 身份 | 200；`USR_T1_OWNER` / `OWNER` / Boss Tan / T1 | HAR #1，`x-request-id=6419881e-c291-4f77-90b8-b58c60b3ec29`，与 `owner.txt` 一致 |
| DO 查询 | 200；`DO_20261029_453C4BC2`；总额 RM70.80；4 bag + 2 btl | HAR #9，`x-request-id=88886a5f-3815-4d58-ad25-544426d44464` |
| 审计查询 | 200；`SAVE_LINES`×2、`APPROVE`×1、`INVENTORY_DEDUCT`×1；`ai_mode=FALLBACK` | HAR #10，`x-request-id=1e280d20-c220-4c52-a802-3f0e5cb8dcc0`，与 `owner.txt` 一致 |
| 页面身份 | 右上角 `Boss Tan / Owner` | `owner_01_me - 1.png`、`owner_02_do.png` |
| 审计页面 | 4 条轨迹，与接口一致 | `owner_03_audit_page.png`、`owner_04_audit_response - 1/2.png` |
| 写操作 | 无订单写操作；仅有 `POST /ai/wake`（非订单写） | HAR 全部条目 |

## 三、WAREHOUSE 核对

| 项 | 结果 | 证据 |
|---|---|---|
| `/me` 身份 | 200；`USR_T1_WAREHOUSE` / `WAREHOUSE` / Ah Kow / T1；`permissions=[]` | HAR #2，`x-request-id=4a86f95c-93c2-4a31-8f16-6176d2f221b2`，与 `warehouse.txt` 一致 |
| 拣货查询 | 200；`DO_20261029_453C4BC2`；面粉 4 bag、食用油 2 btl | HAR #6，`x-request-id=721e59d9-df2a-4c54-a60d-9a56db2ab7d2`，与 `warehouse.txt` 一致 |
| 响应字段 | 仅 `do_number`、`customer_name`、`items[]`、`approved_at` | HAR #6 响应体；无 price/subtotal/total/phone/message/contact/amount/RM |
| 页面提示 | `Read-only picking list` / `Prices and contacts excluded.` | `warehouse_01_me - 1.png`、`warehouse_02_picking_page.png` |
| 只读证明 | 页面无编辑/批准入口；`permissions=[]`；HAR 无写请求 | `warehouse_01_me - 2.png`、`warehouse_02_picking_page.png` |

说明：拣货响应仍含 `customer_name=Restoran Ali`，不含客户电话、联系人字段或原消息。按 He 本轮“没有客户电话”的口径，这一项通过；如果验收标准要求连客户名也不显示，需要另行确认。

## 四、记录修正与历史模式

- `owner.txt` / `warehouse.txt` 已不再出现“单位是 ctn”或“没有黄色阻断提示”的错误表述。
- 三个关键请求 ID 均与 HAR 对上。
- `ai_mode=FALLBACK` 与 C01 审计响应一致；本轮没有新的 LLM 成功证据，LLM 仍不在本结论内。

## 五、仍未闭合的项

1. **完整 HAR / `source-manifest.json`**：第一批附件仍是 12 条摘录，无法绑定 REVIEW 声称的 118 条完整会话。
2. **其余 3 张 C01 截图**：REVIEW 声称 8 张，本次第一批只收到 5 张；本轮新增的是角色截图，不等于补上那 3 张。
3. **C07 409 证据**：HAR #109 仍为 `status=0 / net::ERR_FAILED`；没有 409 响应 JSON、业务错误码或 `X-Request-ID`。
4. **审计页展示疑点解除记录**：`audit-detail` 仍不返回 `SAME_DAY_ORDER=SEPARATE_ADD_ON`；只在 PUT #59 响应和 draft 记录里。
5. **YOUR OWNER/WAREHOUSE 写接口 403 实测未提供**：按“页面无入口 + permissions=[] + HAR 无写请求”的只读证明口径通过；如需最严格证据，可补一次 403 实测。

## 六、结论

- 角色证据（原清单第 4—9 项）：**通过**。
- C01 业务面：**通过**（与第一批复核一致）。
- C01 整体：业务面与角色证据均已通过；第 1—3 项材料完整性仍待补，C07 单独待补。
- 本结论只读；未重跑订单、未改库存、未批准。
