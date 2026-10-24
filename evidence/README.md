# 实测证据归档

已归档 Gate 0 独立确认材料；后端基础验收记录见 [backend-foundation/README.md](backend-foundation/README.md)。这些记录不代表业务效果评测，不预填任何 KPI 或效果数字。

按实际产生的材料归档，例如：
- 基线定义、锁定记录与手工计时原始数据；
- 工具计时、首次使用测试的原始记录；
- 离线评测结果与冻结集哈希；
- 测试环境、样本、测量方法和限制；
- 经筛选的演示或测试截图。

保留原始记录并区分目标、假设和实测结果。所有业务样本使用团队自建合成数据。不要放真实客户记录、个人敏感信息或平台密钥。

正式提案、工具声明及平台使用证明放在根目录 submission/，本目录用于支撑性实验记录。

Gate 0 的四方确认材料保存在 `gate0/` 子目录；冻结的规格与机器契约本体保存在仓库根目录 `gate0/`。证据目录可以继续追加材料，但不得借此修改已经冻结的基线。

## AI official UOM 已知缺口

db6f0ce official 23 条 AI-only 共 31 行，UOM 为 30/31。剩余 1 行为
`KNOWN_UOM_INJECTION_GAP`：`4 botol minyak 5kg` 的 `botol` 未识别为 UOM。
T1 seed 已有 `ALS_UOM_007`（botol→btl），但 adapter 只读 H1 词表 /
`tenant_uom_extensions`，不读 DB `uom_aliases`。

这不是数据缺口，不能写成“UOM 全通过”；本期不改 seed、不升 Gate0。
未来由代码侧注入 tenant UOM aliases 后再重跑 23 条。
