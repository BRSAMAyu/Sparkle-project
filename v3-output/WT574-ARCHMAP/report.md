# WT574 · B-06 V3 核心实体映射与重复真源审计（architecture-map，只读）

- 工位：wt574 ｜ 卡：B-06（LIGHT）｜ 基线：`ece77dc3` ｜ 日期：2026-09-25
- 范围：backend（Python Enum）↔ mobile（Dart enum）双面枚举族；goal/task/streak 状态字段真源；时间戳写端纪律。
- 方法：独立全量盘点（backend/app 286 个枚举类 × mobile/lib 295 个 Dart enum）与 `scripts/guards/check_enum_value_set_parity.py` 受管清单（65 族 = dual 44 + passthrough 21，另 24 族已判定 backend-only）求差；对差集逐族提取双面值集并追 wire 通路。**已入管族不计发现。**
- 基线实录：本次运行 `PASS - 65 条结果：FAIL=0 WARN=7 豁免=0`（明细见文末附录，全量 68 行已内联关键行；原始 .log 按仓规不入库）。
- 本仓不修代码；本报告只登记。

## 统计

| 分级 | 定义 | 数量 |
|---|---|---|
| A 真重复真源 | 同一概念多处定义且漂移已发生 | 3 |
| B 漂移风险 | 未入管的双面同名族 / 双算同指标 / 双写同字段（含有损默认） | 7 |
| C 仅记录 | 设计如此但未入 guard / 无法入 guard / 巧合同名 | 4 |

结构性根因（贯穿 A/B）：`inventory_unmapped_backend_enums()`（check_enum_value_set_parity.py:658-671）**只盘点 `backend/app/models/` 下的 StrEnum**。models 外（`app/core/`、`app/services/`、`app/schemas/`、`app/tools/`、`app/agents/`、`app/orchestration/`、`app/aurora/`、`app/task_guidance/`）的枚举族完全不在守卫盘点射程内——B 批绝大多数条目都产自这个盲区。

---

## A · 真重复真源（漂移已发生）

### A1. GroupType 后端三份真源，API 副本缺 `official`（转换点可抛 ValueError）
- 真源：`backend/app/models/community.py` `GroupType` = `{official, sprint, squad}`
- 副本：`backend/app/schemas/community.py:29` `GroupTypeEnum` = `{squad, sprint}`（**缺 official**）
- mobile：`mobile/lib/features/community/data/models/community_model.dart:15` 已补 official（V3-FIX-266 修复面，guard 在管的是 models↔mobile 这一对）
- 消费点（漂移变现处）：`backend/app/api/v1/community.py:1897`、`:1968` `type=GroupTypeEnum(group_dict["type"].value)`——`/groups/search`、`/groups/directory` 结果中出现 official 群组时 `GroupTypeEnum('official')` 抛 ValueError → 500
- 判定：guard 注释（FAMILIES GroupType 条目）早已记录「API 面 schemas GroupTypeEnum 现仅 squad/sprint」，但该副本不在任何守卫射程内；V3-FIX-266 修复只落在 models 与 mobile 两份上，schemas 第三份仍在漂移。**三份真源、修复落了两份。**

### A2. TaskType 后端双词表：models 大写 7 值 vs tools 小写 6 值（缺 OCR），运行时归一遮蔽
- 真源：`backend/app/models/task.py:37-44` `TaskType` = `ERROR_FIX/LEARNING/OCR/PLANNING/REFLECTION/SOCIAL/TRAINING`（值即大写字符串）
- 副本：`backend/app/tools/schemas.py:10-16` `TaskType` = `error_fix/learning/planning/reflection/social/training`（**小写值、缺 OCR**）
- 兜底（漂移被遮蔽的原因）：`backend/app/tools/task_tools.py:78/261/516` 经 `coerce_task_type(params.task_type.value, ...)` 归一（`backend/app/schemas/task.py:177-203` alias+upper+default）；`TaskUpdate._normalize_task_type`（schemas/task.py:290-298）同样依赖 coerce
- 后果：OCR 类型经 LLM 工具参数不可创建（词表差已变形为功能差）；两词表继续各自演化，coerce 是唯一的隐形对账层。guard 的 PlanType 条目注释只声明了 tools/schemas.py 的 PlanType/PlanStage「当前值集一致」，TaskType 实际不一致。

### A3. focus streak 同指标双实现双数据源双时钟（mobile 本地覆盖服务端值）
- 服务端：`backend/app/services/focus_service.py:808-833` `_calculate_current_streak`——服务端 PG `focus_sessions` + **用户档案时区**（`_local_today`，V3-FIX-37），下发于 `:655`（weekly）`:723`（monthly）`streak_days`
- mobile：`mobile/lib/features/focus/data/repositories/focus_statistics_repository.dart:252-286` `_calculateCurrentStreak`——**Isar 本地库** + **设备本地时钟**（`DateTime.now()`），同文件 `_calculateLongestStreak`（:289+）同理
- 覆盖点：`focus_statistics_repository.dart:138-148`、`:193-204`——weekly/monthly 视图不采用服务端 `streak_days`，用本地重算值装配 `'streak_days': currentStreak`
- 消费侧注释自证双算设计：`mobile/lib/core/statistics/presentation/providers/focus_statistics_provider.dart:62-65`「server: `streak_days`, **or derived from heatmap minutes**」
- 判定：漂移已结构性发生——本地库缺已同步/他端 session、设备时区≠用户档案时区时两端数字不同，且 mobile 展示的是本地那份。achievement 域的 StreakDayStatus/连胜日状态是 guard 在管族，不在此列；此处是 focus 统计域的 streak 计数双算。

---

## B · 漂移风险（未入管双面同名 / 双写同字段 / 有损默认）

### B1. ReviewDecision：backend 两套同名异义词表 + mobile 镜像其一
- `backend/app/agents/reviewer_agent.py:67`（StrEnum）= `{passed, needs_refinement, failed}`——LLM 响应审校，且经 `backend/app/agents/graph/nodes/review_nodes.py:521/:584` 以 `"decision"` 键写入 run metadata 下发
- `backend/app/orchestration/plan_review_service.py:60`（Enum）= `{approved, rejected, needs_modification, requires_confirmation}`——计划复审 API
- mobile：`mobile/lib/features/chat/presentation/widgets/plan_review_card.dart:14-19` 镜像后者；`_parseDecision`（:105-117）default → `requiresConfirmation`（有损）
- 风险：同仓同名两词表，reviewer 词表已在 wire metadata 面流转；任一消费面错接词表即静默错分类。guard EP003 只盯「passthrough 族出现同名 Dart enum」，盯不住 backend 内部同名异义。

### B2. InterventionLevel：SCREAMING vs lower、成员集不同，parse 靠 toLowerCase+有损 default
- backend：`backend/app/schemas/intervention.py:13-18` = `{SILENT_MARKER, TOAST, CARD, FULL_SCREEN_MODAL}`；下发于 `backend/app/services/intervention_service.py:649-660/:825-830`
- mobile：`mobile/lib/core/models/intervention.dart:80-99` = `{silent, toast, card, modal}`；`parseInterventionLevel`（:88-99）`toLowerCase()` 归一 + `full_screen_modal→modal` 合并 + default → `silent`（有损）
- 风险：backend 新增 level（如 BANNER）mobile 静默降级为 silent，无人报警；`SILENT_MARKER`→`silent` 是靠 default 而非显式映射。guard 若纳管需先解决大小写形态差（EP 判定按 wire 值严格比对）。

### B3. NextActionType：snake↔camel 全手工 case 映射，双端有损默认
- backend：`backend/app/schemas/task.py:602`（5 值 snake：`continue_plan/light_expand/practice_apply/quick_review/rest_break`）；下发于 `backend/app/services/next_step_service.py:185/248/271/286/305`
- mobile：`mobile/lib/features/task/data/models/next_action.dart:113-117` 标识符为 camel；`_parseType`（:31-45）default → `quickReview`、`_typeToString`（:72-84）手工反查
- 风险：与 B2 同型——单边加值即有损降级；当前 5=5 相等纯靠手工同步，无守卫。

### B4. AppealStatus：双面 5 值当前相等，parse default 有损，未入管
- backend：`backend/app/services/review_history_service.py`（StrEnum）= `{pending, in_review, resolved, rejected, escalated}`
- mobile：`mobile/lib/features/chat/presentation/widgets/review_appeal_card.dart:21-27`，`_parseStatus`（:69-83）default → `pending`
- wire 面：appeal 卡从响应 `json['status']` 直读。值集今天对齐，但在 models 外（services 层），guard 盘点盲区。

### B5. 未入管但当前相等的 wire 族批（任一单边加值即无告警漂移）
双面同名、值集经本次比对**当前相等**、均为真实 wire 面、全部不在 FAMILIES：
| 族 | backend | mobile | 值集 |
|---|---|---|---|
| StepStatus | `app/orchestration/transparency_data_generator.py` | `lib/features/chat/data/models/reasoning_step_model.dart:6` | `{pending,in_progress,completed,failed}`（透明化流） |
| TaskGuidanceAudience | `app/task_guidance/schemas.py` | `lib/features/task/data/repositories/task_repository.dart:44`（wireValue 扩展） | `{human,ai}`（mobile→backend 上行） |
| FeedbackCategory | `app/models/capsule_feedback.py`（Enum，非 StrEnum→**连盘点都不进**） | `lib/features/cognitive/data/models/capsule_feedback_model.dart:7` | 7 值 `{too_long…other}` |
| GenerationType | `app/models/capsule_generation_job.py`（Enum 同上） | `lib/features/cognitive/data/models/capsule_generation_job_model.dart:26` | 4 值 |
| TimeSlotQuality | `app/schemas/smart_schedule.py` | `lib/features/calendar/data/services/smart_schedule_service.dart:65` | `{blocked,low,normal,peak}` |
| RegenerationType | `app/services/feedback_driven_generation.py` | `lib/features/chat/presentation/widgets/regeneration_prompt.dart:11` | 6 值 |
注：FeedbackCategory/GenerationType 是 `enum.Enum`（非 StrEnum），`PY_CLASS_RE` 只认 StrEnum——models 目录内的非 StrEnum 枚举是盘点盲区中的盲区。

### B6. 任务时间戳：mobile 乐观值全量序列化进请求体，当前靠 backend schema「不收」保持单写
- mobile 写点：`mobile/lib/features/task/data/repositories/task_repository.dart:847-848`（createTask 本地 `createdAt/updatedAt = DateTime.now()`）、`:954`（updateTask 同）、`:1362-1364/:1408-1410`（pause/resume demo 路径写 `updatedAt`）
- 序列化面：`mobile/lib/shared/entities/task_model.g.dart:74-88`——`paused_at/started_at/completed_at/created_at/updated_at` 全量进 toJson；createTask/updateTask 直接 `data: task.toJson()`（:860/:964）
- backend 面：`TaskCreate`（`backend/app/schemas/task.py:209-`）/`TaskUpdate`（:263-）**均无时间戳字段** → pydantic 丢弃，服务端唯一权威（`completed_at` 另有 X-04 红线：服务端按真实起止推算，mobile 只传实测分钟——`task_repository.dart:1507-1544` 注释自证）
- 判定：今天无双写；但「客户端时间戳随请求体流动」+「schema 一旦补字段即成双写」的结构在位，属漂移风险而非违规现状。

### B7. AuroraPresenceLevel：snake/camel 形态分裂，wire 面字符串直通绕开 enum
- backend：`backend/app/aurora/schemas/enums.py`（StrEnum）= `{active, ambient, meta_surface}`，进 `backend/app/aurora/schemas/primitives.py:91` `aurora_presence`
- mobile：`mobile/lib/features/chat/presentation/widgets/aurora_indicator.dart:4-8` = `{ambient, active, metaSurface}`（camel，纯 presentation，全仓无其他引用）
- wire 实际通路：`mobile/lib/features/task/presentation/providers/task_chat_provider.dart:109` 以裸字符串直读 `meta['aurora_presence'] ?? 'ambient'`——enum 不在解析路径上
- 风险：形态分裂（snake/camel）使该族即使想入 guard 也先要对齐形态；字符串直通面无 unknown 兜底语义。

---

## C · 仅记录（设计如此但未入 guard / 无法入 guard / 巧合同名）

### C1. Goal.status：注释即真源，mobile 词表镜像注释；无枚举、无流转写点、死时间戳
- 真源形态：`backend/app/models/goal.py:41-45` status 列 **comment** `draft | active | paused | completed | archived | cancelled`——不是 StrEnum，guard 的解析器根本看不见
- mobile 镜像：`mobile/lib/core/display/lexicon/goal_status_lexicon.dart`（文件头自证「值域依据引擎模型列注释」），6 值逐条对齐
- 写点核查：`GoalUpdateRequest`（`backend/app/api/v1/goals.py:69-72`）只有 title/description/target_date，**status 不可经 API 更新**；全仓 grep 无任何 `Goal.status` 赋值 → 除插入 default `active` 外五个状态全部不可达
- 死时间戳：`goal.completed_at/archived_at`（`backend/app/models/goal.py:69-70`）定义+to_dict 下发，但零写者
- 子状态对齐样本：minimum_acceptance_criteria.status 两端手工文本已对齐（backend 校验 `confirmed/pending_confirmation` 于 `backend/app/api/v1/experience/goal_router.py:233-235`；mobile 写同值于 `mobile/lib/features/goal/presentation/providers/goal_detail_provider.dart:170/:185`）——纯手工两端同步，无守卫可挂
- 判定：V3 核心实体中 goal 是状态治理最弱的一环：值集、流转、时间戳三无。若后续 goal 状态机落地（两端各自补 enum），今天这条记录就是未来的 A 级漂移种子。

### C2. 同名不同域（无 wire 关联，巧合同名，建议改名或加归属注释防误接）
| 族 | backend（值集） | mobile（值集） | 备注 |
|---|---|---|---|
| ErrorSeverity | `app/core/error_taxonomy.py` `{critical,degraded,warning}` | `lib/core/design/widgets/error_widget.dart:17` `{error,info,warning}` | 完全不同词表 |
| FailureKind | `app/core/failure_semantics.py`（18 值工具失效语义） | `lib/core/errors/failures.dart:4`（18 值 UI 错误分类） | 同名 18 值互斥词表，最易误接 |
| ToolCategory | `app/tools/base.py` `{focus,growth,knowledge,plan,query,task}` | `lib/features/tools/models/tool_definition.dart:4` `{cognition,efficiency,input,study}` | 服务端注册表 vs 本地 UI 分组 |
| IntentType | `app/schemas/intent.py`（8 值） | `lib/features/home/domain/services/intent_classifier.dart:8`（deprecated 3 值 `{task,capsule,chat}`） | mobile 侧已标 Deprecated |
| CircuitState | `app/orchestration/circuit_breaker.py` `{closed,half_open,open}` | `lib/core/services/retry_strategy.dart:221` `{closed,halfOpen,open}` | 两端各自基础设施，同型不同源 |
| RegenerationStatus | `app/services/feedback_driven_generation.py` `{pending,in_progress,completed,failed}` | `lib/features/chat/presentation/widgets/regeneration_prompt.dart:43`（+`idle`，camel `inProgress`） | mobile 纯本地 UI 态，wire 零命中 |
| RecommendationItemType | `app/schemas/recommendation.py`（内容推荐 5 值）vs `app/schemas/community.py:163` `RecommendationItemTypeEnum`（`{friend,group}`） | `lib/features/community/data/models/community_model.dart:112` 镜像后者 | **backend 内部两名一姓**：内容推荐与社区推荐对象共享族名 |
| AgentRole | `app/agents/base_agent.py`（Enum）+ `app/core/agent_profiles.py`（StrEnum）双定义 | mobile `AgentType`（`reasoning_step_model.dart:21`）为另一概念 | backend 内部同名双定义 |

### C3. RESTORE：TaskStatus 休眠值，backend FSM map 无此键
- `backend/app/models/task.py:50` `RESTORE` 成员；mobile `task_model.dart:29` `@JsonValue('RESTORE')` 镜像（guard 在管、对齐）
- 但 `backend/app/services/task_service.py:49-57` `_VALID_TRANSITIONS` 无 RESTORE 键——`_validate_transition`（:61-68）遇 `current=RESTORE` 抛 `Unknown current status`；mobile 全仓亦无进入 RESTORE 的路径
- 判定：值集在管但语义休眠；状态流转真源本身单一（backend FSM map + `reopen()` X-04 显式特例，后者带快照语义 `task_service.py:1402-1447`，设计如此）。mobile 无本地流转规则副本（全部走专用端点 + 离线队列重放），不构成双真源——这是正面样本。

### C4. MessageOrigin：guard 盘点唯一未判定候选，需一次显式收编
- 本次基线 INFO：`未进映射表的 backend StrEnum … ['MessageOrigin (app/models/chat.py)']`；mobile 无同名镜像
- 判定：属 passthrough（wire 下发字符串）或 backend-only 待判；不构成双面漂移，但 B-06 建议随下次扩表卡显式判定，清空 INFO 候选。

---

## 附：guard 基线（2026-09-25，主线 venv）

命令：`/Users/brsama/code/GitHub/Sparkle-project/backend/.venv/bin/python scripts/guards/check_enum_value_set_parity.py`

摘要行（全量 68 行输出，其中 65 族对账结果 + INFO 分流 2 行 + 摘要 1 行）：

```
[Rule ENUM-PARITY] PASS - 65 条结果：FAIL=0 WARN=7 豁免=0
```
WARN 7 条全部为既有 EP002（mobile 侧 unknown 哨兵/legacy 值）：AchievementType/GroupType/MessageType/PatternType/PhotonTransactionType/StreakDayStatus 的 `['unknown']` + SharedResourceType 的 `['achievement','capsule','file','fragment']`。无 FAIL、无豁免在期。

## 结论（3 条最值得接卡的）

1. **A1 GroupTypeEnum**：官方群组（official）一旦出现在 `/groups/search`、`/groups/directory` 结果即 500——已知漂移的最后一公里（schemas 副本），修法是 schemas 补 official 或转换点改用 models 枚举。
2. **A3 focus streak 双算**：mobile weekly/monthly 用本地 Isar+设备时钟覆盖服务端值，跨端/换机/时区差必然数字打架；收敛方向是删除 mobile 本地重算、直读服务端 `streak_days`（heatmap 仅作图表数据）。
3. **结构性盲区**：guard 盘点只扫 `app/models/` 的 StrEnum；B1-B5、C2 全部产自 models 外。建议扩表卡把盘点半径扩到「被 wire/schema/service 引用的枚举族」或对 `*Enum`-后缀副本（schemas 层 21 份镜像）做一次 backend-internal 单源化（改 import 而非重声明）。
