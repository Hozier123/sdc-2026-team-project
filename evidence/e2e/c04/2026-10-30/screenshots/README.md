# C04 截图（4 张）

执行：2026-10-30 16:55–17:00（UTC+8）
环境：Chrome 无痕；前端 v1.4.0 / f8ff1d7；生产 API。

| 文件 | 证明 |
|---|---|
| [c04_01_clerk_draft_top.jpg](c04_01_clerk_draft_top.jpg) | 地址栏 `#/order/DRF_AFC94FC488144FC6932FA4800D73B0EC`；`Awaiting owner`；Kedai Rasa Tier B；原文 `Milo 1kg 2 bag, kalau RM17 boleh?`；`Blocking checks clear` + `A price was requested`；身份 Siti / Order clerk |
| [c04_02_clerk_draft_totals.jpg](c04_02_clerk_draft_totals.jpg) | 同一 URL；商品表 Milo 1kg，2 bag，库存 30 bag，**Tier unit price RM 19.00**，Subtotal **RM 34.00**；Order total **RM 34.00** |
| [c04_03_owner_approval_top.jpg](c04_03_owner_approval_top.jpg) | 地址栏 `#/approval/APR_7A1382B29D5C44FFB6242D15477A60B7`；Boss Tan / Owner；**Awaiting decision**；Submitted by USR_T1_CLERK 16:57 MYT；库存 2 requested / 30 available |
| [c04_04_owner_approval_changes.jpg](c04_04_owner_approval_changes.jpg) | 同一 URL；Unit price **RM 17.00**（划线 RM 19.00）；2 bag；Subtotal **RM 34.00**；Changes 表 Effective 19.00→17.00、Subtotal 38.00→34.00；`Approve & generate DO`（未点击） |

## 说明

- **UI-01**：`c04_02` 与 `c04_03` 的 “Tier price RM 0.00” 卡片是前端字段名 bug（`ui.tsx:273`），不是数据错；真实数字见 `c04_02` 商品表、`c04_04` Changes 表与 `sample.json`。
- **ENV-01**：`c04_01` 顶部的 “AI offline” 是前端不自动轮询的过期显示；服务端 16:42/16:54 均 READY，`c04_03` 显示 “AI ready”。
- 4 张图均无 token、无手机号、无 Authorization；地址栏只含 draft/approval ID。
- 原图未裁剪、未压缩；逐张 SHA-256 见上级 `SHA256.txt`。
