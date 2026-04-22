# Aurora Kill Switch Drill Playbook

架构师:请做最终签字验收。
- SGW dogfood: CONDITIONAL
- Kill Switch 三态化完成率: 12/12
- Phase I Exit Gate 建议: patch

日期: 2026-04-22  
维护阶段: Stage 40  
最近统一演练: 2026-04-23

## 范围

本手册覆盖 Phase I Exit Gate 要求的 12 个核心 kill switch，并补充 Stage 33-35 与 Stage 40 的扩展 drill 入口。

统一入口:

- `bash scripts/stage40/drill_all.sh`
- `bash scripts/stage40/drill_calendar.sh`

统一审计文件:

- `artifacts/stage40/kill_switch_drill_audit.jsonl`
- `artifacts/stage33/drill_audit.jsonl`

## 核心 12 个 Kill Switch

| Stage | 名称 | 三态语义 | Drill 命令 | 期望 Prometheus 观测 | 最近演练 |
| --- | --- | --- | --- | --- | --- |
| 18 | Aggregator / Push Policy / Push Delivery | `off`: 全关；`shadow`: 仅计算/审计；`live`: 真正影响推送链路 | `bash scripts/stage40/drill_all.sh` | `sparkle_kill_switch_mode{stage="18",feature="aggregator|push_policy|push_delivery"}` 依次为 `0→1→2→1→0` | 2026-04-23 |
| 19 | Working Memory / Extractor / Consolidation | `off`: 禁止 WM 管道；`shadow`: 保留 dry-run；`live`: 允许受控写入/整合 | `bash scripts/stage40/drill_all.sh` | `sparkle_kill_switch_mode{stage="19",feature="working_memory|llm_extractor|consolidation"}` | 2026-04-23 |
| 21 | Skill Store / Selection / Share | `off`: 停止存取与分享；`shadow`: 保留观测；`live`: 完整技能路径 | `bash scripts/stage40/drill_all.sh` | `sparkle_kill_switch_mode{stage="21",feature="skill_store|skill_selection|skill_share"}` | 2026-04-23 |
| 23 | Bayesian Router | `off`: 完全停用；`shadow`: 只观测；`live`: 参与 live canary 选择 | `bash scripts/stage40/drill_all.sh` | `sparkle_kill_switch_mode{stage="23",feature="mode"}` | 2026-04-23 |
| 24 | Policy Compiler | `off`: 停用；`shadow`: 旁路编译；`live`: 真正提供 policy IR | `bash scripts/stage40/drill_all.sh` | `sparkle_kill_switch_mode{stage="24",feature="policy_compiler"}` | 2026-04-23 |
| 25 | Reflection Wire | `off`: 不接线反思；`shadow`: 只记录；`live`: 实际接入反思链路 | `bash scripts/stage40/drill_all.sh` | `sparkle_kill_switch_mode{stage="25",feature="reflection_wire"}` | 2026-04-23 |
| 26 | Scene | `off`: 场景管道关闭；`shadow`: 生成但不消费；`live`: 完整场景流水 | `bash scripts/stage40/drill_all.sh` | `sparkle_kill_switch_mode{stage="26",feature="scene"}` | 2026-04-23 |
| 27 | Foresight / Attractor / Deviation / JITAI | `off`: 主从全关；`shadow`: 只保留监测；`live`: 正式参与 foresight 路径 | `bash scripts/stage40/drill_all.sh` | `sparkle_kill_switch_mode{stage="27",feature="mode|attractor|deviation|jitai"}` | 2026-04-23 |
| 28 | Traits / NLP / Coldstart | `off`: 主从全关；`shadow`: 保留估计；`live`: 参与 traits 消费 | `bash scripts/stage40/drill_all.sh` | `sparkle_kill_switch_mode{stage="28",feature="mode|nlp|coldstart"}` | 2026-04-23 |
| 29 | SRL / Tracker / Bridge / Scaffolding | `off`: 主从全关；`shadow`: 观测与降级；`live`: 完整 SRL 桥接 | `bash scripts/stage40/drill_all.sh` | `sparkle_kill_switch_mode{stage="29",feature="mode|tracker|bridge|scaffolding_consume"}` | 2026-04-23 |
| 30 | Metacognition / Dashboard / Process / FSM | `off`: 主从全关；`shadow`: 只产生 shadow delta；`live`: 正式参与元认知链路 | `bash scripts/stage40/drill_all.sh` | `sparkle_kill_switch_mode{stage="30",feature="mode|dashboard|process_scaffolding|fsm_combine"}` | 2026-04-23 |
| 31 | Idiographic | `off`: 停用；`shadow`: 保留影子观测；`live`: 正式启用 idiographic 输出 | `bash scripts/stage40/drill_all.sh` | `sparkle_kill_switch_mode{stage="31",feature="idiographic"}` | 2026-04-23 |

## Stage 40 Calendar

名称: `AURORA_STAGE40_CALENDAR_MODE`  
三态语义:

- `off`: 完全跳过 Calendar -> Prompt 路径，并增加 `sparkle_calendar_fallback_total{reason="mode_off",mode="off"}`
- `shadow`: 并行计算 Calendar 上下文，但 prompt 不渲染 Calendar section
- `live`: Calendar section 正常进入 prompt 渲染

命令序列:

- `bash scripts/stage40/drill_calendar.sh`

期望 Prometheus:

- `sparkle_kill_switch_mode{stage="40",feature="calendar"} = 0→1→2→1→0`
- `sparkle_calendar_fallback_total{reason="mode_off",mode="off"}` 在 `off` 演练时增长

回滚条件:

- prompt 出现非 live calendar section
- `shadow` 仍然把 calendar urgency 渲染到 prompt
- `off` 模式没有 fallback 计数

最近一次演练时间:

- 2026-04-23

## 演练步骤

### Stage 18

名称: Aggregator / Push Policy / Push Delivery  
命令序列: `off -> shadow -> live -> shadow -> off`  
执行命令: `bash scripts/stage40/drill_all.sh`  
回滚条件:

- 任一子开关未随主命令切换
- `push_delivery` 在 `shadow` 仍触发真实发送

### Stage 19

名称: Working Memory / LLM Extractor / Consolidation  
命令序列: `off -> shadow -> live -> shadow -> off`  
执行命令: `bash scripts/stage40/drill_all.sh`  
回滚条件:

- `working_memory_enabled` 为 `off` 时仍写入
- `llm_extractor_enabled` 非 `live` 时仍向 working memory 注入候选

### Stage 21

名称: Skill Store / Selection / Share  
命令序列: `off -> shadow -> live -> shadow -> off`  
执行命令: `bash scripts/stage40/drill_all.sh`  
回滚条件:

- `skill_share` 在 `shadow` 自动发布
- `skill_selection` 在非 `live` 仍进入 prompt

### Stage 23

名称: Bayesian Router  
命令序列: `off -> shadow -> live -> shadow -> off`  
执行命令: `bash scripts/stage40/drill_all.sh`  
回滚条件:

- `live` 之外仍进入 live canary 分支

### Stage 24

名称: Policy Compiler  
命令序列: `off -> shadow -> live -> shadow -> off`  
执行命令: `bash scripts/stage40/drill_all.sh`  
回滚条件:

- `off` 时仍生成 live policy IR

### Stage 25

名称: Reflection Wire  
命令序列: `off -> shadow -> live -> shadow -> off`  
执行命令: `bash scripts/stage40/drill_all.sh`  
回滚条件:

- `off` 模式仍调用反思触发链路

### Stage 26

名称: Scene  
命令序列: `off -> shadow -> live -> shadow -> off`  
执行命令: `bash scripts/stage40/drill_all.sh`  
回滚条件:

- `off` 时仍进入 scene merge / consume 路径

### Stage 27

名称: Foresight 主 + 3 子开关  
命令序列: `off -> shadow -> live -> shadow -> off`  
执行命令: `bash scripts/stage40/drill_all.sh`  
回滚条件:

- 主开关关闭后子开关 gauge 仍非 `off`

### Stage 28

名称: Traits 主 + NLP + Coldstart  
命令序列: `off -> shadow -> live -> shadow -> off`  
执行命令: `bash scripts/stage40/drill_all.sh`  
回滚条件:

- `off` 时 `nlp_mode` 或 `coldstart_mode` 仍可用

### Stage 29

名称: SRL 主 + Tracker + Bridge + Scaffolding  
命令序列: `off -> shadow -> live -> shadow -> off`  
执行命令: `bash scripts/stage40/drill_all.sh`  
回滚条件:

- ordered startup / shutdown 后摘要模式不一致

### Stage 30

名称: Metacognition 主 + Dashboard + Process + FSM  
命令序列: `off -> shadow -> live -> shadow -> off`  
执行命令: `bash scripts/stage40/drill_all.sh`  
回滚条件:

- `off` 时 dashboard/process/fsm 任一残留 live

### Stage 31

名称: Idiographic  
命令序列: `off -> shadow -> live -> shadow -> off`  
执行命令: `bash scripts/stage40/drill_all.sh`  
回滚条件:

- `off` 时 idiographic 仍对下游生效

## 扩展 Drill

Stage 33-35 沿用既有脚本并纳入 `scripts/stage40/drill_all.sh`:

- `bash scripts/stage33/drill_transitions.sh`
- `bash scripts/stage34/drill_transitions.sh`
- `bash scripts/stage35/drill_transitions.sh`
