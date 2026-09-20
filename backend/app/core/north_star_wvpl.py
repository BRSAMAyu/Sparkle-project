"""D-06 · WVPL 北极星查询契约 —— 口径冻结与事实 JSON schema（METRIC_TREE North Star）。

定位（DATA stream, locks: analytics-truth 继承 D-04）：
- **本模块是查询层，不建真源**：真源是 D-01 事件契约 / D-02 outcome ledger 五源读
  模型 / D-03 五维内部度量 / D-04 真实统计接线。本卡只做**确定性聚合查询**，把
  METRIC_TREE 的 North Star（Weekly Valuable Progress Loops）变成可审计的事实
  JSON。**不让模型计算数字**：模型（LLM）只在消费端解释事实 JSON，零计算参与
  （代码级证明见 tests，模块不 import 任何 LLM 基础设施）。

WVPL 口径 v1（``WVPL_CALIBER_VERSION = "wvpl.caliber.v1"``，冻结；变更需 bump
版本并过 reviewer，历史事实 JSON 因版本字段可追溯口径）：

- **窗口**：``[as_of - WINDOW_DAYS, as_of)`` 半开区间，naive UTC（仓库规范）。
  as_of 是**幂等锚点**：同一 as_of + 同一库态 → 逐字节相同的事实 JSON。
- **Valuable Progress Loop（一个 loop，v1 三腿全确定性）**：
  1. *goal-linked action*：tasks 行 status=COMPLETED 且未删除，occurred_at
     （coalesce(completed_at, created_at)，与 D-02 账本同口径）落在窗口内，
     且 task.plan_id → plans.goal_id IS NOT NULL（经 Plan 绑定到 Goal；
     plans.goal_id 为 NULL 的计划上的完成**不是** goal-linked）；
  2. *outcome/evidence*：该完成在 D-02 outcome ledger 下分级为
     ``TruthClass.ACTUAL``（可验证证据已解析 / quiz 物化 / focus 覆盖达标）——
     即 D-02 契约预留的「North Star WVPL 用 actual 面，不用完成点击面」；
  3. *state update*：至少一行 study_records（task_id = 该 task，未删除）——
     完成管线 spark_node → 星图状态链（GJ03：task→study_record→mastery）的
     服务端吸收痕迹。spark_node 是 best-effort（try/except），**行的存在**才是
     事实，代码路径存在不是事实。
- **去重**：loop 身份 = D-02 outcome 身份 ``(task_completion, task.id)``——
  重复 event、多条回声 study_record、重复查询都不产生第二个 loop。
- **Active user（分母，必须保留——METRIC_TREE「避免只报绝对数」）**：窗口内
  ≥1 个 engagement 信号的用户，信号 = user 角色聊天消息（未删除）∪
  context_pack_runs 行 ∪ 五源 ledger outcome 行（standalone 谓词）。是 D-03
  ``compute_daily_all`` active 定义（pack/chat）的超集：补上 outcome 面，
  纯 focus 学习（无聊天）用户也进分母。
- **cohort 分离（卡面 work 2）**：生产 cohort = ``users.registration_source
  NOT IN ('guest','seed')``（复用 D-02 ``EXCLUDED_COHORT_REGISTRATION_SOURCES``，
  不复制词表）；seed/guest 用户单列 demo face，绝不混入生产分母/分子。
- **mode/proactive 面（卡面 work 1）**：v1 取 D-05 intervention lifecycle——
  六段事件类型计数（封闭词表）+ started 事件按 execution_mode
  （human|agent|hybrid）分桶；behavioral_outcomes 按 outcome_type 分桶。
  这是「主动干预」与「执行模式」的确定性事实面。
- **有界扫描**：单次 run 用户数与每用户 ledger 翻页数有硬顶（``caps``），
  触顶时事实 JSON 如实置 ``truncated=true``（可审计的诚实截断，不静默）。

事实 JSON schema：``WVPL_FACT_SCHEMA = "north_star.wvpl.fact.v1"``（冻结）。
每个数字的可审计性三件套：**口径**（``FACT_DEFINITIONS``）+ **源查询**
（definitions 内表/谓词描述 + provenance.source_queries）+ **事件溯源**
（loops.sample_event_ids 携带 outcome_id/task/plan/goal ref，可回查 D-02
``derive_outcome_id`` 幂等 id）。

变更流程：口径、schema、caps 属冻结契约，改动需 bump 对应版本并过 reviewer
（C-01/D-01/D-02/X-01 同款纪律）。
"""

from __future__ import annotations

WVPL_FACT_SCHEMA = "north_star.wvpl.fact.v1"
WVPL_CALIBER_VERSION = "wvpl.caliber.v1"

#: 北极星窗口：7 日（METRIC_TREE「7 日窗口」），半开 [start, end)。
WINDOW_DAYS = 7

#: goal recovery after stall 的停滞阈值（METRIC_TREE outcome metrics；
#: 连续两个 loop 间隔 ≥ 此天数记一次 stall，下一 loop 关闭 stall）。
GOAL_STALL_THRESHOLD_DAYS = 14

#: 有界扫描 caps（触发即 truncated=true，诚实披露；v1 面向 staging/周批）。
MAX_ACTIVE_USERS_PER_RUN = 1000
MAX_LEDGER_PAGES_PER_USER = 5  # 每用户全史 walk 页数上限（D-02 页大小 200）
MAX_LOOP_SAMPLES = 50  # 事实 JSON 内嵌的可回查 loop 样本上限

#: 分母 engagement 信号的口径标签（事实 JSON definitions 引用）。
ACTIVE_SIGNAL_CHAT = "user_chat_message"
ACTIVE_SIGNAL_CONTEXT_PACK = "context_pack_run"
ACTIVE_SIGNAL_LEDGER_OUTCOME = "ledger_outcome_any_source"

_LOOP_DEFINITION = (
    "loop = goal-linked action (tasks.status=COMPLETED, not deleted, "
    "occurred_at=coalesce(completed_at,created_at) in [start,end), "
    "task.plan_id -> plans.goal_id IS NOT NULL) "
    "+ outcome/evidence (D-02 outcome ledger classifies the completion as "
    "TruthClass.ACTUAL at query time) "
    "+ state update (>=1 study_records row with task_id=task.id, not deleted). "
    "Loop identity = outcome ledger identity (task_completion, task.id); "
    "duplicate events and echo study_records never double-count."
)

#: 事实 JSON 的冻结口径注释（随事实 JSON 输出，machine-readable 的「每个数字
#: 怎么来的」；文本与 core 模块 docstring 同源，改动需 bump caliber version）。
FACT_DEFINITIONS: dict[str, str] = {
    "window": (
        f"half-open [{{start}}, {{end}}) naive UTC, WINDOW_DAYS={WINDOW_DAYS}; "
        "as_of is the idempotency anchor: same as_of + same DB state -> byte-identical fact JSON"
    ),
    "loop": _LOOP_DEFINITION,
    "north_star.active_users": (
        "distinct users with >=1 engagement signal in window: "
        f"{ACTIVE_SIGNAL_CHAT} (chat_messages.role=user, not deleted) UNION "
        f"{ACTIVE_SIGNAL_CONTEXT_PACK} (context_pack_runs row) UNION "
        f"{ACTIVE_SIGNAL_LEDGER_OUTCOME} (any of the five D-02 outcome sources, "
        "standalone predicates), all within the production cohort"
    ),
    "north_star.wvpl_users": "distinct users with >=1 loop in window",
    "north_star.wvpl_ratio": "wvpl_users / active_users; None when denominator is 0 (no fabricated ratio)",
    "north_star.loops_total": "count of loops in window (deduplicated by task id)",
    "north_star.loops_per_wvpl_user": "loops_total / wvpl_users; None when wvpl_users is 0",
    "outcomes.by_source": (
        "window counts per D-02 OutcomeSource (task_completion/study_record/"
        "focus_session/quiz_feedback/behavioral), standalone predicates, "
        "de-duplicated by the ledger's same-cause merge (completion echo "
        "study_records attach to task_completion, never counted twice)"
    ),
    "outcomes.truth_coverage": (
        "distribution of TruthClass over window task completions (fleet-wide "
        "aggregation of the D-02 read model; actual_ratio=None when total=0)"
    ),
    "outcomes.action_outcome_conversion": (
        "among window goal-linked completions (leg-1 predicate, all truth "
        "classes): actual / total; None when total=0. Measures action->outcome "
        "conversion on the goal-linked face (METRIC_TREE outcome metrics)"
    ),
    "outcomes.behavioral_by_outcome_type": ("window behavioral_outcomes grouped by outcome_type: {total, success}"),
    "proactive.lifecycle_events_by_type": (
        "window intervention_lifecycle_events grouped by event_type (six-value "
        "frozen LifecycleEventType vocabulary; D-05)"
    ),
    "proactive.started_by_execution_mode": (
        "window intervention_lifecycle_events with event_type='started' grouped "
        "by execution_mode (human|agent|hybrid; other values land in 'other')"
    ),
    "outcome_metrics.time_to_first_meaningful_value": (
        "for production-cohort users active in window whose FIRST-EVER loop "
        "falls in window: days from users.created_at to first loop; median over "
        "that cohort. Bounded by caps (truncated flag when bound)"
    ),
    "outcome_metrics.goal_recovery_after_stall": (
        f"per goal (plans.goal_id) over a user's bounded loop history: consecutive "
        f"loop gap >= {GOAL_STALL_THRESHOLD_DAYS} days is a stall; the next loop "
        "closes it. Reports recoveries whose closing loop falls in window and the "
        "median recovery days"
    ),
}

#: provenance.source_queries：事实 JSON 内嵌的源查询登记（表 + 口径谓词摘要）。
SOURCE_QUERIES: tuple[dict[str, str], ...] = (
    {
        "name": "active_users",
        "tables": "chat_messages, context_pack_runs, tasks, study_records, focus_sessions, expansion_feedback, behavioral_outcomes, users",
        "predicate": "window [start,end) per source; five sources use D-02 standalone predicates; registration_source NOT IN ('guest','seed')",
    },
    {
        "name": "loops",
        "tables": "tasks, plans, study_records (+ D-02 OutcomeLedgerService.query truth_class=actual)",
        "predicate": _LOOP_DEFINITION,
    },
    {
        "name": "goal_plan_map",
        "tables": "plans",
        "predicate": "goal_id IS NOT NULL",
    },
    {
        "name": "state_update_leg",
        "tables": "study_records",
        "predicate": "task_id IN (loop candidates) AND deleted_at IS NULL",
    },
    {
        "name": "behavioral_by_outcome_type",
        "tables": "behavioral_outcomes",
        "predicate": "window [start,end), production cohort",
    },
    {
        "name": "intervention_lifecycle",
        "tables": "intervention_lifecycle_events",
        "predicate": "window [start,end) on occurred_at, production cohort",
    },
    {
        "name": "seed_cohort_face",
        "tables": "users + five outcome sources",
        "predicate": "registration_source IN ('guest','seed') — counted separately, never in production numbers",
    },
)

__all__ = [
    "ACTIVE_SIGNAL_CHAT",
    "ACTIVE_SIGNAL_CONTEXT_PACK",
    "ACTIVE_SIGNAL_LEDGER_OUTCOME",
    "FACT_DEFINITIONS",
    "GOAL_STALL_THRESHOLD_DAYS",
    "MAX_ACTIVE_USERS_PER_RUN",
    "MAX_LEDGER_PAGES_PER_USER",
    "MAX_LOOP_SAMPLES",
    "SOURCE_QUERIES",
    "WINDOW_DAYS",
    "WVPL_CALIBER_VERSION",
    "WVPL_FACT_SCHEMA",
]
