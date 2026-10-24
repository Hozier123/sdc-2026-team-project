# T1 E2E blocker evidence

- 文件：`t1_e2e_23_2026-10-24.json`
- 原始 SHA-256：`97FEE66743809D748E4C571749777D69D0CF2B01F6AAA8770C16289AB8F390D8`
- 模式：`REAL`，23 条 T1 E2E parse-draft
- 状态：`BLOCKER_EVIDENCE`
- 不用于：current E2E、READY、通过、准确率

## 为什么是 blocker

`DEV-01`（`3 ctn Ayam A1, 10kg Bawang Bsr India`）在旧 resolver 下：

```text
uom=bag
sku_id=SKU_BAWANG_10KG
qty=10
tier_unit_price=32.00
subtotal=320.00
status=READY_FOR_APPROVAL
```

这是错误的可批准结果：bulk Bawang 应为 `SKU_BAWANG_KG`，10 × RM3.50 = RM35.00。

根因：`row.uom=None` 时 resolver 仍用 `pack_size=10kg` 过滤，误选 bag SKU。PR #55（`c93d6d0`）已阻断该行为：UOM 缺失且同族多 `base_unit` 时返回 `MISSING_UOM` + candidates，不自动选 SKU。

## 其他已知问题

- `DEV-04/05/11/33/37` 仍 `uom=None`
- `DEV-05/33` 因此 `MISSING_UOM`，未进入库存不足判断
- `uom=None / MISSING_UOM` 仍是已知缺口

## 使用规则

```text
[✓] 只能作为 blocker / historical evidence
[✓] 保留原始 CRLF 字节和 SHA
[✗] 不写 CURRENT_E2E
[✗] 不写 READY
[✗] 不写通过
```

重跑必须使用修复后的代码和新的 evidence 文件；旧文件不得覆盖。
