# Rule AS - Vision Compliance

## 目的

Rule AS 用来阻止“字段已经挂到画像，但 Router / Prompt 根本不消费”的伪挂载。

## 判定条件

任一通过 `ProfileContextService._attach_*` 挂到画像的字段，必须满足以下三条之一：

1. 被 `routing_engine.py` 或 `prompts.py` 显式消费。
2. 消费路径存在明确 gate / kill switch。
3. 如果暂不消费，必须写 `# rule-as: ignore <reason>`，并登记到例外表。

## Stage 33 现行范围

| 字段 | 状态 | 消费位置 | Gate |
| --- | --- | --- | --- |
| `srl_phase` | 已接通 | `routing_engine.py` + `prompts.py` | `AURORA_STAGE33_SRL_MODE` |
| `metacognition_profile` | 已接通 | `routing_engine.py` (`_build_metacognition_hint`) | `AURORA_STAGE35_METACOG_ROUTER_MODE` |
| `metacognition_dashboard` | 例外 | 现有 dashboard 路径保留，不进入 Router | `rule-as: ignore stage35_dashboard_existing_path` |
| `metacognition_process_scaffolding` | 例外 | 继续沿用 Stage 30 prompt 路径 | `rule-as: ignore existing_prompt_and_stage30_path` |
| `idiographic_summary` | 例外 | Stage 31/现有 prompt 路径 | `rule-as: ignore existing_prompt_and_stage31_path` |

## Guard

- 脚本: `scripts/guards/check_rule_as_vision_compliance.py`
- Manifest: `scripts/rule_guard_manifest.tsv`

## 例外策略

- 只允许单行注释格式: `# rule-as: ignore <reason>`
- 例外必须同时登记到 `docs/aurora/rule_as_exceptions.md`
- 新增字段若无 expectation 也无 ignore，guard 直接失败
