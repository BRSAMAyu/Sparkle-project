# WT677-VERIFY4 — 今日后半波（FIX-343~364 族）round-2 独立复验裁决

- 会话：wt677（承接 wt649 先例，第二轮修复波独立复验）
- 日期：2026-09-25
- 基线：worktree `agent/node-b/wt677/verify4` @ main HEAD `9806d582`（含今日后半波全部集成提交）
- 方法：**逐项独立亲证，不信任 worker 回报**——每张 FIXED 的红→绿测试在当前 HEAD 亲跑；对代表性项做变异实验（删/坏被测代码验红）；撤面/退役/如实化处 grep 死面关键词；行为面按任务书四项抽查。
- 环境注记：worktree 按 ADR 先例 `cp -RL` 主仓 `backend/app/gen`、`backend/gateway/gen`、`mobile/lib/gen`；backend `.venv` 为主仓同款 homebrew python3.11 shim 符号链接；测试统一 `DATABASE_URL='sqlite+aiosqlite:///:memory:' SECRET_KEY=v`。

## 集成形态核验（先决项）

台账 FIXED@sha（531d0f37/bdf583a9/e059cf05/3fec64f6/b4acf2d3/387bddc1/79ad6a90/2dde59a0/85ecb262/c8142703/c632a801/7a914a2c）均为**原始 worktree 分支提交，非 HEAD 祖先**（舰队规范分支不 push）；集成经 rebase 落 main，对应集成提交逐一在 HEAD 历史确证：`e675092e`(343) `b6299617`(344) `66225669`/`301eed3c`/`b303dcbe`/`0cb0b1c2`(345-348) `c575e6a4`(350-352) `4130f984`+`053bc564`(353/354) `936ae4f7`(355) `9770f636`(356) `b92ae2ec`(359)。测试文件与产品码在 HEAD 亲验为准。

## 逐项裁决

| # | 项 | 裁决 | 亲证证据 |
|---|-----|------|----------|
| 1 | FIX-343 L3 三断桥激活 | **PASS** | `tests/unit/test_v343_l3_closure_bridge_activation.py` 修后 **8/8 绿**；变异（`has_semantic_output=False and …` 短路桥触发）→ **2 红**（activation+faults）非恒真。代码亲读：close_session 改走 `calibration_result.to_session_closure()` 进桥（core_session.py:787）、user_id 透传（桥 :84/:92/:104）、`_L3_BRIDGE_TASKS` 强引用+done callback（:71/:798）、宽 except debug→`logger.opt(exception=True).error`（:807）；kill switch `AURORA_FME_L3_CLOSURE_MODE: str = "live"`（settings.py:973）默认即开通，与台账裁决 a 一致 |
| 2 | FIX-344 溢出加固 | **PASS** | `chat_history_inline_error_overflow_regression_test.dart` **2/2 绿**（400x600+260px 槽+scrollUntilVisible 钉重试入口）；回归 `chat_history_sheet_regression_test.dart` **3/3 绿**。平衡变异（SingleChildScrollView→SizedBox 保括号平衡）→ **2 红**；widget 注记 :73-76 与台账方案（放得下逐像素收缩不变）一致 |
| 3 | FIX-345 kill switch 撤面 | **PASS** | `tests/unit/test_v3_fix345_fme_dead_switch_removed.py` **7/7 绿**；守卫 `check_rule_fme_kill_switch_registered.py` exit 0；**变异实验亲做**：完整挂回 `task_card_protocol_v2` 绑定→守卫 **exit 1**（"retired zero-reader feature … re-registered"）fail-closed 成立。grep：`task_card_protocol_v2` 全仓仅存服务 docstring 留档/退役测试/守卫退役名单；`FME_TASK_CARD_PROTOCOL_MODE` settings 声明已撤（:469 留档注记）；`goal_first_minute` 绑定+真实读者（goal_intent.py）保留 |
| 4 | FIX-346 权限死面退役 | **PASS** | `tests/unit/test_v3_fix346_permission_surface_truth.py` **5/5 绿**；permission_service.py 七 enforcement 方法+三装饰器已删（仅 docstring :10 留档），保留面=Permission 枚举+ROLE_PERMISSIONS+get_role_permissions（auth 注册审计消费）；grep `can_mute_user/can_kick_user/require_*` 全仓零调用（agent_grpc_service `_require_admin` 为无关私有同名）；单一实现 `GroupService._can_manage_member`（community_service.py:451）+9 边界测试在场 |
| 5 | FIX-347 审核台撤面 | **PASS** | `tests/api/test_v3_fix347_avatar_moderation_face_removed.py` **3/3 绿**（模块不可 import+/audit 零 avatar 路由+零 PENDING 写入方）；`audit_service.py` 整文件已删；audit.py 仅余 kill-switch-readiness/aurora-effectiveness/pack-quality/admin_actions；**OpenAPI 面**：`docs/contracts/openapi_snapshot.json` 零 `audit/avatars` 路径，本机以 venv 重导出快照与库内**逐字节等价（896 paths 双向差集空）**；`AvatarStatus.PENDING` 全仓仅注释 |
| 6 | FIX-348 fallback 如实化 | **PASS** | `tests/unit/test_v3_fix348_model_fallback_truth.py` **7/7 绿**；grep「切换到更强大的模型」零残留。**行为面亲读**：用户消息分路两支真实在（review_nodes.py:219-222）——reflection 路径 `will_regenerate=True`→「正在尝试自动修正」（:656-661 真有 reflection 紧随），critical 路径缺省 False→「本次回复未通过质量审查」且 `next_step="__end__"`（:675-687）；建议键 `suggested_model`/`fallback_model` 留痕且全仓零读取方、服务 docstring 如实声明「当前无消费方」；死面 `_get_fallback_model`/`get_model_for_task`/死选择策略族已退役（:368 留痕） |
| 7 | FIX-350 enhanced_orchestrator 删轨 | **PASS** | `tests/agents/test_enhanced_orchestrator_retired.py` **3/3 绿**（与 batch1 同批 6/6）；模块文件已删；AGENT_REGISTRY 仅 study_planner/problem_solver（__init__.py:38-41），/multi-agent/agents 面零暴露；grep 全仓仅退役注释。注：注释引「V3-FIX-345」系重编号前旧号→登记 **V3-FIX-366** |
| 8 | FIX-351 streak 冒充字段 | **PASS** | `test_overview_has_no_flame_proxy_streak_days` 绿（batch1 6/6 内）；statistics.py `streak_days` 冒充字段已删（:152 留痕注记）；grep 零 `flame_level` 代理残留。注：留痕注释引「V3-FIX-346」旧号→**V3-FIX-366** |
| 9 | FIX-352 predictive 空承诺键 | **PASS** | `test_engagement_/difficulty_response_has_no_unwired_placeholder_keys` 绿（batch1 内）；`typical_weekdays/typical_hours/prediction_factors/difficulty_factors` 四键 backend/app 全仓零残留；predictive_analytics.py docstring 留痕。注：留痕引「V3-FIX-347」旧号→**V3-FIX-366** |
| 10 | FIX-353 UserDailyMetric 真接线 | **PASS** | `tests/unit/test_analytics_truth_batch2.py` **3/3 绿**，含任务书点名行为：`test_summary_measures_real_tasks_even_when_metric_table_empty`（表空不冒充）+`test_summary_zero_activity_is_true_zero_from_real_tables`（真零）。代码亲读：get_user_profile_summary 改实时聚合 `Task.actual_minutes/COMPLETED`（:222-238）+`CognitiveFragment` 焦虑占比（:240+），不再读零写入 UserDailyMetric；窗口走 V3-FIX-37 用户本地日切（`_recent_activity_window`）；输出格式不变，零值=真实表扫描 |
| 11 | FIX-354 Isar 死集合 | **PASS** | `test/unit/user_analytics_event_retired_test.dart` **2/2 绿**（退役守卫防复活）；`mobile/lib/core/analytics/` 目录已删、`user_analytics_event.dart(.g.dart)` 已删、`local_database.dart` schema/getter 零残留、`uae_815` 全 lib 零命中 |
| 12 | FIX-355 词汇归一 | **PASS** | `tests/services/test_plan_feedback_decision_vocab.py` **39/39 绿**。**行为面亲证+变异**：`_PENDING_DECISIONS=(rejected, needs_modification, requires_confirmation)`（plan_feedback_service.py:289）+读侧归一（:314）；变异回退旧过滤 `("reject","supplement")` → pending 族 **4 红**（rejected 进 pending 语义即红）非恒真；`normalize_plan_feedback_decision` 别名收编在 schemas、判等复活点 :87/:343/:358、gRPC `PROTO_DECISION_TO_REVIEW_DECISION` 单点、workflow.py:328 容错归一——四套词汇（Literal/docstring/gRPC 实写/workflow）收敛链与台账一致 |
| 13 | FIX-356 投影族退役 | **PASS** | 守卫 `TestTaskProjectionKeyFamilyRetired` **PASS**；**变异亲做**：向 `internal/service` 注入 `task:view:*` 字面量样本→守卫 **FAIL**（逐行捕获）后清退；生产 Go 源 `task:view:*`/`user:tasks:*`/`user:task:stats:*` 与 `TaskSyncWorker`/`TaskProjectionHandler` 双投影器零残留（仅 handlers.go 退役注记）；健康端点无 workers.task 项；**go build OK + go test ./... -count=1 全 12+ 包 ok（exit 0）** |
| 14 | FIX-359 insights 删失诚实化 | **PASS** | backend `test_insights_evidence_cards_api.py` **6/6 绿**；service 亲读（evidence_insight_service.py:211-243）：`not_yet_observed` 只含 `n_censored_not_yet_due`，`not_determinable = window_closed+user_churned+unknown` 三桶，uncertainty 双键独立输出。mobile：`notDeterminable` getter（model :93）+`eicUniqNotDeterminable` 独立成行（widget :256-257）+`eicHelpedTierInsufficient`「证据不足，暂不下结论」哨兵（widget :208，arb zh :15690）+default 兜底不再正向断言；mobile evidence_card 双测试文件 **7/7 绿** |
| 15 | FIX-361 置信度族（OPEN 登记准确性） | **PASS（登记准确）** | 8 键逐一在 zh arb 且词形与登记一致（置信度 {percent}%/{value} 等），每键 lib 生产 dart 引用≥1（六面：chat source_explanation/goal intent/chat plan_review/persona/system_updates/memory_detail）；状态 OPEN 如实（未修） |
| 16 | FIX-362 EN 占位债（OPEN 登记准确性） | **PARTIAL（方向成立，计数未逐键复现）** | 问题本体真实：独立复算按登记所述启发式（值=键名 或 Title/Desc/Label/Subtitle/Hint/Message/Failed/Success/Error 结尾式 CamelCase 碎片，活键=lib 引用集）得 **217**；更严变体 18~152——136 落在方法学敏感带内未能逐键复现，不构成失实但计数口径应视为约数。**22 键 en 含 CJK 全为 *Zh deliberate 变体精确复现**（en arb 全量扫=22，无一例外 *Zh 后缀）。状态 OPEN 如实 |
| 17 | FIX-363 Agent 入群披露（OPEN 登记准确性） | **PASS（登记准确）** | community_agent_provider.dart:374-377 亲读：group 预设 buffer 空时 `_fallbackGroupAgentOutput` 本地模板顶替并带 `kAgentMetadataKey:true` sendMessage 入群，metadata 六键无任何「本地模板/离线兜底」披露；ErrorEvent 分支走 error state 不顶替（:365-371）与登记一致；private 预设 :493 落草稿路径在。状态 OPEN 如实 |
| 18 | FIX-360 technicalMessage 直出（任务书所称"364"） | **PASS（登记准确+编号澄清）** | error_messages.dart:116-123 亲读：UNKNOWN/default 分支剥「Exception: 」前缀后直出 `technicalMessage ?? errorServerIssue`，zh UI 可见英文技术原文属实。**编号澄清**：该项在台账登记为 **V3-FIX-360**（wt672 U-10 终审四连登记之一），非 364；台账无 V3-FIX-364 号（363 后直接 360/365，系多批撞号顺延结果），任务书 361~364 的"364"应对应台账 360。状态 OPEN 如实 |

## 发现的问题（新登记）

- **V3-FIX-366（P4，已登记台账，OPEN）**：集成重编号未回写代码注释——wt651 批三文件四处退役/留痕注释仍引撞号前旧号（agents/__init__.py:35 引 345 应为 350；statistics.py:152 引 346 应为 351；predictive_analytics.py:54/:94 引 347 应为 352），现与台账在册语义冲突（345/346/347 已被 wt652 批占用为 fme/permission/avatar 三撤面），按 ID grep 代码会命中错误问题的注释，追溯链污染。已亲证其余 30+ 处代码内 V3-FIX 号引用号义一致无误；纯注释零行为，纯文案卡可收。

## 观察项（不构成登记）

- 主仓工作树 `v3/06_agent_fleet/DYNAMIC_ISSUES.md` 处于 **UU（未解决合并冲突）** 状态；本复验以 HEAD 已提交内容（9806d582）为准，HEAD 版面干净无冲突。请协调面知悉主仓工作树台账未收尾。
- `scripts/check_openapi_contract.py` 内部子进程导出依赖调用环境提供 `SECRET_KEY` 等环境变量（无 env 时 export 子进程 ValidationError）——环境项非产品缺陷；带 env 复跑导出与快照逐字节等价。
- FIX-342 遗留：本波无新增。

## 测试执行汇总（全部本次亲跑）

- backend pytest：v343 8/8；fix345 7/7；fix346 5/5；fix347 3/3；fix348 7/7；enhanced_retired+batch1 6/6；batch2 3/3；vocab 39/39（pending 子集变异 4 红）；insights_evidence_cards 6/6
- gateway go：worker 守卫 PASS+变异 FAIL；`go test ./... -count=1` 全包 ok exit 0；`go build ./...` 净
- mobile flutter：overflow 2/2+变异 2 红；chat_history_sheet 3/3；user_analytics_event_retired 2/2；evidence_card+navigation 7/7
- 变异实验均当场回滚，worktree 提交前 `git status` 干净（仅 gitignored gen/venv 产物）
