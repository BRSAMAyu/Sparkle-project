# WT384 · 卡 P-05 REPORT — Proactive Longitudinal Evaluation

- base SHA: `322988ce`（worktree `wt384-p05-eval` 起点，clean）
- final SHA: 见提交（单提交 `feat(eval): wt384 卡 P-05 …`）
- 产物：`v3-output/WT384-P05-EVAL/{summary.json, EVAL_RESULTS.md, raw/{proactive_group,baseline_group}.jsonl, raw/events_timeline.json}`
- 复跑：`backend/.venv/bin/python scripts/devtools/p05_run_proactive_longitudinal_eval.py --help`（`--summarize-only` 可从 raw 复算 summary；summary 全部由 raw 程序化计算，无手填数字）

## 1. 结论（数据在 §3，口径在 §2）

**在声明的 persona 模型与时间线下，主动建议面带来目标恢复而非纯负担**：

- 恢复轴：restart 率 **0.875 vs 0.542**（Δ +0.333），重启中位天数 **2 vs 7 天**，deadline 达成率 **0.417 vs 0.0**（基线组 14 天内无人完成全部账本），期末账本进度 **0.773 vs 0.412**。
- 负担轴：主动组 14 天共投放 112 条建议（人均 4.67，最坏 persona 14 条/14 天），每重启 persona 打扰 5.33 次；accept 45.5%、silent ignore 19.6%、dismiss 26.8%、mute 8.0%。
- 正确性不变量全零（mute 后跨天复发=0、沉默<3 天投放=0、revoke 后 auto 直通=0、accept 次日复发=0）——P-03 抑制与 P-04 授权在纵向时间线里行为正确。
- 反例如实保留并回流 dynamic issue（V3-FIX-48）：**「今天不再看」在每日扫描节奏下只买同日安静**（30 次 dismiss 中 26 次次日仍投放）、**过期窗口每日继续打扰**（4 次实证）。完成谱正控：账本 100% → sprint auto-archive → 主动面源头停（完成后投放=0），此面无负担。

诚实声明：persona 决策（accept/dismiss/mute/silent 概率、疲劳模型、内在自发重启日）是 **seeded 显式模型**（参数全量落 `raw/events_timeline.json`），上述量化是该模型与真实主动面行为的联合结果，不是真人 RCT；效应方向与「主动面行为正确性」不依赖模型参数，效应量级不可外推为真实用户指标。

## 2. 时间线设计与口径（headless）

### 2.1 可控时钟（不等待真实时间）

模拟日 d（0..13）+ 当日钟点（AM 生成 09:00=`frac 0.375`，PM 探针 15:00=`0.625`）经 **backdate 换算**写为真实时间戳（与 `tests/aurora/test_comeback_context.py`、`dbfixture.backdate_proposal_expiry` 同口径）：活动痕迹（Task.completed_at）、计划窗口（Plan.target_date）、任务到期（Task.due_date）、建议投递时间（Notification.created_at）、cooldown 窗口尾（UserPreferencesCenter.explicit 的 ignored_until）每 tick 重写。真实服务内部的 `datetime.now` 由此感知为模拟时刻；24h 窗口边界语义与真实语义一致（≥24h 过界恢复，同 `+1s` 单测口径）。

### 2.2 驱动面（真源不重建，无语义 mock）

- 生成/抑制/投递：**直调生产 celery 任务 `comeback_nudge_task`**（真实 get_comeback_context → suppression → duplicate 窗口 → NotificationService.create 全链；仅 `AsyncSessionLocal` 重定向到本世界 sqlite 引擎——基建绑定）。
- 行动：**真实 `ActionCommandService`** 统一 command path（IN_PROGRESS 低风险可逆 / COMPLETED 中风险不可逆恒 proposal+确认——P-04 风险门在授权之上）。
- 反馈：**真实 `ProactiveSuggestionFeedbackService`**（record_ignore_today / record_mute）。
- 授权：**真实 `ActionPermissionService` + UserSettings.low_risk_auto_execute**（grant/revoke 仪式随时间线事件发生）。
- 每条建议记录全量指标：accept/dismiss/mute/silent、行动步骤与执行模式（auto/confirmation+reason codes）、outcome（账本推进/deadline 达成）；每组逐日记录 days_away/days_remaining/stalled/plan_expired/账本状态。

### 2.3 persona 与事件谱（每组 24 = 3 谱 × 8，同 seed 双组共享）

| 谱 | 账本（总量/事前完成） | 计划截止（模拟日） | 考察点 |
|---|---|---|---|
| stalled ×8 | 8/2 | 16（线外） | 经典停滞召回：建议能否拉回活跃 |
| deadline ×8 | 6/2 | 9..11（线内收口） | 截止前恢复达成 / 过期后诚实与打扰 |
| completion ×8 | 4/1 | 16 | 高接受度快速完成 → 完成后主动面行为 |

- 开局：活动痕迹止于模拟日 -4（第 0 天起 days_away≥3 满足 comeback 阈值）。
- 内在行为：每 persona seeded 自发重启日（两组完全一致；基线组唯一行为源）。
- 决策模型：p_accept = receptivity − 0.12×连续无行动建议（下限 0.05）；未接受时按 mute 倾向（疲劳加压）→ dismiss（55%）→ silent 落桶；receptivity~U(0.35,0.85)、mute_propensity~U(0,0.25)。
- P-04 轴：一半 stalled/deadline persona 首次 accept 时走 grant 仪式；1/4 persona 挂「被打扰到关停」谱（累计 3-4 次无行动建议 → revoke + mute）。
- 基线组：同时间线、同 persona、同内在行为，**主动面关闭**（不生成任何建议）。

## 3. 两组对照关键数字（summary.json 程序化复算）

| 指标 | proactive | baseline | Δ |
|---|---|---|---|
| restart 率（停滞→出现真实任务完成） | **0.875**（21/24） | 0.5417（13/24） | +0.333 |
| 重启中位天数 | 2 | 7 | −5 |
| deadline 达成率（账本全完成且 ≤ 截止） | **0.4167**（10/24） | 0.0（0/24） | +0.417 |
| 期末账本进度均值 | 0.773 | 0.412 | +0.361 |
| 建议投放量（人均/最坏） | 112（4.67 / 14） | 0 | — |
| 每重启 persona 打扰次数 | 5.33 | 0 | — |
| disposition（accept/silent/dismiss/mute） | 51/22/30/9 | — | — |
| 生成跳过分布 | not_eligible 165；suppressed:cooldown 30；suppressed:muted 59 | — | — |

机制读法：恢复增益来自「建议→accept→真实任务完成→活动痕迹重置→后续 not_eligible」的真实闭环（165 次 not_eligible 中大量为重启后不再打扰）；负担侧 mute/dismiss 后由真源抑制（59+30 次），非渲染遮蔽。

## 4. 时序交互断言清单（pytest 契约锁，`tests/unit/test_p05_proactive_longitudinal_temporal.py`，5/5 绿）

1. **mute 跨天不复发**：mute 次日起连续 4 天生成全部 `suggestion_suppressed{muted}`，DB 通知数止于 mute 时刻（真实任务路径）。
2. **cooldown 边界**：dismiss 同日 PM 探针 30/30 被 `cooldown` 真源抑制（P-03 检查先于重复窗口）；满 24h 后次 AM 恢复投放（`>=24h` 过界语义）——同时如实钉住「每日节奏下 dismiss 只买同日安静」的负担事实。
3. **auto 授权纵向演变**：grant 后低风险可逆步骤 `auto` 直通（receipt 面经 P-04 既有测试覆盖）；COMPLETED 恒 `confirmation`（授权不压风险门）；revoke 后同类操作回 proposal（`auto_forbidden_category_not_allowlisted`）且确认权仍在；两次行动真实落账（4 proposal COMMITTED、4 任务 COMPLETED）。
4. **基线组零投放**：同时间线主动面关闭 → 零生成/零通知、内在行为照常。
5. **completion 谱正控**：账本 100% → sprint auto-archive（Plan.is_active=False，ExamSprintReviewService.auto_archive_if_complete）→ 后续 4 天生成全部 `not_eligible`——「完成后打扰」在 sprint 谱不存在（反例排查结论，0 完成后投放）。

引擎内全量运行的同款不变量（366 次生成、112 条建议上复算）：`post_mute_deliveries=0`、`sub_threshold_deliveries=0`、`post_auto_revoke_auto_steps=0`、`next_day_redeliveries_after_accept=0`、`post_ledger_complete_deliveries=0`——脚本 exit 0 即这些为红条件。

## 5. 反例与 dynamic issues（保留不剪 → V3-FIX-48）

1. **dismiss 杠杆在每日扫描节奏下失效**：30 次 dismiss 中 26 次次日仍收到建议。机制：24h cooldown 与 24h 重复窗口在两次日 tick 之间双双过期；同日 PM 探针 30/30 被抑制（同日语义正确）。用户第一个直觉杠杆「今天不再看」实际不减少次日频率，最坏 persona（deadline_03）14 天 14 条、dismiss 多次后仍每日一条，直到 decision-mute。→ 产品权衡：dismiss 退避/跨日冷却/扫描降频（OPEN，T-proactive-burden-balance）。
2. **过期窗口继续每日打扰**：deadline 谱 2 persona 在窗口过期后（day12-13）仍各收 2 条建议（A-07 stale 诚实文案生效、无 guilt，但打扰未停）；窗口过期不触发 auto-archive（仅全完成触发）。→ 是否衰减/停投需产品裁决（OPEN）。
3. **正控（非负担）**：完成后投放=0（auto-archive 停源头），完成后骚扰假设被真实代码证伪——如实记录为正控证据。

## 6. 质量门与证据

- pytest（sqlite 内存口径）：本卡新测 **5/5 绿**；邻域 P-03/P-04/X-03/comeback/notification 回归与守卫见 §7 命令与结果；存量败对照 base 定性（`.env` 依赖集成 ERROR 与既有失败与本卡零交集）。
- 脚本可复跑：`--seed/--per-arc/--days/--groups/--out-dir/--summarize-only`，`--help` 完整；raw JSONL 为权威，summary/EVAL_RESULTS 由 `--summarize-only` 从 raw 复算可重现。
- 反例链证据：`raw/proactive_group.jsonl` 逐条建议含 why_now/suggested_action/disposition/行动模式——反例可直接引用到条目级。

## 7. 改动文件清单

- `backend/tests/proactive_longitudinal/__init__.py`（新增：纵向评估引擎包）
- `backend/tests/proactive_longitudinal/persona.py`（新增：persona 时间线规格 + seeded 决策模型）
- `backend/tests/proactive_longitudinal/engine.py`（新增：SimClock 可控时钟 + PersonaWorld 真实服务驱动 + 逐日循环）
- `backend/tests/proactive_longitudinal/metrics.py`（新增：raw → summary 程序化计算 + Markdown 渲染）
- `backend/tests/unit/test_p05_proactive_longitudinal_temporal.py`（新增：5 条时序交互契约锁）
- `scripts/devtools/p05_run_proactive_longitudinal_eval.py`(新增：无人值守 runner，--help 可复跑)
- `v3-output/WT384-P05-EVAL/`（raw + summary.json + EVAL_RESULTS.md + 本 REPORT）
- `v3/06_agent_fleet/DYNAMIC_ISSUES.md`（V3-FIX-48 登记）

## 8. DEFERRED

- baseline 组「打扰成本」天然为 0（无主动面），burden 两轴中「每重启打扰次数」只在主动组有非平凡值——组间 burden 对照的公平口径需真人实验设计，本卡如实只报主动组负担绝对值。
- 决策模型参数（receptivity/fatigue 等）未做敏感性扫描（不同参数下效应量级会变，方向不因 P-03/P-04 正确性断言而变）；如需参数扫描，脚本 `--seed/--per-arc` 已支持批量复跑。
- 过期窗口谱仅 2 persona 在线内过期后存活至 day12+（其余已 mute/重启），反例②样本量 4 条投放——量级存疑、机制确凿（代码路径：过期不触发 archive）。
- 非 sprint 计划类型（无 auto-archive）的完成后行为未评估（本卡事件谱按 SPRINT 真源口径构造）。
- worktree 环境项（按 wt369/J-05 先例自主仓补齐、不入库）：`backend/app/gen/`（proto 生成物）从主仓同步。
