# B-02 数据真实性、Mock 污染与指标 Lineage 基线（wt533，V3 LIGHT 审计卡）

- 基线 commit：`3ed32a4f`（分支 wt533-truth）
- 审计日：2026-09-25
- 性质：审计报告，不改产品码。lock：analytics-truth
- 前序：本卡同名 v1 审计产出的修复已入代码（V3-FIX-01/07/08/11/20/143，见各面引用）；本报告是这些修复之后的**当前基线快照**，供后续卡对照回归。

## 总判断

隔离网主体成熟：guest/seed cohort 在全局榜、好友匹配、社区发现、telemetry、北极星五面已有共享词表排除（`EXCLUDED_COHORT_REGISTRATION_SOURCES = ("guest","seed")`）；测试面有 TEST-DBGUARD 会话门 + in-memory sqlite 双保险；mobile 造数全部收敛在 demo 闸后且有真实会话强制关闭。本次审计发现**两个登记级缺口**（均 P3）：①LLM demo 模式产出落库后与真实模型产出在 schema 层不可区分、且 mock 文本喂记忆推断管线（V3-FIX-256）；②guest 转正原位翻转 `registration_source` 不清洗种子数据，伪造 streak/专注分钟/成就随用户进入全部生产 cohort 口径（V3-FIX-257）。

---

## F1 演示/Demo 模式边界

**结论**：demo 激活条件清晰（显式 `DEMO_MODE=true` 或 API key 缺失自动激活），但 demo 产出落库后**无任何持久标记**，与真实模型产出在 schema 层不可区分；`model_name` 落的是「配置了但从未运行的模型名」。P3，登记 V3-FIX-256。

**证据**：

- 激活条件：`backend/app/config/settings.py:1158` `DEMO_MODE: bool = False`（默认关）；key 缺失自动激活 `backend/app/services/llm_service.py:411-413`（router 路径）、`:458-460`（legacy 路径）、`:580`（provider 显式切换后按新 provider key 状态重估，防 demo_mode 被永久带进后续调用）。
- 拦截点：`llm_service.py:724-729`（chat）、`:1068-1073`（generate 系）、`:1235-1249`（stream_chat，含「无 provider」时明示演示文案分支）。
- 产出内容：3 条脚本回复 `DEMO_MOCK_RESPONSES`（`llm_service.py:137-218`，精确+模糊匹配 `:646-655`）+ 无匹配通用回复（`:656-662`，**该条文本自带「当前处于演示模式」声明**）。
- 标记面（缺陷点）：
  - 唯一标记是 OTel span 属性 `llm.demo_mode`（`:726/:1070/:1237/:1248`）——瞬态观测数据，不入库；
  - `ChatMessage` 表无 demo/provider 字段（`backend/app/models/chat.py:25-78`，AI 相关仅 `model_name` :71 / `parse_degraded` :68）；
  - 落库 `model_name=getattr(llm_service, "default_model", None)`（`backend/app/orchestration/persistence_layer.py:91`）→ `default_model` 即配置的 `chat_model`（`llm_service.py:490-493`）——demo 轮记录的是配置模型名，误导 lineage 查询；
  - 三条脚本回复文本**无任何演示声明**，且含捏造学习分析（如「根据你的知识星图和遗忘曲线分析…掌握度降至 65%」，`llm_service.py:186-201`）。
- 联动污染链：`_persist_assistant_message` 落库后把同一 `full_response` 交给记忆推断管线（`persistence_layer.py:103-119` `MemoryInferredWriteLaneService.enqueue_from_chat_turn`）；`backend/app/services/memory_inferred_write_lane.py` 全文无 demo/seed/guest 过滤（grep 证）——**mock 文本喂记忆推断，产出伪事实记忆**。
- 干净面（核实非问题）：
  - demo 短路在 budget/usage 记录之前（`llm_service.py:724-737`），不产生 TokenUsage/计费（billing_worker 只消费 Redis 队列，`backend/app/services/billing_worker.py:94-110`）——token/cost 统计不被 demo 污染；
  - 脚本回复内嵌 ` ```json actions ` 块仅是展示文本：主链路无「chat 文本→动作解析执行」通道（grep 全 orchestration/agents 无 json-fence 动作解析器），不会创建真实任务；
  - V3-FIX-232 已把 provider 截断族收口（`_TRUNCATION_FINISH_REASONS` 集合判定），demo 面之外的「假完成」症状已有账。

**风险分级**：P3。触发条件（无 key 的 dev/演示环境）不罕见，且聊天记录与记忆是长生命周期数据，转正后随行。

**建议处置**（T-demo-response-origin-marker）：`ChatMessage` 增 origin/demo 标记列或 demo 轮 `model_name` 落固定哨兵值（如 `"demo"`/provider 名）；记忆推断 lane 对 demo 轮跳过或打标；脚本回复文本内嵌演示声明（与通用回复对齐）。不改演示交互体验的前提下做。

---

## F2 guest 种子数据污染面

**结论**：种子数据本体按「用户级 `registration_source` cohort 词表」在用户可见聚合面已全面隔离（v1 审计后修复网），但**转正路径不清洗种子数据**，伪造统计随 `registration_source: guest→email` 翻转整体进入生产 cohort。P3，登记 V3-FIX-257。

**证据**：

- 写入面：guest 登录触发（`backend/app/api/v1/auth.py:982-1013`，幂等）；整段包 SAVEPOINT，失败只回滚种子不毒化登录事务（`backend/app/services/guest_seed_service.py:1479-1498`）。
- guest 本体被种入（全部落真实业务表，无 origin 标记列）：`UserStreakStats` current_streak=7/max=30/checkin=45（`:1579-1592`）；6 枚 `UserAchievement`（含已解锁 streak_7/sprint_first/night_owl，`:1557-1572`）；1000 光子（类型 `GUEST_SEED` 已出可兑换基数词表，MINT-FIX，`:1521-1539`）；13 条 `FocusSession`≈540 分钟含 9 天分布（`:2149-2175`）；认知碎片/行为模式/任务（含 `completed_at`）/知识节点掌握度；计划已打 `Plan.source="example"`（V3-FIX-143，`:1873/:1896`）。
- 演示好友：`_ensure_demo_user` 建真实 `User` 行，`registration_source="seed"`（`:235`）、固定密码 `DemoFriend123`（`:228`）；好友学习档案（streak 8/21/38 等）挂在这些 seed 用户上（`:2412+`）。注：本基线（3ed32a4f）中 spec 仍是字面 dict（`:2278/:2346`），wt528 的 `_DemoFriendSpec`/`_FriendLearningProfile` 建模不在本分支，对照后续集成时需重核。
- 公开内容：seed/guest 作者的 `Post`（`visibility="public"`，`:2597-2618`）与公开群（群字段 `total_flame_power/today_checkin_count/total_tasks_completed` 为捏造显示值，`:2620-2686`）。
- 隔离网（已修复面，全部共享同一词表）：
  - 全局榜 V3-FIX-01：`backend/app/services/leaderboard_service.py:62-66`（词表+「B-02 F1 实测曾占 top-100 的 100%」教训）、`:258-259/:648/:717/:787/:865`（五处查询面排除）；
  - 好友匹配 V3-FIX-07：`backend/app/services/friend_match_service.py:748-752`；
  - 社区 feed/评论/群发现 V3-FIX-08/20：`backend/app/api/v1/community.py:294-313/:416/:553-555`、`backend/app/services/community_service.py:461-484`（种子群按 owner cohort 判定）/:557-565/:645；
  - telemetry/决策/北极星：`backend/app/core/telemetry_boundary.py:89-95`（含 truth-path 守卫）、`backend/app/core/north_star_wvpl.py:34-35/:148/:178`（guest/seed 单独计数从不进生产数）、`backend/app/orchestration/adaptive_replanner.py:145`；
  - 自我锚视图只读本人数据且「无数据如实补零不内插」（`backend/app/services/leaderboard_self_anchor_service.py:19-22`）——诚实数据口径已在代码注释成文。
- **缺口（登记点）**：转正 `upgrade_guest`/`upgrade_guest_social` 原位改写同一 `User` 行 `registration_source="email"`（`auth.py:1077` 及 social 对应行），**无任何种子数据清洗**；`backend/app/tasks/guest_cleanup.py:31-37` 自述「游客升级后的数据不会被清理」。转正后该用户进全部生产 cohort 口径（north_star_wvpl 谓词、全局榜、telemetry），其 streak 榜综合分三因子（`total_checkin_days`/`longest_streak`/achievement 计数，`leaderboard_service.py:229-234`）与专注分钟全部来自种子捏造值。V3-FIX-143 的 example 标记只覆盖 Plan/Task/Goals 的**展示层**，`FocusSession`/`UserStreakStats`/`UserAchievement` 无标记字段。

**风险分级**：P3。转正低频但不可逆且跨五个生产指标面；dev 库 guest 占绝对多数（`leaderboard_service.py:716` 实测注「top-20 = 16 guest + 3 seed + 1 email」），转正潮时北极星/榜面语义被伪造活动填充。

**建议处置**（T-guest-upgrade-seed-data-disposition）：二选一——①转正时按种子源清单删除/归档伪造统计（FocusSession/UserStreakStats/UserAchievement/种子社交关系），保留用户真实创建内容；②数据级 origin 标记列 + cohort 谓词从 `registration_source` 扩为「当前来源 OR 历史种子来源」。需产品拍板后立卡。

---

## F3 指标 Lineage

**结论**：主链路（写入源→API）无估算/兜底假值混入；聚合中间层（Redis 缓存、state_aggregator TTL、账本）均有真实数据约束与可观测降级。**「学习/专注分钟数」存在三源并行口径**（观察项，非缺陷），进基线表供后续卡对齐。

**证据**：

- 三源并行（同一「学习分钟」语义、三个写入点）：
  1. `SUM(Task.actual_minutes)`——`backend/app/services/dashboard_service.py:206-210`（dashboard 今日专注）；
  2. `SUM(FocusSession.duration_minutes) WHERE status=COMPLETED`——`backend/app/services/growth_dashboard_service.py:654-658`、`backend/app/analytics/weekly_stats_service.py:96`；
  3. `SUM(StudyRecord.study_minutes)`——`weekly_stats_service.py:84`（galaxy 掌握度事件流，写方 `galaxy/stats_service` + `error_book_mastery_sync_service`）。
  全为真实写入、无 fallback 数值，但口径互不可比：同一用户同日三个「分钟数」可合法地不相等（任务账本 vs 专注计时 vs 掌握度事件）。
- streak：主读 `UserStreakStats.current_streak`（`growth_dashboard_service.py:242-247`），回落 `FocusSession` 逐日推导（`:672-688`，V3-FIX-208/211 修后双列分钟源）——回落链真实数据，无兜底假值。
- 任务完成率/sprint：`sprint_task_ledger` BP-4 单一事实源，`status==COMPLETED` 过滤显式处理「abandon 也写 completed_at」坑（`leaderboard_self_anchor_service.py:14-21` 头注成文）。
- 中间层清点：
  - dashboard Redis 缓存（`dashboard_service.py:76-79/:125`，TTL 内可能滞后，非造假）；
  - state_aggregator 只读 + per-field TTL（`backend/app/state_aggregator/service.py:98-119`），字段构建降级默认值有 Prometheus 计数器（PROD-FIX-1，`:84-92`）；telemetry 渗入已被 V3-FIX-11 双层守卫+cap 封顶（`telemetry_boundary.py`）；
  - mobile 侧 warm cache 为 D-04 版本化缓存，legacy mock 时代条目一次性清除且永不 served（`mobile/lib/core/statistics/data/repositories/hybrid_statistics_repository.dart:135/:342-365`）；
  - 无物化视图（alembic grep 证）。
- 兜底值检查：
  - growth LLM 叙事失败回落 rule-based 文案，数字用真实 `COUNT/SUM`（`growth_dashboard_service.py:754-763`）——无假数；
  - `achievement_event_consumer.py:265` `max(1, duration_ms/60000)`：亚分钟完成计 1 分钟，方向偏高、有界、语义为「至少 1 分钟」（观察项，不动）；
  - `estimated_minutes` 只作缺省回落目标、不反向顶替真实值（`:266`）。

**风险分级**：观察项 P4（三源口径分叉）。无登记项。

**建议处置**：后续若做「学习时长」统一报表，先拍板三源语义归属（建议专注分钟=FocusSession、任务时长=actual_minutes、学习强度=study_records 各归其位，展示层禁混用同名）；现阶段在报告留基线即可。

---

## F4 前端展示真伪（mobile）

**结论**：展示层造数全部收敛在 `DemoDataService.isDemoMode` 闸后，且有「真实 token 强制关闭」与「登出/转正清 pref」双保险；debug 状态注入是渲染闸不是第二数据源。无登记项。

**证据**：

- 造数面收敛：`DemoDataService.isDemoMode` 闸后共 30 文件（repositories/services 全清单 grep，含 `predictive_service.dart:17/:36`、`galaxy_repository.dart:26+:`、`learning_path_repository.dart:24+` 等），demo 数据集中在 `mobile/lib/core/services/demo_data_service.dart`（3517 行，独立文件）。
- 激活路径：编译期 `--dart-define=DEMO_MODE=true` 或 prefs `demo_guest_mode_enabled`（`mobile/lib/main.dart:127-130`）。
- 退出路径：有真实 token 会话时强制 `isDemoMode=false`（`mobile/lib/features/auth/presentation/providers/auth_provider.dart:187-190` 注释「确保从后端读取真实数据」）；登出/升级/会话重置共 8 处 `setBool(key,false)`（`:233/:270/:315/:354/:745/:791/:819` 等）。
- debug 注入面：U-06 `surface_state_injection.dart:25-28` `kReleaseMode` 守门 + 头注明示「不伪造数据、不旁路真实 provider」——release 零生效。
- 占位资源：picsum/placeholder 图 URL 仅存在于 demo service 与 seed 服务（后端），无泄漏到生产渲染路径（grep 证）。

**风险分级**：P4（健康）。无需处置。

---

## F5 测试数据隔离

**结论**：隔离成熟，且是从真实污染事故（「2026-09 泔染事故」）根因封堵的。无登记项。

**证据**：

- backend/tests：in-memory sqlite（`backend/tests/conftest.py:116/:224-225`）；TEST-DBGUARD 会话门——`DATABASE_URL` 指向演示库形状（库名 sparkle）且显式配置时整个进程拒跑 UsageError（`conftest.py:364-381` + `tests/_dbguard.py`）；Redis 走隔离测试 DB + 用后 flushdb（`conftest.py:340-361`）；进程级单例污染治理 autouse fixtures（V3-FIX-120，`:149-219`）。
- tests_e2e：默认 `sparkle_test` 库（`tests_e2e/conftest.py:131-136`）+ 对 `TEST_DATABASE_URL` 与 `settings.DATABASE_URL` 双条件 demo 库门（`:143-159`）。
- 种子脚本：`backend/app/data/*`（achievements/shop/词表）是定义目录（catalog），非用户数据；`ensure_global_galaxy_baseline` 仅种全局共享 `KnowledgeNode` 目录（`is_seed=True, source_type="startup_seed"`，`guest_seed_service.py:129-204`，`main.py:544-549` 调用）——共享 catalog 语义，无 per-user 污染；guest 种子仅由 guest 登录触发，不在测试路径。

**风险分级**：P4（健康）。

---

## 基线快照（关键指标 → 数据源 → 中间层 → 污染风险）

| 指标 | 写入源 | 中间层 | API/展示面 | 污染风险 |
|---|---|---|---|---|
| 专注分钟（growth/weekly） | `FocusSession.duration_minutes`（focus 服务真实计时） | 直查，无聚合任务 | `growth_dashboard_service._sum_focus_minutes` / weekly_stats | guest 种子 13 条≈540min；转正随行（V3-FIX-257） |
| 今日专注分钟（dashboard 卡） | `Task.actual_minutes` | Redis 缓存 TTL | `dashboard_service._get_today_focus_minutes` | 种子任务含 COMPLETED+时长；转正随行；与上行**口径分叉**（观察项） |
| 学习分钟（周报） | `StudyRecord.study_minutes`（galaxy/error_book 掌握度事件） | 直查 | weekly_stats_service | seed cohort 已被用户面排除；guest 转正随行 |
| streak | `UserStreakStats`（+FocusSession 推导回落） | 直查 | growth/leaderboard/self_anchor | guest 种子 7/30/45 纯捏造；转正随行（V3-FIX-257） |
| 任务完成率/sprint | `Task.status/completed_at` | sprint_task_ledger（BP-4 账本） | exam_sprint/self_anchor | 种子任务 COMPLETED；V3-FIX-143 `is_example` 仅展示层标记 |
| 全局榜综合分 | checkin_days×W+achievements×W+streak×W（全是 `UserStreakStats`/`UserAchievement` 字段） | 查询面直算 | leaderboard_service | guest/seed 已排除（FIX-01）；**转正用户带伪造三因子入榜**（V3-FIX-257） |
| token/成本 | LLM usage → Redis 队列 | billing_worker 批量+死信重试 | `token_usage` 表 | demo 短路在 usage 前返回，干净 |
| 北极星 WVPL | 五源事实表 | cohort 谓词 `registration_source NOT IN ('guest','seed')` | north_star_wvpl | 转正用户携种子活动进生产 cohort（V3-FIX-257） |
| 聊天记录/记忆 | `ChatMessage` + MemoryInferredWriteLane | 独立 session 提交 | chat history / 记忆管线 | demo mock 文本落库无标记且喂记忆推断（V3-FIX-256） |
| 学习状态快照 | 只读聚合 | per-field TTL + telemetry 守卫 + cap | state_aggregator | telemetry 渗入已由 V3-FIX-11/14 封；降级默认值有指标 |

## 本次登记

- V3-FIX-256（P3）F1：demo 模式产出落库不可区分 + mock 文本喂记忆推断管线。
- V3-FIX-257（P3）F2：guest 转正不清洗种子数据，伪造统计进生产 cohort。

其余为观察项（三源口径分叉、亚分钟 ceil、群字段捏造显示值等），已达处置门槛前留本报告即可。
