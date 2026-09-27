# WT730 — kill_switch 邻批扫雷（V3-FIX-443 批次）

2026-09-27 ｜ 分支 `agent/node-b/wt730/ksweep`（base a0e80368）｜ worktree `Sparkle-sysrev/wt730-ksweep`

任务：kill_switch 邻批类扫雷——沿 FIX-348 一族（守卫反装/假开关）与 FIX-187/189（旁路直读）、FIX-415（假关断幽灵信号）口径，对仓内 kill switch / feature flag / 紧急停摆面按四模式走查：

1. 守卫反装（`if enabled: 正常 else: 禁用` 写反/嵌套错）
2. 开关读取旁路（直读 env/legacy bool 绕三态门）
3. 假关断（off 仍走部分副作用）
4. 假开（宣称可控的死面）

---

## 一、扫雷面清单（27 面，BINDINGS 全表）

经 `aurora_*_kill_switch_service.py` ×20 + `fme_kill_switch_service.py` + `dual_core_router` 的 BINDINGS 集全表与全仓 import 图（62 消费文件），逐面四模式走查：

| 族 | 面 | 模式1 反装 | 模式2 旁路 | 模式3 假关断 | 模式4 假开 |
|---|---|---|---|---|---|
| 18 | aggregator / push_policy / push_delivery | ✓ | ✓（legacy bool 仅兜底，FIX-21/186 已闭） | ✓（deliver off→None） | ✓ |
| 19 | working_memory / llm_extractor / consolidation / storage_gate | ✓ | ✓（FIX-189 已闭） | ✓（consolidation live-only 写车道为既定语义） | ✓ |
| 20 | sufficiency_judge / conflict_resolver | ✓ | ✓（FIX-187 已闭） | ✓ | ✓ |
| 21 | skill_store / skill_selection / skill_share | ✓ | ✓ | ✓ | ✓ |
| 23 | bayesian master | ✓ | ✓ | ✓（off→早退） | ✓ |
| 24 | policy_compiler / scheduler | ✓ | ✓ | ✓（off→skip+metric） | ✓ |
| 25 | reflection_wire | ✓ | ✓ | ✓（off→skip+metric） | ✓ |
| 26 | scene | ✓ | ✓ | ✓（off→disabled；读面 `!=live`→[]） | ✓ |
| 27 | foresight master / attractor / deviation / jitai | ✓ | ✓ | ✓（attractor celery 面 FIX-108 已挂门） | ✓ |
| 28 | traits master / nlp / coldstart | ✓ | ✓ | ✓（off→None/空） | ✓ |
| 29 | srl master / tracker / bridge / scaffolding_consume | ✓ | ✓ | ✓（srl_events off→None） | ✓ |
| 30 | metacog master / dashboard / process_scaffolding / fsm_combine | ✓ | ✓ | ✓（off→空快照；fsm_combine `!=live`→None） | ✓ |
| 31 | idiographic | ✓ | ✓ | ✓（off 写空缓存；读 `!=live`→None） | ✓ |
| 33 | master / social / srl / wm_prompt / events / community | ✓ | ✓ | ✓（community celery 面 FIX-109 双层门在位） | ✓ |
| 34 | master / capsule / journey_subscribers | ✓ | ✓ | ✓ | **✗→发现 A（error_bridge 死绑定）** |
| 35 | metacog_router | ✓ | ✓ | ✓（off/shadow 剥 hint） | ✓ |
| 37 | llm_safety | ✓ | ✓ | ✓（off 仍保 SEC-1 floor=PII+output validate，正确设计） | ✓ |
| 38 | err_replan / push_scheduler | ✓ | ✓ | **✗→发现 B（err_replan off 全链照跑）** | **✗→发现 C（aurora_runtime 死门）** |
| 39 | master / scaffolding_prompt / cogload_route / galaxy_inject | ✓ | ✓ | ✓ | ✓ |
| 40 | calendar | ✓ | ✓ | ✓（off→{}） | ✓ |
| dual_core | master | ✓ | ✓ | ✓（off→legacy 路径） | ✓ |
| doc_context | document_context_injection | ✓ | ✓（fallback 读 settings 合法=服务异常兜底） | ✓（off→跳过注入） | ✓ |
| privacy | pii_redaction | ✓ | ✓（run_until_complete 缝已修，R2-04） | ✓ | ✓ |
| fme | goal_first_minute | ✓ | ✓ | ✓（FIX-345 后单活绑定有真读者） | ✓ |
| 非 Aurora 族 | budget_tuning / ltm_rollout / within_category(TOOL_PREF) / ENABLE_AURORA_RUNTIME_V1(orchestrator:940) | ✓ | ✓（独立 env 判据、无三态门族属，非旁路） | ✓ | ✓ |

## 二、发现（3 条，2 修 1 登记）

### 发现 C（修，P2）：runtime_v1 aurora_runtime 门恒 ValueError→缺省 shadow，off 分支死路（假开/死面）

- `app/aurora/runtime_v1/service.py:595`：`AuroraStage38KillSwitchService().get_feature_mode("aurora_runtime")`，但服务 `_BINDINGS` 仅 `err_replan`/`push_scheduler`——`_resolve_binding` 抛 `ValueError: Unknown Stage38 feature: aurora_runtime`，被调用方宽 `except Exception` 吞掉，`kill_switch_mode` 恒落缺省 `"shadow"`。R8-P1-03 off 分支（最小 TurnPlan）**不可达**，无任何 env/Redis 通道可关停 runtime 决策管线（本门承诺的 Redis 临场覆盖不兑现）。
- 既有旁证：`tests/unit/test_aurora_runtime_v1.py:452-454` docstring 明文记载「当前未注册 aurora_runtime binding，get_feature_mode 恒 ValueError→缺省 shadow（binding 接线属后续开关接入工作）」——既有测试靠桩掉 get_feature_mode 才到达 off 分支。
- 修法（接线，非撤面——读者真实存在，FIX-345 registered-iff-read 契约的反向半边成立）：stage38 服务补注册 `aurora_runtime` binding（`settings_attr=AURORA_STAGE38_AURORA_RUNTIME_MODE` 默认 live；`legacy_bool_attr=ENABLE_AURORA_RUNTIME_V1` 缺席兜底——orchestrator.py:940 主入口本就吃该 bool，语义闭环）；`summary()` 增第三键+模块尾 gauge 同形；settings.py 增 tri-state 声明。修后 off=最小 TurnPlan 可经 env/Redis `aurora_stage38:aurora_runtime_mode` 双通道触达。
- 红→绿：新增 `test_wt730_ksweep_faces.py` 面 1 五测修前全红（tri-state off/live 解析 ValueError、legacy bool 兜底 ValueError、真链路零桩 settings off 仍跑全管线、summary 三键缺）→修后绿；`test_aurora_runtime_v1.py` 过时注记作废改写（桩保留隔离分支行为面）。

### 发现 B（修，P2）：err_replan off 假关断——bridge 全链副作用照跑

- `app/services/error_replan_bridge.py:on_error_created`：mode 判据仅三路——shadow→影子记录+legacy 判据、live→stage34 判据、**off→else 落 legacy 判据后继续跑全链**：mastery echo 落库、次日修复任务插入、InterventionRecord 创建、plan 调整通知、`AdaptiveReplanner.evaluate_plan_health_now`、弱节点 claim 写 Redis。翻 off 唯一差异=不写影子记录+用 legacy 阈值——**开关关不断特性**（调用方 `galaxy_event_consumer.py:149` 无外门）。与 FIX-108/109（开关 off 链照跑）及 FIX-415（幽灵信号）同族。
- 红证实录（修前）：`test_wt730_ksweep_faces.py::test_err_replan_off_stops_bridge_without_side_effects` → `assert result["triggered"] is False` 得 `assert True is False`；日志同屏实录 `ErrorReplanBridge: triggered immediate plan-health evaluation ... mode=off threshold=3`。既有 `test_error_replan_bridge.py:495` 仅钉 `mode in ("shadow","live")`，off 行为零钉测。
- 修法：mode 解析后 `if mode == "off": return self._blocked(mode=mode, gate="kill_switch_off")` 早退（先于一切副作用；对齐 social bridge `kill_switch_off` 与 community bridge `!= live` 早退语义）。语义钉死：off=零副作用跳过、shadow=legacy 判据+影子记录、live=stage34 判据。默认部署（settings live）行为零变化。

### 发现 A（登记不修，P3）：stage34 `error_bridge` tri-state 绑定死面（FIX-341/345 假开关同族）

- `aurora_stage34_kill_switch_service.py:21-26` 的 `error_bridge` 绑定（`AURORA_STAGE34_ERROR_BRIDGE_MODE` / Redis `aurora_stage34:error_bridge_mode`）**零行为读者**：全仓消费仅 `summary()` 遥测（context_builder `_stage34_modes_payload` 只取展示、profile_context 只取 capsule_mode）。真实 bridge 由 stage38 `err_replan` 治理（error_replan_bridge.py:47 `AuroraStage34KillSwitchService = AuroraStage38KillSwitchService` 别名即 stage34→38 迁移残根）——运维翻 stage34 error_bridge 旗（env 或 Redis）遥测值变、行为零变化。
- 不修裁决：撤面按 FIX-345 先例需动 summary 键形（`test_stage34_kill_switch.py` 三处钉值）+ context_builder fallback 负载形 + 防复活守卫，属独立小卡；day7 终门前不动遥测负载形。登记移交。

## 三、四模式总结论

- 模式 1（守卫反装）：全仓 27 面零新发现——既往 FIX-21/108/109/186/187/189 批次后极性全部正确（`not enabled→skip` / `enabled→do` / live-only 写车道语义一致）。
- 模式 2（读取旁路）：零新发现。legacy bool 直读残留 3 处均为注释（routing_engine.py:1158 / aggregator_backed_social_context_provider.py:50 / conversational_extractor.py:49）；`resolve_settings_mode` 三态门为唯一判据的收口在 HEAD 成立。context_builder/orchestrator 的 settings 回落读均为服务异常 fallback 分支，合法。
- 模式 3（假关断）：1 新发现=发现 B（已修）。stage37 off 保 SEC-1 floor、context_budget off 返回 base、idiographic off 写空缓存（诚实空投影非残留）均为正确形态。
- 模式 4（假开）：2 新发现=发现 C（已修）+发现 A（登记）。

## 四、验证（本 worktree 实录）

- 红→绿：`tests/unit/test_wt730_ksweep_faces.py` 6 测修前 6 红（含 ValueError 直证与 off 全链 `triggered=True` 实录）→修后 6/6 绿；触达族 `test_stage38_kill_switch.py`（summary 钉测三键化+redis override 三键化）+`test_aurora_runtime_v1.py` +`test_error_replan_bridge.py` +`test_error_replan_bridge_stage34.py` 合跑 38/38 绿。
- 邻域回归：27 个 kill switch 套件（含 wt422 celery 面矩阵 10 测）+`test_scheduler_push_kill_switch.py`+`test_aurora_runtime_checkpoint_service.py`+`test_stage38_d3_persistence.py` 合跑 **136/136 绿**。
- mypy：worktree stash 对照 base 147 = 修后 147 零漂移（台账引 146 与本环境差 1 为环境既有，同 wt707 先例；触达 3 app 文件 0 错）。
- ruff：触达 6 文件 All checks passed（新文件 import 排序已 --fix）。
- black：新文件已格式化；3 个既有触达文件为 base 既有漂移（base 版单独 --check 同红，black hunks 与本次新增行零重叠，V3-FIX-05 形制）。
- 台账：`ledger_union_merge.py --verify` 通过（312 行 8 裸管零 FAIL）→登行后复跑通过（313 行）。

## 五、改动面

- `backend/app/services/aurora_stage38_kill_switch_service.py`（+aurora_runtime binding/summary/gauge）
- `backend/app/config/settings.py`（+AURORA_STAGE38_AURORA_RUNTIME_MODE）
- `backend/app/services/error_replan_bridge.py`（off 早退门）
- `backend/tests/unit/test_wt730_ksweep_faces.py`（新增 6 测）
- `backend/tests/unit/test_stage38_kill_switch.py`（summary/override 钉测三键化）
- `backend/tests/unit/test_aurora_runtime_v1.py`（过时注记作废）
- `v3/06_agent_fleet/DYNAMIC_ISSUES.md`（V3-FIX-443 行）
