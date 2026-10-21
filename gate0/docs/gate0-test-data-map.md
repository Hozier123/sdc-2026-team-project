# Gate 0 测试数据与编号表（gate0-v4）

> 本表是 **数据岗独占** 的冻结集/DEV 编号真相；Gate 0 H5 契约用例使用 `H5-CT-*`，不得占用 `TEST-*`。
> 本文件不改变 Gate 0 的运行时契约，只固定数据交付路径与编号。

## 1. 文件路径

| 文件 | 内容 | 状态 |
|---|---|---|
| `tests/dev_41.json` | `DEV-01`—`DEV-41` 全部开发场景 | **canonical** |
| `tests/dev_32.json` | 旧 32 条开发场景 | deprecated，仅历史兼容，不再新增 |
| `tests/frozen_eval_32.json` | `TEST-01`—`TEST-32` 冻结集 | canonical（10/22 10:00 封存） |
| `tests/FROZEN_SHA256.txt` | 冻结集哈希 | 封存时生成 |
| `tests/answers/dev_answers.json` | DEV 答案键 | 仅离线 `run_eval.py` 读取 |
| `tests/answers/frozen_answers.json` | TEST 答案键 | 仅离线 `run_eval.py` 读取 |

- **应用/API/AI 运行时不得读取 `tests/answers/*`**；答案键不得进镜像、prompt 或公开 URL。
- `dev_41.json` 与 `frozen_eval_32.json` 不重叠；DEV-33—41 是回归/新规则，不进入冻结集。\n- 冻结集尚未在 repo 分发；数据岗封存后只交 `FROZEN_SHA256.txt` 和答案键审批记录，不把冻结消息/答案提交进应用仓库。
- 冻结集封存后只读；需要修改时新建版本并重算 `FROZEN_SHA256.txt`，不能静默覆盖。

## 2. DEV 编号（1—41）

| 范围 | 主题 |
|---|---|
| DEV-01—12 | 方案 B 基础场景 |
| DEV-13—24 | 改价升级、阈值、账期、权限、库存、注入、别名、PII |
| DEV-25—32 | STOCK 条件、PRICE 条件、OTHER、跨客户、三语、同日（P1） |
| DEV-33—38 | v2.1 正确性回归（库存状态、价格目标行、跨短语） |
| DEV-39—41 | H1 字段证据（qty 不同、fam 不在 span、span 重叠） |

## 3. TEST 编号（1—32，冻结集）

| 范围 | 主题 |
|---|---|
| TEST-01—24 | 方案 B Group A—F |
| TEST-25—28 | 改价升级 + 老板批准、跨租户阈值、权限、库存变化 |
| TEST-29 | 有货条件，有货与缺货各一种 |
| TEST-30 | 价格条件，马来语/中文/英文各一种（含 `can less?`/`老价钱`） |
| TEST-31 | 同一条消息，不同客户，路由随账期提醒变化 |
| TEST-32 | 没有条件标记的送货要求/闲聊，不生成条件 |

> Gate 0 H5 契约用例是 `H5-CT-01`（裸金额/历史不触发）、`H5-CT-02`（STOCK+PRICE 多标签）、`H5-CT-03`（PRICE 缺目标/UNIT 阻断）；它们**不是** TEST-29/30/32。

## 4. 数量裁定

| 项 | 裁定 |
|---|---|
| T1 条件消息 16 条 vs 至少 12 | 16 可保留；多出的 4 条标 `split=dev`，不进 `frozen_eval_32.json` |
| T2 16 SKU vs “约15” | 保留 16；“约15”是近似值，覆盖 10 族/5 客户即可 |
| DEV 总数 41 | 用 `dev_41.json`；`dev_32.json` 不再作为 canonical |
| 冻结集 32 | `frozen_eval_32.json` 只放 TEST-01—32，不放 DEV |
