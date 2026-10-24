# Canonical six samples — source of truth

Canonical 六条样例唯一来源：

```text
docs/ai_contract/samples/{normal,ambiguous,condition,empty,multi_candidate,multi_line}.json
```

本目录只保存 **blob SHA-256 清单**，不复制第二份 JSON，避免出现两套版本。

口径：

```text
family_scored=false
GENERIC_CONTRACT_SAMPLE
只评 span / qty / uom / pack_size / conditions
```

复现时使用 `SHA256.txt` 中的 blob 哈希校验源文件；如需运行六样例，
直接使用 `docs/ai_contract/samples/`，不要从本目录另取一份。

最终 6 条 evidence 为 `evidence/he_6cases_final_2026-10-24.txt`，
其头部引用同一组 source path 和 SHA。
