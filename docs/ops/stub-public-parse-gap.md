# 公网 Stub 环境商品行缺失问题记录

- 记录日期：2026-10-24（Asia/Shanghai）
- 状态：Open / 已知限制
- 影响阶段：2026-10-24 演示录制、公网 Stub 环境
- 不涉及：Gate 0 冻结契约、真实 AI 验收、UAT 通过结论
- 负责人：He Minghao（后端/部署）；Ye Lianghui 不需要为此改前端
- 相关代码：`backend/app/extraction/stub.py:8-17`

## 1. 现象

前端已部署到：

```text
https://kiraorder-web.replit.app
```

后端已部署到：

```text
https://kiraorder-api.replit.app
API base: https://kiraorder-api.replit.app/api/v1
```

CORS 预检已通过：

```text
OPTIONS /api/v1/me
Origin: https://kiraorder-web.replit.app
HTTP 200
access-control-allow-origin: https://kiraorder-web.replit.app
```

在公网前端连接 API 后创建订单草稿：

```text
Customer: Restoran Ali (Tier A)
Message:
Boss, Milo 5 pkt
Tepung 3 ctn
Minyak 2 ctn
```

创建成功，但结果页出现：

```text
Order draft created
Needs your decision
Offline match · non-AI
Products & quantities: Awaiting a complete product selection
Order total: —
Clarification: Please confirm this order: Which item do you mean by "item"? Thank you!
```

草稿记录：

```text
Order #4E373C
URL: https://kiraorder-web.replit.app/#/order/DRF_4E373C6EF639464EB9574B5EF9A7B859
```

## 2. 根因

不是前端 bug，不是 CORS，不是部署失败。

当前 `AI_PROVIDER=auto`，且没有配置 `AI_SERVICE_URL`，因此后端使用
`StubExtractor`：

```python
class StubExtractor:
    """Returns no rows; the skeleton creates an unresolved draft."""

    def extract(...):
        return RawExtraction()
```

Stub 固定返回空 `RawExtraction`，所以：

```text
无商品行
无数量/单位/商品族映射
无价格/库存检查
无法形成可审批订单
```

`parse-draft` 随后按设计创建 unresolved draft，并生成泛化 clarification。

## 3. 影响

公网 Stub 环境可以验证：

- 登录 / `/api/v1/me`
- T1 客户列表
- 创建草稿
- unresolved issue
- clarification 文案
- 保存草稿
- 前端空状态与错误提示

公网 Stub 环境不能验证：

- 商品行解析
- SKU / 数量 / 单位 / 商品族匹配
- 价格与库存
- 可审批订单
- 审批 / DO 生成
- 真实 AI 精度

因此：

```text
不能用这条空草稿做“完整下单流程已打通”的声明。
不能点 Approve & generate DO 来假装成功。
```

## 4. 与前端责任边界

Ye / 前端不需要：

- 伪造商品行
- 隐藏空状态
- 把 Stub 结果包装成成功解析

前端当前展示：

```text
AI offline · non-AI
Awaiting a complete product selection
```

是符合 Stub 实际行为的。

## 5. 可选方案

### A. 演示录制使用前端 Local Demo（当前建议）

```text
Return to demo
```

使用前端已有合成数据，展示完整订单、商品、审批流程。

优点：

- 不改代码
- 不需要重新部署
- 10.24 录制可控
- 不依赖 RunPod

限制：

- 明确标注 Local Demo
- 不是公网后端真实解析
- 不作为真实 AI 精度或 UAT 证据

### B. 后端增加 deterministic fallback provider

复用现有：

```text
backend/app/ai/fallback.py
extract_fallback_order()
```

在无真实 AI 时返回确定性商品行。

需要：

- 后端代码改动
- 单元/集成测试
- CI
- Replit `git pull` + Republish
- 公网重新 smoke

风险：

- 演示前改动后端
- 需要明确该模式不是真实 AI
- 需要避免改变 Gate 0 业务契约

### C. 等 RunPod 恢复

当前 RunPod 公开请求不可用，不作为 10.24 前置依赖。

## 6. 当前决定

```text
2026-10-24 录制：采用方案 A，前端 Local Demo。
公网 Stub URL 保留，作为部署、CORS、API 连通和空草稿行为证明。
公网 Stub 不作为完整下单/UAT/真实 AI 验收证据。
方案 B 需要单独确认后再改后端，不在本次录制前临时上线。
```

## 7. 重新验证条件

如果后续实施方案 B：

1. 后端改动合并到 `main`
2. CI 全绿
3. `kiraorder-api` 执行 `git pull`
4. Republish
5. 公网重新创建同一条消息的草稿
6. 确认出现商品行、数量、单位、商品族映射
7. 再检查价格/库存/审批/DO
8. 更新本文档状态

如果切真实 AI：

1. RunPod `/health`、`/v1/models`、chat 可用
2. 跑六样本
3. 跑 T1/T2 parse
4. 设置 `AI_PROVIDER=runpod_adapter`
5. 再 Republish 并重新 smoke

## 8. 证据边界

本文档只记录：

- 公网部署事实
- Stub 空结果事实
- 当前演示决策

不构成：

- 业务字段级验收
- 数据签字扩展
- 真实 AI 精度结论
- UAT 通过
- 最终提交材料完成
