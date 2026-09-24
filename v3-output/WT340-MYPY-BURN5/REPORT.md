# WT340-MYPY-BURN5 — mypy 烧减批 5（union-attr 余量收官）报告

- **base SHA**: `450437c0`（main @ 开工时）
- **final SHA**: 分支 `wt340-mypy-burn5` 最新 commit
- **工位**: `/Users/brsama/code/GitHub/Sparkle-sysrev/wt340-mypy-burn5`
- **家族选择与理由**: 继续 **union-attr 余量**（base 105 条）。理由：wt331/wt333 已两轮建立完整修法先例（双调用局部绑定 / None 短路 / 防御分支 / 显式 Any 显式化），同族延续可机械核验、风险最低；余量虽分散（40+ 文件）但单点修法全部落在既有先例类别内。实测 union-attr 105→23（−82），其余 −15 来自同文件邻近家族（修正确类型后连带消除，wt333 同款）。
- **战区回避声明**: 开工核对 wt338/wt339 在航 worktree（均无领先 commit、无未提交触碰面）后执行：未触碰 **galaxy 全目录 + galaxy_service/galaxy_grpc_service/schemas+api galaxy/plans/title_sanitizer/celery_app/plan_tools/task_query_tool/galaxy_plan_consumer**（wt330/334/337 刚合入族谱）；未触碰 **aurora 任何文件**（含 checkpoint_runtime 的 3 条余量，主动放弃）；未触碰 **goal 链**（users/user_settings/user_settings_service/goals/growth_dashboard，wt335 已合 + wt338 在航）；未触碰 chat_modes；未触碰 mobile/gateway 任何文件；**未改 `quality/mypy_baseline.txt`（保持 1375，Forbidden 条款）**。

## 消减数（冷缓存复验，ratchet 同口径 `mypy app --ignore-missing-imports --no-error-summary`）

| 口径 | base | final | Δ |
|---|---|---|---|
| 总错误 | 1375 | **1278** | **−97** |
| union-attr 族 | 105 | **23** | **−82** |
| 连带家族 | — | — | **−15**（arg-type −4、assignment −3、typeddict-item −3、typeddict-unknown-key −2、misc −1、return-value −1、type-var −1） |

- 环境：worktree 无自有 venv，复用主仓 `backend/.venv` python 以 `-m mypy` 运行（cwd=worktree/backend，.mypy_cache 落在本 worktree，主仓零写入）。base 与 final 均冷缓存双跑验证（final 在收尾 ruff I001 修复后第三次冷跑仍 1278）。
- **零新增证明（方法）**：对 base SHA 冷缓存全量清单（/tmp/wt340/base_errors.txt）与 final 冷缓存清单（/tmp/wt340/final_errors2.txt）做「去行号归一化 + multiset 差集」（Counter 对比 `(file, message)` 键）：**新增实例 = 0，消除实例 = 97**。归一化共两层：① 剥行号（`file:line: error:` → `file: error:`）；② **TypedDict Missing/Extra keys 元组内键排序**——本批发现 mypy 对该元组的输出顺序不稳定（同一 `fallback_state` 缺失键集在 base/final 两次冷跑中输出顺序不同：`("error", "review_context", ...)` vs `("enable_deep_review", "error", ...)`），不排序会把同一错误误判为一删一增；排序后 multiset 差集归零。此归一化方法已如实记录，仅影响该 1 对消息。
- 中途新增及当场归零处置（wt333 第 7 类同款）：热缓存中途检查曾出现 6 条新增——achievement_event_consumer 缺 `from typing import Any`（name-defined ×1）、decision_record `Sequence→list`（return-value ×1）、state_aggregator redis-py 双模式桩暴露（misc ×1，按 wt331 库官方 `inspect.isawaitable` 模式修正）、lang_graph_planner 联合坍缩后暴露 3 条存量 TypedDict 级联（见修法类别 8）。全部当场修正后终态冷跑新增=0。
- `git diff` 中 `type: ignore` 出现次数：**0**。

## 逐模块烧减表（union-attr，冷缓存口径，53 个 app 文件 + 2 个收尾文件）

| 模块 | 烧减 | 修法 |
|---|---|---|
| services/progress_narrative_service.py | 3 | `current_plan`/`task` 双调用表达式局部绑定 ×2 |
| services/routing_outcome_service.py | 3 | `_judge_success` signal_scores 双调用局部绑定 |
| services/predictive_service.py | 3 | `prediction` 双调用表达式局部绑定 |
| services/community_service.py | 3 | checkin `Group.get_by_id` None 显式 ValueError（带 group_id，与同函数 2204 行既有 ValueError 同类外抛） |
| services/recommendation_feedback_service.py | 3 | `_interaction_item_type` 集合推导双调用→海象单次绑定；FRIEND 分支 isinstance 联判收窄 |
| services/simulation/simulation_engine.py | 3 | 3 个私有方法补 `self.db is None` 守卫（对齐本类 391/1665/1690 行既有守卫口径） |
| services/community_study_room_service.py | 3 | `in_room` 与 `session is not None` 显式联判（真值表不变）使 mypy 可收窄；`current_session_minutes` 提前计算 |
| api/v1/memory_admin.py | 3 | `getattr+hasattr` 双调用→单次 getattr 绑定，两个查询共用一个谓词局部 |
| api/v1/profile_transparency.py | 3 | `metadata` 双调用 ×2 局部绑定；`learning_goal.strip()` 合并进既有 `or ""` 归一化 |
| learning/statistics.py | 2 | `norm.ppf if HAS_SCIPY else inv_cdf` 双行改写为单表达式（对齐本文件 175/338/403 行既有形态） |
| core/age_client.py | 2 | `self.pool` 局部绑定 + init 后 None 显式 RuntimeError（原 AttributeError 同类外抛） |
| services/feedback_adjustment_service.py | 2 | 过滤推导式→显式循环 `list[Task]`（mypy 无法跨推导式携带收窄） |
| services/routing_parameter_experiment_service.py | 2 | redis 局部绑定 + None 显式 RuntimeError（本方法无回退分支） |
| api/v1/scenario_packs.py | 2 | assign 侧 None 显式 RuntimeError 走既有 except 告警路径；progress 侧 None 早退与 except 同回退 |
| services/intervention_feedback_binding_service.py | 2 | `metadata` 双调用局部绑定 |
| services/milestone_handler.py | 2 | `chat_json` 返回 `Any \| None`：isinstance 落空 dict 走既有空 tasks→None 回退 |
| orchestration/plan_review_service.py | 2 | `result.data or {}` 局部绑定（wt331 translation 同款） |
| services/task_service.py | 2 | getattr 局部显式 Any 注解（原表达式本含 Any，hasattr 守卫保留） |
| services/spine_event_bridge.py | 2 | `_plan_created`/`_srl_transition` metadata 双调用局部绑定 |
| api/v1/chat.py | 2 | learning_preferences 块移入 `if user:` 守卫（真缺陷，见雷达 #1） |
| api/v1/calendar.py | 1 | `event_in`/`event` 跨分支复用改名（`event_update`/`existing_event`），连带消除 assignment ×2 |
| api/v1/accountability.py | 1 | `unlocked_at` 可空列 isoformat 联判（与同 dict 既有 scheduled_for 同款） |
| api/v1/cards.py | 1 | `occurrence_status.value` 可空列三元（与下一行 scheduled_for 同款） |
| api/v1/ingestion.py | 1 | `file.filename or ""`（真缺陷，见雷达 #2） |
| api/v1/memory.py | 1 | INFERRED_META.get 双调用局部绑定 |
| api/v1/signals.py | 1 | redis None 早退与 except 同回退 |
| api/v1/auth.py | 1 | `if is_new_guest:`→`if user is None:`（布尔中转变量打断 mypy 窄化；运行时等价） |
| api/v1/experience/dashboard_router.py | 1 | 生成器内海象单次绑定 completed_at |
| core/agent_persona.py | 1 | identity 双调用局部绑定 |
| core/data_minimization.py | 1 | `configured_mode or getenv(...) or ""` 尾部兜底（值语义逐字等价） |
| core/ingestion/ingestion_service.py | 1 | `para.style` 可空→"" 默认（真缺陷，见雷达 #3） |
| orchestration/agent_scoring.py | 1 | sorted key lambda 双调用→闭包单次绑定 |
| orchestration/lang_graph_planner.py | 1 | persona 单次绑定 + hasattr 守卫（连带消除 TypedDict 族 5 条，见修法类别 8） |
| orchestration/learning_state_fragment.py | 1 | payload 显式 Any 注解（hasattr 守卫保留） |
| orchestration/orchestrator.py | 1 | L1 fast path 日志取值单次绑定（isinstance 分支内提取） |
| orchestration/planning_workflow.py | 1 | redis 局部绑定 + None 显式 RuntimeError 走既有 except 跳过路径 |
| orchestration/response_builder.py | 1 | `correction_visible` 布尔中转→isinstance 内联（窄化可传递） |
| orchestration/situation_brief.py | 1 | payload 显式 Any 注解（与 learning_state_fragment 同款孪生函数） |
| services/achievement_event_consumer.py | 1 | rarity 显式 Any 注解（hasattr 守卫保留）+ 补 Any import |
| services/action_commands/task_commands.py | 1 | getattr 局部显式 Any 注解 |
| services/analytics/dual_core_decision_bench.py | 1 | signal_scores 双调用局部绑定 |
| services/aurora_control_surface_service.py | 1 | surface 条件与取值单次 getattr 绑定 |
| services/decision_record_service.py | 1 | 补本类既有 `db is None` 跳过守卫（record_decision 已有，见雷达 #4） |
| services/device_service.py | 1 | 补本文件既有 `if self.redis:` 守卫（其余 4 处都有，见雷达 #5） |
| services/model_fallback_service.py | 1 | `decision.reason` 可空→日志三元 'unspecified' |
| services/llm/providers.py | 1 | stream=True 契约 cast（AsyncStream，**kwargs 致 mypy 无法择 overload） |
| services/task_occurrence_service.py | 1 | `new_status` 可空列三元 None |
| state_aggregator/service.py | 1 | hasattr 恒真假守卫→显式判空 + isawaitable dual-mode（见雷达 #6） |
| agents/collaboration_workflows.py | 1 | `planner_response.metadata or {}` |
| agents/enhanced_agents.py | 1 | `mastery_levels or {}` 局部绑定 |
| agents/graph/nodes/router.py | 1 | 消息载体显式 Any + getattr 默认值（SparkleState 值类型既有松散性显式化） |
| agents/standard_workflow.py | 1 | `english_question_match` 不可达分支显式兜底（1022 行已保证非 None） |
| **app 文件小计** | **−82 union-attr + −13 连带** | 53 文件 |
| services/action_command_service.py | 0（收尾） | 导入路径精确化（Rule AT，见守卫节） |
| docs/aurora/rule_at_exceptions.md | 0（收尾） | dual_core_decision_bench 例外登记 |
| **合计** | **−97** | 55 文件 |

## 修法类别（类型学正确，零 ignore、零新增消音 Any）

1. **双调用表达式局部绑定**（wt325 #2 / wt331 #1 / wt333 #1 延续）：本批最大成因，12 处。
2. **None 短路/守卫补齐**：redis/session/db/pool 局部绑定，回退值与原「AttributeError 被宽 except 吞」路径一致；三处补的是**同文件/同类已有约定的缺失点**（decision_record、device_service、simulation_engine）。
3. **不可达分支显式失败**：age_client init 后 pool None、rpe redis None、scenario_packs assign redis None——显式 RuntimeError 指明资源与用途（原 AttributeError 同类外抛、可诊断性修复）。
4. **可空列序列化诚实化**：occurrence_status/unlocked_at/new_status/reason 可空缺席落 None/'unspecified'，与同 dict/同调用面既有回退同款。
5. **显式 Any 注解显式化**（wt333 #6 口径）：4 处 hasattr/getattr 模式，局部 `Any` 系原表达式本就含有的 Any 显式化，运行时守卫全部保留。
6. **布尔中转打断窄化修复**：auth `is_new_guest`、response_builder `correction_visible`、study_room `in_room`——条件改写为 mypy 可传递的形式，运行时真值表逐字等价。
7. **有据 cast**：仅 llm/providers 1 处——`stream=True` 时 openai SDK 契约恒返 AsyncStream，`**kwargs` 使 mypy 无法选择 overload（注释写明契约；wt331 collaboration 同款）。
8. **lang_graph_planner 级联处置**：`initial_state: SparkleState` 注解系谎言——字面量在下方三段条件更新（162-179 行）后才成为完整 SparkleState，构造点从未满足该 TypedDict；base 中同行 union-attr 错误恰好抑制了严格校验，修正后暴露 5 条存量（missing/extra keys、messages 不变型、mode_strategy 未知键、update 不兼容）。按字面量真实类型改注解 `dict[str, Any]`（构造期诚实类型；下游 `graph.ainvoke` 接受 dict），5 条连带消除且不引入行为变化。

## 真缺陷 / 类型谎言雷达

1. **chat.py `learning_preferences` AttributeError 截断整个 context**（api/v1/chat.py:957）：块级代码引用 `user.depth_preference` 但位于 `if user:` 守卫**外**——user 行缺席时 AttributeError 被外层 `except Exception`（1043 行）吞掉，`recent_tasks`/`plans`/`knowledge_stats` 等**全部后续 context 段静默丢失**。这正是同文件 997 行 GAIN-FIX 红旗3 注释自述的「半坏」形态的第二处实例（注释只修了 Plan.is_completed 一处）。已把该块移入 `if user:` 守卫内（user 缺席时仅缺这一个键，其余段存活）。**本批最重要缺陷修复**；覆盖测试：test_chat_legacy_user_context 6 passed。
2. **ingestion `splitext(None)` TypeError → 500**：UploadFile.filename 按 starlette 契约可为 None，原代码直接 `.lower()` 链上炸出 500；现 `or ""` 落空扩展名走既有 400「file type not allowed」（客户端错误正确归类）。
3. **ingestion_service `para.style` 可空 AttributeError**：python-docx 段落 style 可为 None，原代码整篇解析中断；现空样式落 ""（非 header、metadata 记空串）。
4. **decision_record_service 类内守卫不一致**：`record_decision` 有 `db is None` 跳过守卫、`get_recent_records` 没有（None 时裸 AttributeError）——补齐本类既有约定（跳过 + warning 日志，返回 []）。
5. **device_service 文件内守卫不一致**：同文件 4 处 `if self.redis:` 守卫，唯独 `_cache_device_tokens` 裸解引用——补齐文件既有约定。
6. **state_aggregator hasattr 恒真假守卫第二例**：`hasattr(cache_service, 'redis')` 对模块级单例恒真（wt331 achievement_engine 同款模式的又一实例），防不住 None；改显式判空 + redis-py 官方 isawaitable dual-mode。
7. **recommendation_feedback「判 A 调用、取 B 调用」脆弱模式第二例**（wt333 planning 第一例）：`_interaction_item_type` 在集合推导中各调用两次；当前为纯读选择器未构成现行 bug，已坍缩单次绑定（预防性）。同文件 FRIEND 分支对 payload.strategy 的跨变体解引用改为 isinstance 联判——调用不一致（FRIEND item_type + Group payload）时从「中途 AttributeError」变为「跳过整支」，防御性修复。
8. **community_service checkin group None 无诊断**：`Group.get_by_id` None 未检，AttributeError 无 id 信息；现 ValueError 带 group_id，与同函数既有 linked_goal 校验（2204 行）同类外抛。
9. 其余烧减点均为类型收窄失败而非运行时缺陷；所有 None 短路分支与既有回退语义逐一对齐（见逐模块表注）。

## 测试证据（DATABASE_URL=sqlite+aiosqlite 内存库 + 占位 SECRET_KEY，路径均经 find 实证）

| 批次 | 文件 | 结果 |
|---|---|---|
| 1 | accountability_api / auth 空凭据+refresh+session_touch / calendar api+service+kill_switch / chat_legacy_user_context / ingestion api+service / memory_api / memory_admin_api / profile_transparency_api / scenario_packs / data_minimization | **72 passed + 4 failed** |
| 2 | achievement_event_consumer+publishers / aurora_control_surface / community_study_room+squad_mvp / dual_core_decision_bench / feedback_adjustment_delete_task / intervention_feedback_binding / milestone_command_path / progress_narrative / recommendation_feedback_api / routing_outcome_backfill / simulation_runner / spine_event_bridge / task_service / ab_test_statistics / situation_brief | **116 passed** |
| 3 | plan_review_service+breaker / planning_workflow+cold_start / response_builder_semantic_meta+mixins / standard_workflow fallback+routing / router_node_learning+sufficiency / working_memory_aggregator / enhanced_orchestrator / predictive extension+productization / router_absolute_quality | **140 passed + 3 skipped** |
| 4（收尾新增碰面） | test_action_command_service | **29 passed** |

- **4 个失败（test_memory_admin_api 的 stage18/19/21/expanded_aurora kill_switch）在 base HEAD 干净克隆**（`git clone <worktree> /tmp/wt340-baseline`，按并发安全纪律未用 stash/reset）**逐字复现同失败集**——kill_switch 写入需真 Redis（测试日志明示 "called without Redis; write ignored"），全部为存量环境失败，与本批无关。合计 **357 passed + 3 skipped，0 新增失败**。
- Rule AT 收尾引入的 action_command_service 单独跑 test_action_command_service 29 passed。

## 守卫与 ruff

- `bash scripts/run_all_rule_guards.sh` → **EXIT 0**（83 条全过；终态复跑二次确认。gen 三件套已按协议以 `cp -RL` 从主仓复制 backend/app/gen、gateway/gen、mobile/lib/gen，gitignored 不入库）。
- **Rule AT 事件与处置**（本批唯一的非预期守卫交涉）：改动把 action_commands/task_commands.py 与 analytics/dual_core_decision_bench.py 纳入守卫 scope 后报 AT001「no runtime import outside tests」。
  - task_commands：**守卫 AST 盲区误报**——真实运行时链 `action_command_service.py:61 → action_commands/__init__.py → task_commands` 存在，但守卫跳过 `__init__.py` 作为 importer 且无法解析包成员别名。处置=把 action_command_service 的导入从包再导出**精确化到定义模块**（同一对象、语义零变化、依赖图对静态工具变真），不属「为数字改语义」。
  - dual_core_decision_bench：**真 orphan-by-design**——模块自述 "intentionally read-only" 离线决策审计器，app 内零导入方、有直接单测，与文档既有 planning_benchmark_evaluator/profile_eval_runner 完全同类。按守卫设计机制登记进 `docs/aurora/rule_at_exceptions.md`（该文档无冻结棘轮，登记即设计内用途）。
- 54 个被碰 backend 文件 `ruff check --fix` → **All checks passed**（含 action_command_service 1 处 I001 自动整理；其余 53 文件零自动改动）。
- `git diff` 中 `type: ignore` 出现次数：**0**。

## 其它

- `/tmp` 自产清理：/tmp/wt340/（base/final 错误清单、mid 检查、守卫日志）与基线克隆 /tmp/wt340-baseline 收工自清。
- worktree 内 `backend/app/gen`、`backend/gateway/gen`、`mobile/lib/gen` 为 gitignored 生成物副本。
- 遗留台账：union-attr 余量 23 条全部位于本批战区回避集合（galaxy 13 + aurora checkpoint_runtime 3 + 其余 7 条在 goal/chat_mode 相邻文件），待战区解禁后一批收尾即可清零该家族。
