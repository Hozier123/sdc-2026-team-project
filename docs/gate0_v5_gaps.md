# Gate 0 v5 Known Gaps & Reconciliation Notes

## 1. N10 Comma Decimal Guard (`1,5kg` / `0,5 ctn`)
- **Discovery Date**: 2026-10-22
- **Contract Baseline**: Gate 0 v4 (`contract_oracles.py:20`)
- **Observed Behavior**:
  Gate 0 v4 reference oracle extracts `qty=1` from `1,5kg` because `_ARABIC` parses the leading integer `1` before pack_size and decimal guards execute.
- **Production Implementation Fix**:
  `backend/ai/fallback.py` adds strict no-space comma guard (`(?<![\d.,])\d+,\d+(?![\d.,])`) and moves comma unit guard BEFORE pack_size masking.
  Result: `1,5kg` and `0,5 ctn` correctly block with `qty=None` and `issue_reason="INVALID_QUANTITY"`.
- **Side-effect note**:
  The strict comma decimal guard will also block un-spaced numbers without units like `12,3` as decimal. Per B2B wholesale order safety, this is an intentional fail-safe bias towards disambiguation.

## 2. N10 Malaysian/Indonesian Comma Currency Amount (`RM2,50`)
- **Discovery Date**: 2026-10-22
- **Contract Baseline**: Gate 0 v4 (`field-evidence-v2.json:qty_exclude_pattern`)
- **Observed Behavior**:
  `qty_exclude_pattern` only matches dot decimals (`\brm\s*\d+(?:\.\d{1,2})?`). A price written as `Milo RM2,50` causes `,50` to leak as `qty=50`. Furthermore, `Milo RM2,50 satu, 10 ctn` fails to mask `satu`, causing `AMBIGUOUS_QUANTITY` between 1 and 10.
- **Production Implementation Fix**:
  1. Added `_AMOUNT_WITH_COMMA_DECIMAL = re.compile(r"(?i)\brm\s*\d+,\d{1,2}(?!\d)")` to length-preserving mask pipeline.
  2. Relaxed `unit_price_marker_pattern` at runtime from `\.\d{1,2}` to `[.,]\d{1,2}` to ensure `RM2,50 satu` is fully masked.
  Result: `Milo RM2,50` yields `qty=None`, and `Milo RM2,50 satu, 10 ctn` cleanly yields `qty=10`.

## 3. H5 金额/分配/单价正则未下沉词表 & condition_scope 判定规则缺失

- **Discovery Date**: 2026-10-22
- **Contract Baseline**: Gate 0 v4 (`contract_oracles.py:240-248`, `condition-triggers-v3.json`)
- **Observed Behavior**:
  1. `_AMOUNT_VALUE` / `_ALLOCATION` / `_UNIT_PRICE` 三个正则与
     `("kalau", "if ", "?", "？")` token 列表**只存在于 oracle 代码**，
     `condition-triggers-v3.json` 中没有对应条目。仅读词表的实现会漏判
     真值表第 4 / 10 / 12 行（实测：漏 `_ALLOCATION` 时 `RM95 for 5 ctn`
     由 `['PRICE']` 退化为 `[]`）。
  2. 真值表 16 行未覆盖逗号小数金额（如 `RM95,50`）。生产实现若放宽为
     PRICE，属未经契约确认的扩展。
  3. `ConditionScope` 的 `MULTI_LINE` / `ORDER_LEVEL` 判定规则在契约中
     未定义，P0 实现只能按行数简化为 `SINGLE_LINE` / `UNKNOWN`。
- **Production Implementation Fix**:
  `backend/ai/adapter.py` 复制上述三个正则（注释标注来源行号）并附
  16 行真值表 parity 单测；逗号金额扩展默认关闭待契约确认；
  `condition_scope` 简化逻辑在代码与交付说明中显式标注为 P0 简化。
- **Target Release**: `gate0-v5` 应将三个正则下沉到
  `condition-triggers-v3.json`，补充逗号金额真值表行，并定义
  `MULTI_LINE` / `ORDER_LEVEL` 判据。

## 4. 当数量因小数被阻断（INVALID_QUANTITY）时强制 pack_size=None
- **Discovery Date**: 2026-10-23
- **Contract Baseline**: Gate 0 v4 (`contract_oracles.py:extract_row_field_evidence`)
- **Observed Behavior**:
  Gate 0 oracle 对 'Beras 1.5kg' 仍输出 `pack_size='1.5kg'`。
- **Production Implementation Note**:
  4. 当数量因小数被阻断（INVALID_QUANTITY）时强制 pack_size=None：与 Gate 0 oracle 对 'Beras 1.5kg' 仍输出 pack_size='1.5kg' 存在已知偏离（生产侧偏向安全侧保守，避免将非法小数数量当作规格入库），gate0-v5 需确认是否应保留规格。

