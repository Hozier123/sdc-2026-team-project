# PR #3 AI 审核要点指引

> 审核对象：`docs/rules/03_KiraOrder_v1.3_后端与AI对接规则.md`  
> 适用 PR：<https://github.com/Hozier123/sdc-2026-team-project/pull/3>  
> 基线：`gate0-baseline-v1` / Gate 0 v4 / draft revision 5  
> 基线哈希：`6A44089C623C1B4AE8F444660DBD89422C663E7EBDD141EA6FDA549DDD833770`  
> Canonical：`gate0/`；本文只是审核指引，不是契约。

---

## 0. 审核前

先打开 PR #3，点：

```text
Update branch
```

审核目标：

> **这份 AI 文档会不会让 AI/Adapter 写出与 Gate 0 不一致的实现？**

会 → 阻断。  
不会 → 确认或提非阻断建议。

---

## 1. AI 边界

AI 不应该决定：

```text
价格是否成立
库存是否足够
是否升级给 OWNER
目标行是谁
是否批准
最终 DO
```

AI 只输出：

```text
span
qty / uom / family / pack_size
条件候选
ignored_spans
```

- [ ] 文档是否明确 AI 不决定价格/库存/审批/目标行
- [ ] 是否禁止 AI 返回 `sku_id / unit_price / available_qty / target_line_ids / approval_required / do_number`
- [ ] 是否明确 Adapter 由后端维护，AI 不直接写正式字段

### 阻断例子

```text
文档让 AI 返回可用库存
文档让 AI 决定是否升级
文档让 AI 直接写 target_line_ids
```

---

## 2. PII 与输入

- [ ] 是否固定三个 token：
  - `[REDACTED_PHONE]`
  - `[REDACTED_MYKAD]`
  - `[REDACTED_EMAIL]`
- [ ] 是否禁止 `[PHONE]`、`[EMAIL]` 第二套
- [ ] 是否明确原始 `message_text` 不进入 prompt/日志/fixture
- [ ] 是否明确 `masked_text` 最多 4000 Unicode code points
- [ ] 是否明确偏移是 Unicode code point
- [ ] 是否明确超长直接 422 `MESSAGE_TOO_LONG`，不调用 AI

### 阻断例子

```text
文档允许第二套 PII token
文档允许原始电话进入 prompt
文档按 UTF-16 计算 span
```

---

## 3. H1 v2 字段证据

- [ ] 是否使用 `field-evidence-v2.json`
- [ ] 是否覆盖 qty/uom/family/pack_size
- [ ] 是否要求 span 唯一定位
- [ ] 是否要求 start/end 映射回原 masked text
- [ ] 是否明确 0/负数/小数/非法格式 → `INVALID_QUANTITY`
- [ ] 是否明确多个不同 qty 候选 → `AMBIGUOUS_QUANTITY`
- [ ] 是否明确金额/编码不能当 qty
- [ ] 是否明确 `RM2.50 satu` 的 `satu` 是单价限定词
- [ ] 是否明确 `RM95 untuk 1 ctn` 的 1 不是订单 qty
- [ ] 是否明确 `pack_size` 不是 qty
- [ ] 是否明确逗号小数只在后接单位时阻断
- [ ] 是否明确 `10kg bawang` 仍是 qty=10
- [ ] 是否禁止把词表复制成 prompt 硬编码

### 阻断例子

```text
文档允许两个 qty 候选取最早值
文档允许 500g/2kg/12 x 1L 当 qty
文档允许 satu 当 qty=1
文档允许 RM95 for 5 ctn 自动除以 5
文档按旧 decimal 守卫误伤 12, 3 pack
```

---

## 4. H1 实现注记必须看

PR #3 的 03 文档已标出 Gate 0 v4 的文字/oracle 不一致：

```text
gate0/contracts/field-evidence.md 第 39 行旧 pipeline
```

审核时不要要求实现按旧文字写。实际以：

```text
gate0/tests/contract/contract_oracles.py
gate0/contracts/lexicons/field-evidence-v2.json
```

为准：

```text
1. 单价限定词掩码
2. 金额掩码
3. 编码掩码
4. pack_size 条件掩码
5. 小数守卫
6. 候选 + 多候选判定
```

- [ ] 文档是否保留这条实现注记
- [ ] 是否明确不改 `gate0/`
- [ ] 是否明确需要 canonical 文字一致时开 `gate0-v5`

### 说明

这是 Gate 0 v4 的文档勘误，不是 PR #3 修改契约。  
如果审核人认为“文档必须和 Gate 0 完全一致”，可以提非阻断意见，但不能要求本 PR 修改 `gate0/`。

---

## 5. H5 v3 条件

- [ ] 是否使用 `condition-triggers-v3.json`
- [ ] 是否 16 行真值表
- [ ] 是否明确裸 `RM95` 不触发
- [ ] 是否明确 `kalau RM95 boleh` 触发 PRICE
- [ ] 是否明确 `RM95?` 触发 PRICE
- [ ] 是否明确 `kalau ada, boleh kurang` → STOCK + PRICE
- [ ] 是否明确 STOCK 条件 `blocking=false`
- [ ] 是否明确 PRICE 默认 `blocking=true`
- [ ] 是否明确 `price_basis` 只允许 `UNIT/TOTAL/UNKNOWN`
- [ ] 是否明确 `RM95 for 5 ctn` 不能自动除法
- [ ] 是否明确 `RM95 untuk 1 ctn` 才是 UNIT
- [ ] 是否明确 `condition_scope=UNKNOWN` + 空 target → `TARGET_LINE_REQUIRED`
- [ ] 是否明确 `NOT_A_CONDITION` 必须带 note
- [ ] 是否明确 `negative_contexts` / `context_markers` 从词表读取
- [ ] 是否明确显式询价覆盖历史否定

### 阻断例子

```text
文档允许 STOCK 条件阻断
文档允许 RM95 for 5 ctn 自动算单价
文档把 price_basis 扩展成 UNKNOWN_OR_TOTAL
文档在 prompt 里再写一套否定词
文档把 H5 契约用例写成 TEST-xx
```

---

## 6. Adapter 与降级

- [ ] 是否明确 Adapter 校验 JSON shape
- [ ] 是否丢弃额外字段
- [ ] 是否比较模型值和确定性候选
- [ ] 是否计算 evidence start/end
- [ ] 是否合并客户别名
- [ ] 是否禁止“取第一个/取最像/让模型再选一次”
- [ ] 是否单行失败隔离
- [ ] 是否 qty/family 失败必须阻断或单行 fallback
- [ ] 是否禁止静默形成确定 SKU+数量
- [ ] 是否明确 RapidFuzz 只排序不决策
- [ ] 是否明确超时走 fallback 或 503，不静默成功

### 阻断例子

```text
文档允许 Adapter 猜一个候选
文档允许失败行静默通过
文档把超时当无字段
```

---

## 7. 测试与验收

- [ ] H1 是否有 35 个 required_cases
- [ ] H5 是否有 16 行 truth_table
- [ ] Gate 0 契约测试是否 42 passed
- [ ] 是否覆盖 H1-PACK-1—4、H1-AMB-1、H1-UPM、H1-UNIT-PRICE、H1-DEC-COMMA-NEG、H1-UOM-PLURAL
- [ ] 是否覆盖 H5 16 行
- [ ] 是否禁止硬编码词表
- [ ] 是否有 PII/超时/降级测试

---

## 8. 审核结论

### 无阻断

```text
03 AI 对接已核对：
- PII 三 token / 4000 上限 / code point 偏移
- H1 v2：AMBIGUOUS_QUANTITY、pack_size、金额/编码/单价限定词
- H5 v3：16 行、STOCK 不阻断、PRICE/UNIT/TOTAL/UNKNOWN
- Adapter 降级与禁止硬编码
无阻断异议。
```

或 `Review changes → Approve`。

### 有阻断

```text
Request changes

阻断项：
文件/行：
Gate 0 依据：
期望：
实际：
影响：
```

### 非阻断

```text
非阻断建议：
```

例如补充一个边角例子，但不要因此阻塞合并。

---

## 9. AI 通过标准

```text
[ ] AI 不决定价格/库存/审批/目标行
[ ] PII 三 token / 4000 / code point 正确
[ ] H1 v2 覆盖 qty/uom/family/pack_size
[ ] AMBIGUOUS_QUANTITY 正确
[ ] pack_size 不是 qty
[ ] 金额/编码/单价限定词不误判
[ ] H5 v3 16 行 / STOCK 不阻断 / price_basis 正确
[ ] Adapter 降级无静默错配
[ ] 无阻断评论
```
