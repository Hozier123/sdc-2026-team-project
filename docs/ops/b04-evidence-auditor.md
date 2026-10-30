# B04 离线证据包核验器

`backend/tools/audit_b04_evidence.py` 仅用 Python 标准库，只读 ZIP 或目录；不导入应用、不调用 HTTP/DB/GPU、不解压或修改输入。检查清单/字节哈希、case 与请求绑定、版本、角色/租户、实际模式，以及原始库存/DO/审计数据的一致性。

从 `backend/`、已激活 Python 环境执行：

```powershell
python -m tools.audit_b04_evidence '<returned-evidence.zip>' --reference '<original-handoff.zip>' --reference-sha256 '<64-hex SHA256 from original delivery record>' --require-t2-four
```

参考 hash 取自先前已保存的交付记录，不能自动相信待审包自己声明的 hash。`--reference` 不携带参考时仍可检查内部一致性，但会保留 REVIEW。默认生成新的 JSON 和 Markdown 报告到忽略的 `evidence/b04-audits/`；`--out '<new-report.json>'` 可另设新路径，工具拒绝覆盖已有文件或写入被审目录。

| 选项 | 用途 |
| --- | --- |
| --reference / --reference-sha256 | 外部固定的原交付快照及整包哈希 |
| --require-t2-four | 必须收到四种真实 T2 路线，mock/显式负例不能充数 |
| --negative-run | 显式标记预期 FAIL 的 run_id 或 case_id，可重复传 |
| --expected-driver-sha256 | 默认已签收驱动哈希；新版本需另行明确 |

原始 ZIP 没有清单但先前收到的独立 SHA 表仍可用时，应在新本地目录并置原字节材料和原表，单独记录组合来源；不要重写原 ZIP 或生成新清单来冒充原始校验依据。

## 核验覆盖

- JSON manifest、SHA256 Markdown/sha256sum 清单的大小和哈希，缺文件及未列入清单的核心证据。
- case canonical hash、已签收驱动、summary/checkpoint/case/run_id、角色租户、实际 AI 模式、请求缓存与 raw response 的绑定。
- 请求序号、request_id/header、原始响应哈希、HTTP 状态、目标 URL、parse 输入与保存/批准版本。
- SKU、数量、单位、价格、行序、金额、DO 引用、老板快照/决定、仓库字段裁剪与日志次数。
- 逐 SKU 库存差量、DO/approval 终态、审计次数及同库 batch 库存衔接；不因 checks=true 就接受结论。
- 顺序 409/跨租户 404 记录；缺少成对 retry/保护侧原始快照时保留 REVIEW。

若 `input/` 保留旧交付 manifest，仅在其字节等同外部固定整包 hash 的参考 manifest 时，按参考包核验旧清单。它不能替代回传文件或覆盖本次证据清单。

ZIP 拒绝路径穿越、绝对/驱动器路径、重名/大小写碰撞、symlink、加密成员和超限数据；默认最多 5000 成员、单文件 16 MiB、总解压尺寸 128 MiB。

| 退出码 / status | 含义 |
| --- | --- |
| 0 / PASS | 自动覆盖部分无错误或必需证据缺失，仍须读 REVIEW |
| 1 / FAIL | 哈希、绑定、业务值矛盾，或输入损坏/不安全 |
| 2 / INCOMPLETE | 缺必需材料/步骤/路线，或只有报告而无原始证据 |

PASS 不代表证据生成者身份、真实连接过哪台服务器或正式评分；缺失原始数据不能推断为已验证。mock 只计模拟，预期 FAIL 不代表无副作用，顺序防重不证明并发。正式 TEST32/v5 预期、冻结及评分另行处理。

## 离线验证

```powershell
python -m pytest -q tests/test_run_workflow.py tests/test_audit_b04_evidence.py
```

公开交付分支共 83 项离线测试通过：驱动 35 项、核验器 48 项。核验器测试覆盖删文件、哈希篡改、重签清单后的库存/DO/审计篡改、错误请求绑定、固定参考与伪参考、目录安全和报告不覆盖。

`tests/fixtures/b04-audit-direct.zip` 是公开 canonical T2 合成 DEV 运行的测试快照，不含会话或冻结 TEST32 答案，不是新的运行/独立验收证明。所有原始独立回包、完整私密报告、正式答案及本机接收记录均留在本地。
