# AI 独立评测 Intake 清单

日期：2026-10-23  
状态：**等待真实 parse/approve；当前只有结构草案，不能当最终答案键**

## 1. 当前输入

数据岗已说明：

```text
dev_41_draft.json：41 条，按 r2 商品/客户/价格重写
frozen_eval_32_draft.json：32 条，未冻结，无 FROZEN_SHA256
```

当前用途仅限：

```text
[✓] 检查消息覆盖、字段结构、样本类型
[✗] 不作为最终 expected answer key
[✗] 不用于对外宣称准确率
```

## 2. 正式资产要求

真实 parse/approve 跑通后，再向数据岗请求正式文件：

```text
[ ] dev_41.json
[ ] frozen_eval_32.json
```

每个文件必须带：

```text
[ ] 文件名
[ ] 版本 / 日期
[ ] 条数
[ ] SHA-256
[ ] frozen_eval_32 的 FROZEN_SHA256
[ ] 输入字段说明
[ ] expected_status
[ ] expected_issue
[ ] expected_escalation
[ ] 允许使用范围（仅内部合成数据评测）
[ ] 维护人 / 签字人
```

## 3. 冻结协议

```text
1. 数据岗交付正式 JSON
2. 计算 SHA-256
3. 冻结 frozen_eval_32，不再改动
4. 将 FROZEN_SHA256 写入评测记录
5. 评测人不得修改输入或答案键
6. 结果异常时保留原始输出，不回写答案键
```

## 4. 评测范围

按 AI handoff 的 H1/H5 边界：

```text
[ ] 行切分 / span 可定位
[ ] fam / qty / uom / pack_size
[ ] H1 小数、模糊数量、单位
[ ] H5 条件 kind / price_basis / requested_amount
[ ] ai_mode：LLM / FALLBACK / MIXED / ALIAS_ONLY
[ ] ignored_spans
[ ] 不产生 sku_id / price / stock / approval
```

`expected_status / expected_issue / expected_escalation` 必须来自真实
parse/approve 结果，而不是当前 Stub 或草案推断。

## 5. 评测输出

```text
[ ] 6 条合同样例结果
[ ] dev_41 逐条结果
[ ] frozen_eval_32 逐条结果
[ ] 汇总：条数、通过/失败、错分类型
[ ] 原始 stdout / JSON
[ ] 版本、SHA、时间、执行人
```

## 6. 验收边界

```text
[✓] 文件来源和 SHA 可追溯
[✓] frozen 集未改动
[✓] 评测脚本可复现
[✓] 结果包含失败项，不只报通过率
[✗] 不用团队自测替代独立评测
[✗] 不在 RunPod 未恢复时伪造 LLM 结果
```

## 7. 依赖

```text
Xiong：RunPod /health + /v1/models + chat 恢复
Backend：真实 provider + parse/approve 跑通
Zhou：正式 dev_41 / frozen_eval_32 + expected 字段
Test：独立执行和签字
```

## 8. 当前结论

```text
能做的：准备本清单、确认草案边界
不能做的：正式评测、准确率声明、冻结集结论
```

正式评测开始前，不把任何 draft 结果写入 README、提交材料或对外演示。
