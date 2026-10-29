# Zhou C01 附件独立复核结论

- 复核人：Zhou Jingxi（数据与质量）
- 日期：2026-10-29
- 复核对象：He 提供的 C01 附件
- 复核单号：DO_20261029_453C4BC2
- 结论：**C01 业务面在附件范围内通过；材料完整性与 OWNER/WAREHOUSE 网页身份/权限证据待补。按 He 的口径，整体暂不记通过。**

> 2026-10-29 追加：OWNER / WAREHOUSE 角色证据见 `04_Zhou_C01角色证据补判_2026-10-29.md`（通过）；C01 漏发补充材料见 `05_Zhou_C01补充材料复核_2026-10-29.md`（第 1—2 项已补，第 3 项 C07 仅屏幕证据）。本文的“整体暂不记通过”只代表第一批材料到手时的状态。

## 一、复核材料与方法

本次实际收到的材料：

| 文件 | 说明 |
|---|---|
| `selected-network-evidence(1).json` | 12 条请求/响应摘录，不是完整 HAR |
| `C01(1)/c01_01_baseline.png` | v2 页面，规格已选，同日订单阻断仍在 |
| `C01(1)/c01_02_approved.png` | 批准后的 DO 页面 |
| `C01(1)/c01_03_do.png` | DO 打印预览 |
| `C01(1)/c01_04_stock_after.png` | 批准后新草稿读取库存 |
| `C01(1)/c01_05_log.png` | 审批轨迹 4 条 |
| `Records.original(1).txt` | Records 原始记录 |
| `REVIEW(1).md` | 被审材料；只核对其引用，不采信其结论 |

方法：以 `selected-network-evidence(1).json` 中的原始请求/响应逐条复算，并用 5 张截图交叉核对。另对同一 DO 做了只读 GET 抽查，数据与附件一致；线上抽查不作为网页角色证据，也不改变“整体暂不记通过”的口径。

未重跑订单、未修改库存、未批准、未向他人发消息。

## 二、结论摘要

| 核对项 | 结论 |
|---|---|
| 商品、数量、规格、单位 | 通过 |
| 等级单价与小计 | 通过 |
| 总额 RM70.80 | 通过 |
| 面粉库存 31→27 | 通过 |
| 食用油库存 23→21 | 通过 |
| 批准审计 1 条 | 通过 |
| 扣库存审计 1 条 | 通过 |
| FALLBACK + 人工确认路径 | 通过 |
| 材料完整性 | 待补 |
| OWNER/WAREHOUSE 网页身份与权限 | 待补，暂不记通过 |

## 三、逐项核对

### 1. 单号、草稿与版本

- DO：`DO_20261029_453C4BC2`
- 草稿：`DRF_39D4D66CACC440A594B1C1AEBEF151B9`，v3
- `approval_mode`：`DIRECT`
- `approved_by`：`USR_T1_CLERK`
- `approved_at`：`2026-10-29T07:16:58.981249Z`（UTC+8 15:16:58）

### 2. 商品、数量、规格、单位、单价、小计

| 商品 | 数量/单位 | 规格 | 等级单价 | 小计 |
|---|---|---|---|---|
| SKU_TEPUNG_1KG 面粉 | 4 bag | 1kg | RM3.20 | RM12.80 |
| SKU_MINYAK_5KG 食用油 | 2 btl | 5kg | RM29.00 | RM58.00 |

总额 **RM70.80**，与网页、批准响应、DO 三处一致。

### 3. 模式与人工确认

- parse #22（15:09:53）：`ai_mode=FALLBACK`；面粉 line `sku_id=null`；`MULTIPLE_PACK_SIZES` 与 `SAME_DAY_ORDER` 两条均 `blocking`。
- PUT #35（15:10:04）：人工选定 `SKU_TEPUNG_1KG` / 1kg，保存 v2。
- PUT #59（15:16:53）：`SAME_DAY_ORDER` 已解决，`resolution=SEPARATE_ADD_ON`，`resolution_note="Separate add-on order"`，保存 v3，状态 `READY_FOR_APPROVAL`。
- `field_diffs` 共 9 条，全部 `source=PUT_LINES` / `reason=USER_EDIT`。

结论：符合“FALLBACK + 人工确认”，不是 LLM 一次解析无歧义。

### 4. 库存

- parse #22：面粉候选 `available_qty=31`，食用油 `available_qty=23`。
- 批准后新草稿 #86/#99（15:20:21—15:20:43）：面粉 `27`，食用油 `21`。
- 中间无其他扣减。

结论：面粉 31→27（扣 4 bag），食用油 23→21（扣 2 btl），成立。

### 5. 审计

- 事件计数：`SAVE_LINES` ×2、`APPROVE` ×1、`INVENTORY_DEDUCT` ×1。
- `APPROVE` 与 `INVENTORY_DEDUCT` 的 payload 均带 `do_number=DO_20261029_453C4BC2`。
- 两条事件时间同为 `2026-10-29T07:16:58.927554Z`。
- 截图 `c01_05_log.png` 与接口事件完全一致。
- 15:22:10 的重试 #109 为 `status=0 / net::ERR_FAILED`；15:23:47 的审计 #116 仍只有一次扣库存，支持未二次记账。

### 6. 请求 ID

- parse：`ca57c454-bf64-4868-941a-a3797858b392`
- approve：`1ff33119-afa7-4d04-bf33-33f9f880e9a1`
- 与 `Records.original.txt` 对上。

### 7. 网页来源

- HAR 中 `Origin` / `access-control-allow-origin` 为 `https://hozier123.github.io`。
- API 为 `https://kiraorder-api.replit.app`。
- `/me` 返回 `CLERK / Siti / T1`。

## 四、差异与待补

1. **完整材料未随附**：`REVIEW(1).md` 自述依据是 118 条请求的 HAR 与 8 张截图，但本次附件只有 12 条摘录和 5 张截图；`source-manifest.json`、`Xiong-message.txt` 也未随附。摘录本身自洽，但无法核验它与完整 HAR 的对应关系。
2. **C07 409 证据缺失**：REVIEW 提到的 409 截图不在本次附件；HAR #109 为 `status=0 / net::ERR_FAILED`，无响应体、无响应头、无 `request_id`。C07 暂不判定。
3. **Records 措辞需修正**：
   - “单位是ctn❌”不成立：本次输入和选择均为 bag/btl，没有 ctn 缺陷；
   - “没有黄色阻断提示✔”只对 v3 之后成立：`c01_01_baseline.png` 是 v2，仍有 `SAME_DAY_ORDER` 黄色卡。
   以上是记录措辞问题，不影响 C01 业务数据。
4. **审计视图不展示疑点解除记录**：`audit-detail` 不返回 `SAME_DAY_ORDER` 的 `SEPARATE_ADD_ON` 记录；该记录只存在于 PUT #59 的响应和 draft 记录中。若要求网页审计体现“人工确认同日加单”，需补接口/页面展示。
5. **角色证据待补**：本批 `/me` 只见到 CLERK；OWNER / WAREHOUSE 的网页身份与权限证据未提供。按 He 的口径待补，收到后补判。

## 五、边界

- 本结论只覆盖 C01 降级业务验收。
- LLM 真实推理与 Gate E 不在本结论内。
- 未重跑订单、未改库存、未批准；只做只读复核。
