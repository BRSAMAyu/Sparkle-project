# WT349-MYPY-BURN6 — mypy 烧减批 6（attr-defined 主族 + 连带家族）报告

- **base SHA**: `b280d38a`（main @ 开工时）
- **final SHA**: 分支 `wt349-mypy-burn6` 最新 commit
- **工位**: `/Users/brsama/code/GitHub/Sparkle-sysrev/wt349-mypy-burn6`
- **家族选择与理由**: 卡面原定「union-attr 剩 23 条清完后转下一家族」。开工实测确认 **union-attr 剩余 23 条全部位于战区回避集合**（aurora 7 + services/galaxy/ 与 galaxy_service/galaxy_event_consumer 15 + api/v1/goals.py 1；wt340 报告遗留台账与此一致），另 card_protocol 4 条因债务台账（KNOWN_CODE_DEBT_LEDGER：card_protocol mid-flight 迁移、先查 shadow 状态）一并冻结。故主族直接转入 **attr-defined（base 133 条，全库第三大族）**：其聚类密度最高（context_builder 23 + graph-nodes 14 + spine_orchestrator 13）、且真缺陷密度最高——本批雷达 12 项运行时级缺陷全部出自该族及其相邻文件。连带家族：agent_scoring 签名放宽连带 arg-type、同文件变量改名连带 assignment/misc 等。
- **战区回避声明**: 未触碰 galaxy 全族（services/galaxy/ 零触碰、galaxy_service.py、galaxy_grpc_service.py、api/v1/galaxy.py、schemas/galaxy.py、galaxy_event_consumer.py、title_sanitizer）、aurora 全部文件、chat_mode、growth dashboard、goal 创建链（api/v1/goals.py、user_settings_service 等）、memory_admin 测试族、l10n、card_protocol/。开工核对 wt345/346/347/348/350 五个在航 worktree（无领先 commit；wt350 仅碰 mobile Dart 文件），无后端 Python 交叠。未改 `quality/mypy_baseline.txt`（保持 1278，Forbidden 条款）。

## 消减数（冷缓存复验，ratchet 同口径 `mypy app --ignore-missing-imports --no-error-summary`）

| 口径 | base | final | Δ |
|---|---|---|---|
| 总错误 | 1278 | **1103** | **−175** |
| attr-defined 族 | 133 | **15** | **−118** |
| 连带家族 | — | — | **−57**（arg-type −26、assignment −10、valid-type −5、operator −5、override −3、var-annotated −3、misc −2、call-overload/call-arg/no-any-return 各 −1） |

- 环境：worktree 无自有 venv，复用主仓 `backend/.venv` python 以 `-m mypy` 运行（cwd=worktree/backend，.mypy_cache 落在本 worktree，主仓零写入）。base 与 final 均冷缓存验证（final 为收尾 ruff/终版代码后冷跑 1103）。
- **零新增证明（方法）**：对 base SHA 冷缓存全量清单（/tmp/wt349/base_errors.txt）与 final 冷缓存清单（/tmp/wt349/final_errors2.txt）做「去行号归一化 + multiset 差集」：Counter 对比 `(file, message, code)` 键，**新增实例 = 0，消除实例 = 175**。归一化共两层：① 剥行号；② TypedDict Missing/Extra keys 元组内键排序（wt340 已记录的 mypy 输出顺序不稳定问题；本批 collaboration.py 3 条 Missing keys 仅键序不同，排序后完全一致，避免误判为一删一增）。
- `git diff` 中 `type: ignore` 出现次数：**0**。新增显式 `Any` 注解均系「既有松散性显式化」口径（wt331/333/340 先例）：mixin 契约 `redis: Any`（组合方 orchestrator 的 redis_client 形参本未注解）、`type[Any]` 承接异构 SQLAlchemy 模型 map、importlib 动态模块别名 `Any`、成就注册表值混装 `dict[str, dict[str, Any]]`。

## 真缺陷 / 类型谎言雷达（12 项运行时级，红测先行；4 项配红测）

1. **GDPR 硬删除任务三连断**（core/celery_tasks.py `purge_deleted_account`）：① `from app.models.achievement import UserStreakDays` 模型名笔误（实名 UserStreakDay）→ import 恒 ImportError，任务从未跑到删除一步；② `_purge_redis_keys` 调 `cache_service._get_redis()`——CacheService 从无此方法（真实访问面 `.redis` 属性）→ AttributeError 被 retry 吞；③ redis SCAN 循环 `cursor = b"0"`/`while cursor:` 与 asyncio 桩 int 契约不符（若按类型修成 int 0 会被 `while cursor:` 直接跳过循环——改显式 break 等价形式）。红测：test_purge_task_no_longer_references_nonexistent_streak_model（base 上 ImportError 红）。
2. **cache 失效任务 import 谎言**（celery_tasks `invalidate_cache`）：`from app.core.cache import redis_client`——cache.py 从未导出模块级 redis_client（唯一入口 cache_service.redis）→ ImportError 经 retry 耗尽任务必死。改 cache_service.redis + 显式 None RuntimeError（重试语义不变）。
3. **cognitive insights payload 整体夭折**（orchestration/context_builder.py:596）：`self._build_cognitive_prompt_guidance(...)` 全仓从未有过该方法的定义（git log -S 只见 initial commit 引用）→ return 行必 AttributeError 被 except 吞成 `{"has_cognitive_patterns": False}`——凡有 patterns 的用户整个 payload 被丢弃。消费方 prompts.py `_render_cognitive_prism` 对 guidance 空值本有 `or ""` 容忍；落 `""` 交付 payload 其余字段。红测：test_wt349…（配 `current_guidance` 契约注释）。
4. **self_model 上下文从未进 payload**（context_builder ~1350）：`SparkleSelfModelService.get_readout_summary(...)` 是实例方法却被类级调用 → TypeError（missing self）被 `contextlib.suppress(Exception)` 吞，`payload["self_model"]` 永不出现。按 spine_orchestrator/outcome_consumer 同文件先例以 redis 实例化后调用。
5. **growth 工具缺 await**（tools/growth_strategy_tools.py）：`SituationBriefBuilder.build` 是 async（situation_brief.py:272），原未 await 即取 `.to_dict()` → 运行时必 AttributeError，该工具从未成功返回。补 await。
6. **STT ABC 契约谎言**（services/stt/providers/base.py）：`transcribe_stream` 协程式声明（体内无 yield）而全部实现均为 async-generator、调用方直接 `async for`——wt331 LLMProvider.stream_chat 同款。声明体补永不执行的 yield。红测：isasyncgenfunction 断言（base 上红）。
7. **dormant 注入聚合三连错**（api/v1/chat.py:180-188）：`from app.state_aggregator.service import StateAggregator`（实名 StateAggregatorService）+ `UserStateFieldName.ENGAGEMENT_STATE/.LEARNING_STATE/.ACTIVE_SKILLS`（UserStateFieldName 是 Literal 字符串别名、无枚举成员；真实成员 "engagement_state"/"learning_state"/"active_skills_summary"）→ AttributeError 被 except 吞成整段聚合跳过，dormant 注入上下文从未构建。改实名 + 字面量成员。
8. **quality guard 降级计数从未生效**（signals/spine_orchestrator + spine_metrics）：`self.metrics.record_spine_degradation(...)`——SpineMetricsCollector 上从无该方法（同名权威实现在 business_metrics）→ AttributeError 被外层 except 吞，降级事件从未计数。在 collector 上补委托方法（async 包装同步权威实现）。
9. **策略信念更新循环恒空转**（spine_orchestrator `_enrich_pipeline_post_policy`）：`getattr(effect, "strategy_key", None) or effect.get("strategy_key")`——get_recent_policy_effects 恒返 PolicyEffectEntry dataclass，其字段是 `policy_key`（写入侧 outcome_recorder:301 以 policy_key=record.reason 落账）→ strategy 恒 None，learning_base 信念更新从未执行。改直读 `effect.policy_key`（getattr/dict 双重死防御一并清除）。
10. **notification 指令事件从未发出**（signals/directive_store.py `store_notification`）：publish payload 读 `nd.notification_type`/`nd.user_visible_reason`——NotificationDirective 无此二字段 → AttributeError 被吞，`spine.notification_directive` 事件从未发布（当前无订阅方，键面即真实契约）。改按 dataclass 真实字段（channel/trigger/message_strategy）发布。
11. **UX 风险卡整体夭折**（spine_orchestrator `get_ux_risk_warning`）：① 405-409 行读 `directive.max_task_duration_min/required_task_type/avoid_new_chapter`——约束实际落在 hard_constraints dict（policy_engine/exam overlay 写入面），dataclass 上从无此三属性 → directive_summary 永远生不出来；② 3083 行读 `active_dir.primary_strategy`——该字段在 PolicyDecision 不在 directive → AttributeError 被外层 except 吞成 None，风险卡从未渲染。修复：约束改读 hard_constraints；策略按 get_rendered_timeline 既有模式从 `spine:policy:{id}` 读回（为此给 PolicyDecision/UserVisibleReceipt 补了与 types.py 全文件 from_dict 约定一致的 classmethod——get_rendered_timeline 原有的两处 from_dict 调用同样是必炸后被吞的死路径）。
12. **annotation 谎言与松散键显式化**（非运行时缺陷，类型学修复）：db/session.py `get_db/get_db_no_commit` 体内 yield 却注解 `-> AsyncSession`（llm_service 两处 `__anext__` 报错根因）；`learning/rolling_correlator.CorrelationResult` 无 dim_pair 而 idiographic:686 直读（改走本服务既有 `_dim_pair(dim_a, dim_b)`）；expansion_service 迭代 ExpansionApplyResult（dataclass 非 iterable，改读 created_nodes——expanded_nodes 落库从未成功）；error_book 读不存在 settings.GATEWAY_URL（实名 GATEWAY_INTERNAL_URL，sparkle-file 图片解析从未走通）；daily_task_selection 调 AuroraRuntimeStore.load_energy（方法在 AuroraEnergyStore 上）；file_processing 对 VectorChunk dataclass 用 `.get("text")`（字段实名 content）；achievement_engine SPRINTS_STREAK 因函数级 `result/query` 变量首绑定类型锁定把 ORM 行推成 int（改名+显式 Sequence[Plan]）；main.py lifespan 删除 event_bus=None 死占位（import 立即重绑）修复 begin_shutdown/close 的 None 类型错位；policy_patch 证据收集 dict 声明 tuple 却 append（消费侧 tuple() 等价，实为注解谎言非运行时炸点）；agent_scoring.record_from_runtime `state: dict[str, Any]`→`Mapping[str, Any]`（调用方传 TypedDict 的只读事实契约，连带清 10+ 条 arg-type）。

## 逐模块烧减表（主要文件，冷缓存口径）

| 文件 | 修法概要 |
|---|---|
| orchestration/context_builder.py（26→0） | Mixin 契约纯注解声明（redis/state_manager/context_pruner/_experiment_cohort_for_user/_self_heal_versions，TYPE_CHECKING 导入，运行时零效果）；current_guidance 兜底（雷达3）；self_model 实例化（雷达4）；by_type 显式注解。连带 −no-any-return |
| signals/spine_orchestrator.py（13→2，余 2 为 dispatch 遗留见下） | 约束读 hard_constraints、primary_strategy 走 spine:policy 读回、belief 循环改 policy_key（雷达10/11） |
| agents/graph/nodes/ 7 文件（16→0） | `_planning_constraints` 松散键统一 isinstance 收窄：6 文件新增 `_route_intent_from_constraints` 助手、collaboration 两处就地收窄（dict/缺失/脏值三态与原 `or {}` 等价） |
| orchestration/agent_scoring.py（连带） | record_from_runtime state 收窄 dict→Mapping（TypedDict 只读契约） |
| api/v1/chat.py（4→0） | StateAggregatorService 实名 + Literal 字面量成员（雷达7） |
| core/celery_tasks.py（5→0） | 雷达1/2 |
| core/metrics.py（5→0） | 补注册 DOC_* 五指标（类型/标签以 _report_metrics 实际用法为准） |
| services/document_service.py | 同上消费方 |
| services/memory_provenance_service.py（6→0） | `_SUPPORTED_KINDS: dict[str, type]`→`dict[str, type[Any]]`（异构模型 map 松散性显式化） |
| services/openclaw/url_guard.py（5→0） | `_BaseAddress`→`IPv4Address | IPv6Address` 联合收窄（ip_address() 恒返具体类型） |
| services/graph_knowledge_service.py（2→0） | vector_service（KnowledgeService 实例）上调用其不存在的 update_node_status/get_user_nodes——**deferred 未修**（见下） |
| services/cognitive_service.py（4→0） | result/analysis 变量首绑定冲突改名 + pydantic 属性跨语句窄化局部绑定 |
| services/personalization/inferred_preference_decay_service.py（2→0） | 同型 result 变量复用改名 decay_result |
| services/error_replan_bridge.py（5→0） | feature_bundle 值类型 object→Any（松散 bundle 契约显式化） |
| services/source_lifecycle.py（1→0） | 登记表值结构 dict[str, list[_RetrievalInvalidationPlan]]→TypedDict（plans/tasks 异构） |
| services/idiographic_association_service.py（1→0） | item.dim_pair→_dim_pair(item.dim_a, item.dim_b)（雷达12） |
| services/simulation_runner.py（1→0） | importlib 动态别名显式 Any |
| services/expansion_service.py（1→0） | 迭代 ExpansionApplyResult→created_nodes（雷达12） |
| services/file_processing_orchestrator.py（1→0） | VectorChunk.get("text")→.content（雷达12） |
| services/error_book_service.py（1→0） | GATEWAY_URL→GATEWAY_INTERNAL_URL（雷达12） |
| services/daily_task_selection_service.py（1→0） | AuroraRuntimeStore→AuroraEnergyStore（雷达12） |
| services/achievement_engine.py（1→0） | SPRINTS_STREAK 变量首绑定类型锁定（雷达12） |
| services/understanding_dimensions_service.py（3→0） | type[Any] map + Row 显式索引取列 + 变量改名 |
| services/node_sector_service.py（1→0） | source 统一 list[tuple]（dict_items 无 append 为类型面问题，运行时原本不炸——分类为类型修复非运行时缺陷） |
| core/policy_patch.py（2→0） | 证据收集注解 tuple→list（同上分类）+ 消费期变量改名 |
| core/websocket.py（2→0） | 动态 user_id 统一挂 websocket.state（读写四点同步，运行时逐连接等价） |
| main.py（2→0 连带 6） | event_bus=None 死占位删除；收尾段 8 个同名局部变量改名 _stale 后缀 |
| orchestration/adaptive_replanner.py（2→0） | spec 显式 dict[str, Any] |
| orchestration/context_retrieval_pipeline.py（1→0） | isawaitable 后 Awaitable.close 用 isinstance(Coroutine) 收窄 |
| agents/graph/workflow.py（2→0） | last_message.tool_calls→getattr 三参（wt340 router 同款） |
| agents/graph/nodes/collaboration.py 等 | 见上；其 3 条 Missing keys 为键序不稳定，非新增 |
| db/session.py（连带 2） | get_db 注解谎言修正（雷达12） |
| signals/types.py（连带 2） | PolicyDecision/UserVisibleReceipt 补 from_dict（全文件既有约定） |
| signals/spine_metrics.py（连带 2） | record_spine_degradation 委托权威实现（雷达8） |
| tools/growth_strategy_tools.py（1→0） | 补 await（雷达5） |
| services/stt/providers/base.py（1→0） | ABC async-gen 契约（雷达6） |
| services/accountability_achievement_service.py + tasks/accountability_tasks.py（5→0） | 注册表/stats dict 显式 Any |
| services/memory_provenance / understanding_dimensions | 同上注解修正 |

## Deferred（战区/范围外交付阻塞，不当成本批失败）

- **services/galaxy/crdt_persistence.py:57**：`from sqlalchemy import insert`（泛型）+ `.on_conflict_do_update` —— 泛型 Insert 无此方法，CRDT 持久化 upsert 首调必 AttributeError；正修需改 `sqlalchemy.dialects.postgresql.insert`。**位于 galaxy 回避区，未动**，移交战区解禁后处理（附证据）。
- **services/galaxy/provenance.py:53**：status（object 型）上赋 learning_path_snapshot —— 同属 galaxy 区，未动。
- **spine_orchestrator.py:2348 `ExternalIntegrationGateway.dispatch`**：docstring 承诺「ExternalRawEvent→ActionableSignal 翻译」但该方法从未实现（gateway 只有 route_to_spine 路由回执）；实现需逐 source 的翻译语义，属功能开发非类型修复。on_external_event 入口今日为静默 no-op（AttributeError 被吞）。移交产品卡。
- **graph_knowledge_service.py:284/350**：GraphKnowledgeService.update_node_status / get_learning_path 内部调用 KnowledgeService 上不存在的 update_node_status/get_user_nodes（真实面仅 update_node_mastery）——两公开方法零外部调用方（graph_monitor 只用 graph_rag_search），属死代码但修法（删方法 or 实现 UserNodeStatus join）超出类型烧减授权。移交。
- **card_protocol 4 条 union-attr**：台账 mid-flight 迁移，冻结。

## 测试证据（DATABASE_URL=sqlite+aiosqlite:///:memory: + 占位 SECRET_KEY，路径均经 find/ls 实证）

| 批次 | 文件 | 结果 |
|---|---|---|
| 1 | tests/unit/test_spine_orchestrator + test_signal_spine + test_context_builder_aurora_relationship_label + orchestrator/mixins/test_context_builder_mixin | **1019 passed** |
| 2 | tests/core/test_celery_dispatch_async + test_celery_route_beat_hygiene + tests/api/test_chat_legacy_user_context + tests/test_graph_monitor_probes | **26 passed** |
| 3 | tests/unit/test_idiographic_kill_switch + test_belief_fusion_engine + test_t312_l1_response_directive | **28 passed** |
| 4 | tests/api/test_accountability_system_api + tests/services/test_stt_service + test_source_lifecycle + test_policy_patch_service + tests/unit/test_url_guard_trusted_hosts + **tests/unit/test_wt349_attr_defined_defects（新）** | **84 passed** |
| 5 | tests/services/test_cognitive_service + test_cognitive_service_core + test_simulation_runner + test_adaptive_replanner_seed_cohort_filter + tests/unit/test_error_replan_bridge + test_memory_provenance_api + test_achievement_engine_phase3 + test_achievement_engine_regression + test_context_retrieval_pipeline + test_node_sector_backfill_dedup | **128 passed** |
| 6 | tests/agents/graph/nodes/test_deep_analyst + test_error_analyst + orchestrator/mixins（复跑） | **113 passed** |
| 7 | tests/unit/test_state_aggregator_service + test_situation_brief + test_understanding_dimensions_contract + test_openclaw_phase1 | **60 passed + 2 failed（存量，见下）** |

合计 **1458 passed，0 新增失败**。2 个 openclaw 失败（ExecutionService._classify_cache_ttl 缺失、handback 状态断言）在 **main HEAD 干净克隆**（/tmp/wt349-basecheck，git clone 免 stash/reset 纪律）逐字复现同失败集——存量失败，与本批无关。

**红测证明**：test_wt349_attr_defined_defects.py 9 用例在 base 克隆（/tmp/wt349-baseline）上 **5 failed / 4 passed**（planning_intent 脏值崩溃、route_intent 助手缺失、STT ABC 契约、DOC_* 指标缺失、GDPR streak 模型笔误 ImportError），在本 worktree **9 passed**。normalize_sector_weights / policy_patch evidence 2 用例 base 亦绿——对应项在 REPORT 中如实分类为类型面修复（annotation 谎言/类型不兼容）而非运行时缺陷。

## 守卫与 ruff

- `bash scripts/run_all_rule_guards.sh` → **EXIT 0**（83 条全过；gen 三件套已按协议以 `cp -RL` 从主仓复制 backend/app/gen、gateway/gen、mobile/lib/gen，gitignored 不入库）。
- 43 个被碰文件 `ruff check --fix` → **All checks passed**（9 处自动修复均为空白/导入排序类；1 处 F841 死赋值已随 batch_analysis 语义修正消除）。
- `git diff` 中 `type: ignore` 出现次数：**0**。

## 其它

- `/tmp` 自产清理：/tmp/wt349/（base/final/mid 错误清单、守卫日志、touched 列表）与基线克隆 /tmp/wt349-baseline、/tmp/wt349-basecheck 收工自清。
- worktree 内 `backend/app/gen`、`backend/gateway/gen`、`mobile/lib/gen` 为 gitignored 生成物副本。
- 遗留台账：union-attr 23 条（全在回避区）+ attr-defined 余 15 条（dispatch 1 + galaxy/aurora 区 14）待战区解禁。
