# T1 E2E post-PR55 evidence

- 文件：`t1_e2e_23_2026-10-24_post55.json`
- 原始 SHA-256：`DCA16B6E5DBC54AB712C1FD1133DFA13CF5083A397B56CCA99CBE41363DAC4C0`
- 模式：`REAL`，23 条 T1 E2E parse-draft
- Code base：`c93d6d0`
- 状态：`E2E_POST55`
- 不进入 AI-only 索引

## 结果

- 23/23 HTTP 200
- 23/23 `ai_mode=LLM`
- fallback 0
- 7 READY / 16 DISAMBIGUATION_REQUIRED

## DEV-01

已修复为：

```text
DISAMBIGUATION_REQUIRED
MISSING_UOM
candidates=SKU_BAWANG_10KG / SKU_BAWANG_KG
```

不再错误 READY，不再产生 RM320 的 bag subtotal。

## 仍存在的已知缺口

UOM None 9 处：

```text
DEV-01/04/05/07/11/13/27/33/37
```

其中 DEV-07/13/27 被 `MISSING_UOM` 阻断，属于已知的
`KNOWN_UOM_INJECTION_GAP`；本轮不修 seed、不升 Gate0。

## 使用规则

```text
[✓] 可作为 post55 E2E 证据归档
[✗] 不写 AI-only index
[✗] 不写 23/23 E2E 通过
[✗] 不覆盖旧 97FEE blocker 文件
```

旧 `97FEE667…` 继续只作 `BLOCKER_EVIDENCE`。
