# V4-I10｜limitations

## 本卡未覆盖（如实记录，不冒充完成）

1. **M6 第二账本未收敛**：`llm_security_wrapper._record_usage`（B06 地图 M6）的安全包装估算账与 TokenTracker 主账仍是两本账，无 root_request 关联。收敛需 67 个消费文件的调用树贯通，超出本卡最小增量；本卡根请求行的 `sub_calls` 机制为后续收敛提供了切片容器。分类/充分性/HyDE/审查/反思/embedding/语音的 hidden 消费面（B06 §3）仍走 M6 估算账，未逐调用并入根请求行。
2. **rescue token 为估算而非实测**：非流式 `chat()` 只返回文本，上游 usage 不外暴露（usage 帧仅流式回传）。rescue 子调用 token 以 tiktoken 估算并以 `usage_source=estimated` 显式标注，不冒充实测。若上游未来在非流式路径回 usage，可替换为实测而不改折算结构。
3. **主生成失败轮的 provider 侧消耗不可测**：流式 400/超时失败轮，上游是否计 token 无回执无凭据（B06-T3 同源限制），计量面按 0 处理。
4. **llm_fallback_manager 内部重试的逐 attempt 用量不可切片**：`execute_with_fallback` 的失败 attempt 无 usage 回传，只有成功 attempt 的 usage 入账；重试消耗在 provider 侧不可见。
5. **reserve/settle 的差额回补未实现**：既有 `_reserve_usage_atomic` reserve 估算、`record_usage` settle 实际，两者简单相加路径存在高估面（app 内当前 `check_only=True` 调用使 reserve 路径休眠，实际无害）。差额回补（多退少补）留待预算卡收敛，本卡不动 M5 面（`model="gpt-4"` 硬编码标签属 M5，未改）。
6. **S06 的 7 条原始样本未在真链重放**：零真模型红线 + 无 live 栈授权，检出机制以可失败单测锁定（产生路径按 B06 §4.5 代码锚复现），非真链端到端重放。
7. **回执 cost 的与网关/移动端联动未验证**：`usage_cost_unpriced` metadata 标记的下游消费（网关透传 OK——map 字段透传，移动端是否展示）未做 UI 验证；本卡交付的是引擎侧语义与标记，UI 消费属后续卡。
8. **`get_total_stats` 仍只统计 gpt-4/gpt-3.5-turbo 两个硬编码键**（token_tracker.py 既有面）：模型分布统计的键集扩展与本卡核价权威无耦合，未顺手改（避免超范围）。

## 既有失败/漂移（非本卡引入）

- mypy 4 文件 scope 既有 31 条、standard_workflow scope 既有 30 条错误（stash 前后集合一致，零新增）。
- tests/orchestration 7 warnings、相邻面 39 warnings 均为既有（pytest-asyncio/RunnableConfig 等）。
- phase5 北极星 1 skipped 为既有条件跳过。

## 依赖的 B06 事实

- 三缺陷代码锚与产生机制：`v4/evidence/V4-B06/metering_point_map.md` §1/§4（M1/M2/M3/M8）、`diff_or_evidence_only.md` A3/A4。
- T1/T2/T3 探针样本：同目录 §5（本卡靶 1/靶 4 的实证输入）。
