# D02 UOM 语义表：后端阻断验收记录

- 日期：2026-10-31
- 输入：Zhou Jingxi《D02 UOM 缺口语义表》（2026-10-31 00:25）、`evidence/README.md` 的 UOM 24/31 记录、T1 种子目录（`data/seed/T1_seed.sql`）
- 范围：Resolver、parse-draft、save-lines、approve 四条后端路径；不改种子、不改 Gate 0、不改 AI 侧 prompt。
- 实现：He（backend）

## 2026-10-31 收口补充

- 状态：**DONE_WITH_KNOWN_LIMITATIONS**。下文保留原执行方记录；本补充由 Kilo 核对引用与仓库状态，不代 Zhou 新签收。
- [PR #91](https://github.com/Hozier123/sdc-2026-team-project/pull/91) 已于 2026-10-31 12:04:52（UTC+8）合并，merge `a0628d37bc9d90c2a12e808da9632b3359343dc1`；后端 `postgres` 与前端 `test-and-build` CI 均成功。不再等待重复合并。
- guard 结论限于已核的混合 base-unit / 歧义缺口；单一 base-unit 家族仍保留既有解析路径。不能概括为所有输入都绝不推断单位，也不能把后端阻断当作模型识别修复。
- 原文的“真实 T1 种子 7/7”等为执行方记录；Zhou 原复核未独立复现该项，不因本补充或 CI 自动升级为独立复验通过。原测试输出与缺口数不改。
- UOM 仍 **24/31**，七个模型质量缺口保留。[#92](https://github.com/Hozier123/sdc-2026-team-project/issues/92) 和 [#93](https://github.com/Hozier123/sdc-2026-team-project/issues/93) 仍 OPEN；本轮不改 adapter、不重跑模型、不关闭 Issue。条件 span 问题与单位识别分开跟踪。
- 后续[限定部署验证](../ops/pr91-deployment-verification-2026-10-31.md)另绑定应用 `520556cd64a7e6e6a17dfe84d0cdd386d0fef94e` / Replit `5cae3434`；已有单合成草稿 FALLBACK guard 记录不替代模型准确率、完整 TEST32 或受试计时。新引用仍待 Zhou 确认。
- 公开部署 JSON 的 LF/CRLF 哈希口径及引用限制见 [D06 公开索引](d06-public-citation-index-2026-10-31.md)。未修改 seed/Gate 0 或任何原始证据。

## 一、结论

1. **parse 路径 7/7 阻断**。逐条跑真实 T1 种子：`status=DISAMBIGUATION_REQUIRED`、`lines[0].sku_id=NULL`、`lines[0].uom=NULL`、两/两个候选 SKU、`blocking_issues=["MISSING_UOM"]`、`blocked_actions={"APPROVE_AND_GENERATE_DO": ["MISSING_UOM"]}`。
2. **save/approve 路径也拦得住**。只选 SKU、不写 `uom` 时，混合 base unit 家族仍保留 `MISSING_UOM`，保存后仍是 `DISAMBIGUATION_REQUIRED`；`approve` 返回 400 `DISAMBIGUATION_UNRESOLVED`。显式写入 `uom` 后才能进入 `READY_FOR_APPROVAL` 并生成 DO。
3. **相邻反例全部按语义工作**：显式 bag、显式 kg、缺单位、小数数量、T1 botol/pail、T2 无 pail，见第三节。
4. **不是 P0，但仍是质量缺口**。7 条是模型侧/UOM 识别缺口；后端只负责“缺单位必须阻断”，不能写成“单位全部通过”。UOM 统计仍是 24/31，7 个已知缺口。

## 二、代码修改点

### 1. `backend/app/resolver.py`：显式 kg 不再被 10kg 规格误伤

`pack_size="10kg"` 与散装 SKU 的 `pack_size="散装"` 不相等，旧逻辑会先把散装 KG 过滤掉，导致“显式 kg”反而 `NO_CANDIDATE`。

修复：先按规格精确匹配；没有精确匹配且 `uom` 已显式给出时，保留 bulk 规格（`散装`/`bulk`/`loose`/`timbang`）作为兜底。这样：

- `Bawang 10kg` + `uom=kg` → `SKU_BAWANG_KG`（散装）；
- `1 bag Bawang 10kg` + `uom=bag` → `SKU_BAWANG_10KG`；
- `uom=None` 仍走 `MISSING_UOM`，不会因为原文有 10kg 就选袋装。

### 2. `backend/app/parse.py`：MISSING_UOM 只出一次，且只在它真的是阻断原因时出

旧逻辑有两处问题：

- `product is None and row.uom is None` 无条件加一条 `MISSING_UOM`，随后候选分支又按 `resolution.issue_code` 再加一条，同一行出现两条 `MISSING_UOM`。
- 单一 base unit 家族只剩包装规格歧义时（如 Milo 1kg/2kg 都是 `ctn`），也会被误标 `MISSING_UOM`，澄清文案出现 `ctn / ctn` 这种无意义选项。

修复：以 `Resolution.issue_code` 为唯一来源，一次生成 `MISSING_UOM` / `MULTIPLE_PACK_SIZES` / `MULTIPLE_GRADES`；只有 resolver 明确返回缺单位时才标 `MISSING_UOM`。`LOW_CONFIDENCE_MATCH/NO_CANDIDATE` 仍是兜底。

### 3. `backend/app/drafts.py`：save-lines 不再替混合单位家族自动补 uom

旧逻辑 `_canonical_uom(None, base_unit)` 会直接把所选 SKU 的 `base_unit` 写进 `line.uom`。如果 clerk 只选 `SKU_BAWANG_KG`、不写单位，保存后 `MISSING_UOM` 会被静默清掉并变成 `READY_FOR_APPROVAL`。

修复：保存时若家族存在多个 base unit 且请求没有显式 `uom`，保留 `uom=None`，让原有 `MISSING_UOM` 分支继续 blocking；单一 base unit 家族仍保留既有“按家族解析”的默认行为。

同时 `blocked_actions` 从笼统的 `["BLOCKING_ISSUES"]` 改为实际阻断码（如 `["MISSING_UOM"]`），并始终保留 `APPROVE_AND_GENERATE_DO` 键。

### 4. `backend/app/extraction/evidence.py` / `parse.py`：租户 UOM alias 规范化

新增 `evidenced_uom()`：AI 返回 `btl` 或表面词 `botol`、`pail` 时，只要该别名确实出现在脱敏 span 中，就按当前租户的 `uom_aliases` 归一；别名只从当前租户查询，T1/T2 不共用全局表。它不会从 SKU、包装规格或上下文中“猜”单位；`uom=None` 仍然返回 `None`。

### 5. `backend/app/approvals.py`：未改代码，补验收

approve 原有三道闸门已经足够，本次用回归固定下来：

- 状态必须是 `READY_FOR_APPROVAL`（否则 400 `DISAMBIGUATION_UNRESOLVED`）；
- 任何 `blocking=true && resolved=false` 的 issue 都拒绝；
- 每行必须有 `sku_id` 和 `uom`，且 `uom` 必须与所选 SKU 的 base unit 一致。

`confirmed_items` 兼容路径会先走 save-lines 再校验，因此同样无法绕过。

## 三、相邻反例回归

| # | 场景 | 预期 | 实测（真实 T1 种子） |
|---|---|---|---|
| 1 | 显式 bag：`1 bag Bawang 10kg` | `SKU_BAWANG_10KG`，uom bag，pack 10kg | `READY_FOR_APPROVAL`，bag / 10kg |
| 2 | 显式 kg：`Bawang Bsr India 10kg` + `uom=kg` | `SKU_BAWANG_KG`（散装），不选 10kg 袋 | `READY_FOR_APPROVAL`，kg / 散装 |
| 3 | 单位缺失：`Bawang Bsr India 10kg` | `MISSING_UOM` + 两个候选 + 阻断 | 7/7 之一，`sku=NULL`，候选 KG/10KG |
| 4 | 小数数量：`Bawang 2.5kg` | `LOW_CONFIDENCE_MATCH/INVALID_QUANTITY`，不拆 25、不取整 | 无行，blocking，`blocked_actions` 有 `APPROVE_AND_GENERATE_DO` |
| 5 | T1 `botol`/`pail`；T2 无 pail | T1 归一 btl/pail；T2 不得复用 T1 pail | T1 botol→btl、pail→pail；T2 pail 不归一，保持阻断/无候选 |
| 6 | 10kg 洋葱保护：`Bawang Bsr India 10kg` 作为散装 kg | 仍走 `SKU_BAWANG_KG`；只有显式袋装才选 10kg 袋 | 与 #2 相同；`uom=None` 时仍阻断 |

## 四、回归测试

新增/扩展：

- `backend/tests/test_resolver_missing_uom.py`
  - 7 条 D02 缺口参数化：`product is None`、`MISSING_UOM`、候选集合；
  - 显式 kg + span 内 10kg → 散装 KG；
  - 显式 bag → 10kg bag；
  - 矛盾的 bag 5kg → 无候选；
  - 小数数量 → `INVALID_QUANTITY`。
- `backend/tests/test_d02_uom_blocking.py`（无数据库）
  - 7 条 parse 级阻断：单条 `MISSING_UOM`、`blocking=True`、`ask=CLERK`、候选、`blocked_actions`、澄清含两种单位；
  - 显式 bag / 显式 kg / 小数数量 / 单一 base unit 包装歧义不误标 `MISSING_UOM`；
  - T1/T2 UOM alias 不跨租户。
- `backend/tests/test_uom_save_approve.py`（集成）
  - parse 缺单位 → 选 `SKU_BAWANG_KG` 但不传 `uom` → save 仍 `DISAMBIGUATION_REQUIRED` + `MISSING_UOM`；
  - 此时 approve → 400 `DISAMBIGUATION_UNRESOLVED`；
  - 再 save 显式 `uom=kg` → `READY_FOR_APPROVAL` → approve 200，total 35.00；
  - `confirmed_items` 兼容路径同样无法绕过；
  - T1 pail/botol 成功，T2 pail 不成功。

执行环境：Python 3.13.5、PostgreSQL 17.10（本地临时实例）、`pytest 9.1.1`。

```text
pytest -q -m 'not integration'                 → 457 passed, 131 deselected
pytest -q tests/test_d02_uom_blocking.py \
         tests/test_resolver_missing_uom.py    → 26 passed
pytest -q tests/test_uom_save_approve.py       → 3 passed
ruff check app tests                           → All checks passed
ruff format --check app tests                  → 85 files already formatted
```

全量 588 条（457 非集成 + 131 集成）已按文件分组跑完并全部通过；单进程一次性跑全量时，本地嵌入式 PostgreSQL 在反复 `CREATE/DROP DATABASE` 的 teardown 阶段出现过一次等待（未产生断言失败），因此最终验收按文件分组执行。分组结果：

```text
test_b01_integration.py                         7 passed
test_checks_enabled.py                          4 passed
test_drafts_approve_do.py                      29 passed
test_parse_draft.py                            10 passed
test_resolver_memory.py                         6 passed
test_uom_save_approve.py                        3 passed
test_ai_catalog / approval_concurrency /
  c07 / canonical_seed / me / parse_runpod /
  seed                                          32 passed
test_backend_audit.py                          82 passed
contract_regression / export / reset_demo /
  migrations / cli                             67 passed
test_live_contract_audit.py                      2 passed
```

真实 T1 种子逐条校验的 7/7 输出：

```text
DEV-01 BLOCK uom=None sku=None candidates=[SKU_BAWANG_10KG, SKU_BAWANG_KG]
DEV-05 BLOCK uom=None sku=None candidates=[SKU_BAWANG_10KG, SKU_BAWANG_KG]
DEV-11 BLOCK uom=None sku=None candidates=[SKU_BAWANG_10KG, SKU_BAWANG_KG]
DEV-33 BLOCK uom=None sku=None candidates=[SKU_BAWANG_10KG, SKU_BAWANG_KG]
DEV-07 BLOCK uom=None sku=None candidates=[SKU_MINYAK_17KG, SKU_MINYAK_5KG]
DEV-13 BLOCK uom=None sku=None candidates=[SKU_MINYAK_17KG, SKU_MINYAK_5KG]
DEV-27 BLOCK uom=None sku=None candidates=[SKU_MINYAK_17KG, SKU_MINYAK_5KG]
blocked 7/7
```

## 五、仍存在的缺口（不由本 PR 关闭）

- AI 适配器仍未注入租户 `uom_aliases` 的 botol/pail 词表（Xiong 侧）；本 PR 只保证“AI 若返回 botol/pail，后端能按租户归一”，以及“AI 返回 None 时一定阻断”。
- 7 条 D02 缺口仍是模型侧质量缺口；UOM 仍是 24/31，不能写成“单位全部通过”。
- 本 PR 不改种子、不改 Gate 0、不声称 P0；需要重跑 23 案例并替换官方证据后，才能更新 UOM 统计。
