# Predictive SQAM

## ID1

- `get_prediction_analytics()` 必须持续暴露 CTR 字段，避免产品/监控消费面结构漂移。

## ST1

- 多条预测路径共享 `0.95` 置信度上限，避免 LLM 或规则层高估。

## DP1

- `_build_realtime_llm_messages()` 在导出 `partial_text` 前调用 `_redact_pii()`。

## SM1

- `dropout_risk.risk_level` 在 JITAI handoff 前被消费；高风险时抑制 mood-only hint。
