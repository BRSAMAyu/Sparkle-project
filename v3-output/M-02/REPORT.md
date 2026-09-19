# M-02 Personalized Storage Gate（该不该记）— 执行报告

worktree: `Sparkle-sysrev/wt8 @ 43942d23`（基线）→ 本卡改动见 `changes.patch`
gate: Memory V3 M-02 ｜ risk: medium ｜ reviewers_required: 1 ｜ locks: memory-write-policy ｜ 禁 commit/push（已遵守）
执行：前任 Worker（额度中断，留下 gate 模块/接入/单测/评测集未提交稿）+ 本任接续（甄别续作、修 4 类缺陷、跑基准与回归、落盘交付物）

## 0. 六句总结

单一权威 gate 模块 `backend/app/services/memory_storage_gate.py`：bypass→规则（B1-B3/R1-R10 纯 stdlib 首匹配）→可选语义层（chat_json + 3s→5s 超时 + 断路器 + 限频，任何失败降级规则默认且不得自授权 confirm），落点在 `create_episodic_memory` 落库之前，不改 LLM 主链。五分类 {store,current_state,event,ignore,confirm}：ignore/current_state 一票跳过 L1 落库（内容仍留 Redis 工作记忆层，consolidation 通道 veto 后自然滞留）；confirm 挂起为 HYPOTHESIS（confidence 封顶 0.55 + pending tag + 不推"记住了"），由既有四动作治理 API 收口，未新造确认机制；event 打 bounded_scope（decay 压 7d/due_at+7d），瞬时 today constraint 绝不默认 global。接续修复前任 4 类缺陷：评测集 3 处规则漏判（ev06 日期+轻动词/cs02 状态变体/ig04 拼接应答）与 1 个子串过匹配真 bug（词表 "emo" 命中英文 "memory" 内容导致存量 vector-runtime 测试被误杀——改为边界正则，测试未弱化而恢复通过）。验收：64 场景评测集五类 precision/recall 全 1.0 落盘 EVAL_RESULTS.md + 回归阈值守卫固化；韧性红绿齐备（gate 内部异常/入口异常/语义层超时/坏输出/断路器 → 降级 ignore+log 或规则默认，mock 异常断言写路径与聊天主链不炸）。受影响域回归 181 过，2 失败经 git stash 对照证实为基线预存，1 处环境性缺 gen 产物；真实 LLM 冒烟 9/10 次预算内完成（qwen3.8-flash 端到端 3/5 精化命中且类别合理，同时实证 3.0s 超时必截断 thinking 档 → 默认改 5.0s）。

## 1. 问题与目标

任务卡：减少瞬时噪声与错误长期化。①规则+fast semantic gate 输出五分类 {store,current_state,event,ignore,confirm}+决策原因；②敏感/高影响 hypothesis 需 confirmation（衔接既有 memory 治理 API 四动作，不新造确认机制）；③transient sessions/重复信息/一次性时间约束 case。验收：①50+ 写入场景 precision/recall 评测落盘；瞬时 today constraint 不默认 global；②gate 失败不阻断聊天主链（mock 异常断言主链不炸）。

### 接续甄别（前任未提交稿的处置）

前任已完成且质量良好（保留续作）：gate 模块主体架构（bypass/rule/semantic 三层 + 断路器 + 限频 + dedup LRU）、`memory_service` 接入点（含 pgvector 降级重建路径的幂等注解重放）、kill-switch 三态绑定（对齐 stage19 既有模式）、Prometheus 指标、30 项单测与 64 场景评测集。前任未完成：评测未跑通（3 场景漏判致 precision 0.833）、无 EVAL_RESULTS/REPORT/patch。前任稿内含 4 类缺陷（见 §3）。

## 2. 设计（核心决策）

### 2.1 单一权威与落点

- **落点**：`MemoryService.create_episodic_memory` 内 `_build_episodic_memory_record` 之后、`db.add` 之前——所有 L1 episodic 写方（orchestrator 主链、inferred lane、working-memory consolidation 升级通道、focus/reflection/error_book 等）都汇于此，一处治理全部；`force_write` 只旁路抽取侧检查，仍过 gate（consolidation 即治理对象）。
- **顺序**：`_allow_write`（用户关闭开关）仍先行——用户主权 > gate 策略。
- **不改 LLM 主链**：gate 是写路径旁路组件；veto 返回 None，orchestrator 侧调用本就 try 包裹、不消费返回值；consolidation 得 None 即不标记 consolidated，条目留在 Redis 层（可在窗口内重试或过期）。

### 2.2 五分类语义（决策原因可审计）

| verdict | 处置 | 触发（rule 层） |
|---|---|---|
| store | 照写 | B1 user_confirmed lane / B2 用户陈述种子(user_registered/user_state) / B3 结构化系统写方(task_outcome/struggle/reflection 等) / R2 显式记忆口令(短语或 stage16/19 explicit_command schema) / R9 稳定性标记(总是/习惯/我喜欢…) / R10 兜底 |
| event | 写但封界 | R5：commitment subject / due_at / (一次性时间锚点 × 事件名词或轻动词)；decay 压 7d（无 due_at）或 due_at+7d，tag `m02:event_bounded` |
| current_state | 跳过 L1（留工作记忆） | R6：瞬时状态词表（情绪/精力/位置）或 时间标记×感受token；稳定性标记优先排除 |
| ignore | 不写 | R1 空 / R3 负面身份标签（错误长期化守卫，防 consolidation force_write 绕过抽取侧封禁）/ R7 噪声（精确表+短串+拼接应答整耗尽+包含词）/ R8 30min TTL-LRU 快速重述去重 |
| confirm | 挂起 HYPOTHESIS | R4：敏感词表（health/mental_state/financial/identity/family_privacy）× 推断 lane；confidence 封顶 0.55 + `m02:pending_confirmation` + `m02:sensitive:{cat}` tag + 不推系统通知；收口于既有 confirm/wrong/outdated/delete 四动作治理 API |

关键裁决：**R2 显式口令压过 R4**（用户自己要求记住的敏感陈述是其主权，B2 同理——显式 lane 的敏感信息照写，治理 UI 可删）；**R4 压过 R5**（"下周去医院复诊"按敏感挂起而非事件）；**R5 压过 R6**（"我现在好累，明天还要考试"混合句取一次性约束）。语义层不得自授权 confirm（敏感确认必须来自可审计规则命中，LLM 说 confirm 降级 store 并记 `semantic_verdict`）。

### 2.3 韧性契约（验收 #2）

- `evaluate` 入口全量兜底：内部异常 → `ignore` + layer `error_degraded` + log + 指标。fail-closed-on-write 是刻意的：gate 故障期不向长期记忆灌未审内容，且瞬态内容仍在 Redis 工作记忆层，无不可逆丢失。
- `memory_service` 接入点再包一层 try（入口异常同降级），随后逻辑保证 veto 短路先于任何 apply 调用。
- 语义层：独立 settings 开关（默认关）+ 3 次连续失败断路 300s + 30 次/分钟限频 + asyncio.wait_for 超时；一切失败 → 规则默认（内容域 fail-open：R10 残留本就由置信度机制兜底）。
- kill-switch `AURORA_STAGE19_STORAGE_GATE_MODE`：off=全旁路恢复既有行为 / shadow=只观测（shadow_verdict 注解）不拦截 / live=执行。

### 2.4 可观测性

`sparkle_memory_storage_gate_total{verdict,layer}`（layer ∈ bypass/rule/shadow/semantic/semantic_fallback/error_degraded）+ `MEMORY_WRITE_TOTAL{type=episodic,status=gate_filtered}`；每次 veto 带 user_id/verdict/reason/detail 日志。

## 3. 接续修复的缺陷（前任稿问题清单）

1. **评测 3 场景漏判**（规则层 → store 误判，precision 0.833）：ev06「6月15日要考四级」（EVENT_NOUNS 无裸"考"）→ 新增 `_ONESHOT_EVENT_VERB_RE` 轻动词路径（仅与一次性时间锚点共现时采信；`(?<!思)…(?!虑|察)` 排除 思考/考虑/考察，`(?<!不)(?<!不要)` 排除否定/犹豫形态）；cs02「我今天状态不太好」→ 感受 token 增"状态"（与时间标记组合，稳定性标记仍优先）；ig04「嗯嗯知道了」→ 噪声判定支持拼接应答整串消耗（前缀剥离至尽）。
2. **子串过匹配真 bug（波及存量测试）**：词表裸 "emo" 命中英文 "memory summary" 内部 → 两个 pgvector 降级存量测试被误杀（R6 误 veto）。改为边界正则 `_TRANSIENT_TOKEN_RE`（`(?<![a-zA-Z])emo(?![a-zA-Z])`），同修裸单字 困(≠困难)/渴(≠渴望)。**测试未弱化**——vector-runtime 语义照旧，仅不再被误杀。
3. **语义层默认模型不可解析**：默认 "claude-haiku-4-5" 在本部署 router 未注册（无 Anthropic 凭据）→ 改 "qwen3.8-flash"（flash 档、DASHSCOPE_FAST_MODEL 同款、已注册）。
4. **语义层超时默认必截断**：实测 qwen3.8-flash（thinking 档）JSON 分类 2-3.4s，3.0s 默认 0% 完成 → 5.0s（实测可用），并写明依据。

另：EVENT_NOUNS 删除裸 "课"（"选课方向" 误判事件），保留 有课/上课/实验课。

## 4. 验收证据

### ① 50+ 场景评测落盘（64 场景）

- 数据：`backend/tests/fixtures/memory_storage_gate_eval_v1.json`（五类 15/12/11/14/12，人工标注含对抗样例与重述对）。
- 结果（规则层独跑、语义关、kill-switch live，可复现）：**五类 precision/recall 全 1.0000，accuracy 1.0000**；逐场景结果与规则命中分布见 `EVAL_RESULTS.md`。
- 回归守卫固化：`tests/unit/test_memory_storage_gate_eval.py` 断言 ≥50 场景、五类全覆盖、每类 P/R ≥1.0、ev01/ev09 专项 event——词表演进任何误判即红。
- **瞬时 today constraint 不默认 global**：ev01（明早8点考试）/ev09（今天下午3点实验课，无 due_at）判 event + bounded_scope；写路径断言 decay 压至 7d（`test_write_path_event_bounded_scope`）。
- fixture 之外对抗负例集（13 例：思考/考虑不判事件、否定犹豫形态不判事件、噪声前缀不吞内容、稳定性标记压过状态 token、英文子串不误伤）固化为单测。

### ② gate 失败不阻断聊天主链

红绿测试（`tests/unit/test_memory_storage_gate.py`，共 43 项全绿）：
- 绿：规则层抛异常 → evaluate 不 raise，降级 ignore/error_degraded（`test_gate_internal_exception_degrades_to_ignore`）；
- 绿（接入点）：`MemoryStorageGate.evaluate` mock 抛 RuntimeError → `create_episodic_memory` 返回 None 不上抛（`test_gate_veto_does_not_break_write_path`）；orchestrator 主链调用点本就 try 包裹且不消费返回值（勘察确认）；
- 绿：语义层超时/坏 payload/断路器开 → 规则默认（3 项）；语义 confirm 自授权被降级（1 项）；kill-switch off 旁路恢复旧行为（1 项）；shadow 永不 veto（1 项）；apply 幂等（pgvector 降级重放路径）（1 项）。

### 真实 LLM 冒烟（9/10 次预算）

qwen3.8-flash，语义层开、live、5s 超时，6 条 R10 歧义残留：3/5 精化命中且类别合理（薄弱科目→store、"随便聊聊"→ignore、"在纠结换课题组"→current_state），2 条延迟尖峰降级规则默认（断路器阈值 3 连续未达、未误开）；首轮 3.0s 超时下 0% 完成 + 断路器实战开启后规则默认稳住——降级路径在真实条件下演练通过。

### 存量回归（受影响域，串行定向）

181 passed / 2 failed / 1 collection error：
- `test_memory_inferred_write_lane.py::test_two_consecutive_sessions_prompt_includes_inferred_memory`、`test_achievement_engine_phase3.py::test_process_event_rolls_back_unlock_when_photon_grant_fails`：**git stash 对照证实均为基线预存失败**（43942d23 无本卡改动同样失败），非本卡引入；
- `test_focus_service_memory.py` 收集错误：worktree 缺 `app/gen/sparkle/inference` 生成产物（gen 不入库），环境性；
- 其余全绿含 M-01 守卫（epistemic contract / migration sqlite / inference write guard / conflict guard 共 15 项）与写路径全部消费方（API/治理/export/jobs/context pack×4/evidence/rule_y/naturalization/integration e2e×2）。

## 5. 改动清单

- 新增 `backend/app/services/memory_storage_gate.py`（单一权威 gate，~1030 行）
- 新增 `backend/tests/unit/test_memory_storage_gate.py`（43 项）、`test_memory_storage_gate_eval.py`（基准守卫）、fixtures/`memory_storage_gate_eval_v1.json`（64 场景）
- 接线 `backend/app/services/memory_service.py`（create_episodic_memory 落库前 gate + veto 短路 + confirm 静默 + 降级重放幂等 apply）
- 配置：`settings.py`（gate 模式 + 语义层四参数）、`aurora_stage19_kill_switch_service.py`（storage_gate 三态绑定）、`business_metrics.py`（gate 决策计数）
- 零迁移、零 proto 改动、零 LLM 主链改动

## 6. 已知边界与残留（如实）

1. 语义层默认**关闭**（规则层即完整能力）；若开启，thinking 档延迟 2-6s，5s 超时下完成率约 60%，建议接入非 thinking 快模型或仅离线批处理开启——已作为部署提示写入 settings 注释。
2. R10 残留（规则歧义推断内容，如"好的，那我先去上课了"无锚点）在语义层关闭时 fail-open 为 store，由 lane 自身置信度机制（MEMORY_INFERRED_MIN_CONFIDENCE=0.9）兜底——非本 gate 职责，语义层开时覆盖。
3. R8 去重为进程内 TTL-LRU（30min/4096 条），跨进程重复由 ConflictResolverService semantic_key 链仲裁（既有职责，未重复实现）；多副本部署下 R8 只保证单进程快速重述去重。
4. 基线预存 2 处失败（见 §4）建议登记后续卡；`test_focus_service_memory` 需 gen 产物才能在本 worktree 跑。
5. event decay "7d" 为写死短窗；若未来事件跨度超 7 天（如两周后考试有 due_at 会走 due_at+7d，无 due_at 的口语日期只会 7d），到期由既有 decay 任务清理——可接受，极端长跨度口语事件需 M-04 抽取侧补 due_at。

## 7. 复现命令

```bash
cd backend
pytest tests/unit/test_memory_storage_gate.py tests/unit/test_memory_storage_gate_eval.py -q   # 43+3 全绿
pytest tests/unit/test_memory_service.py tests/unit/test_memory_inferred_write_lane.py ...     # 受影响域（§4 列表）
# 语义层真实冒烟：settings 三参（ENABLED=True/MODEL=qwen3.8-flash/TIMEOUT=5.0）+ 6 条 R10 残留脚本（本轮已跑，9/10 次预算）
```

## 8. 收工清理

`.env` 临时副本（backend/.env，本卡开工从主仓复制）已删除；/tmp 探针产物已清；无模拟器/浏览器/独立端口进程；无 commit/push。
