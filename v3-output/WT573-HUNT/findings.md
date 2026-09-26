# WT573 猎缺报告 — 数据正确性轴（第一轮）

工位 wt573 ｜ 基线 9c4b2904 ｜ 2026-09-25 ｜ 只读猎缺，未改任何产品代码。
台账对齐：已 grep `DYNAMIC_ISSUES.md` 全部 V3-FIX- 行 + `KNOWN_CODE_DEBT_LEDGER.md`，以下均不在案（V3-FIX-287/FIX-286/wt559 六测/wt567 五轴/V3-FIX-01/07/37 等已知项均避开）。
共 6 条：P2 × 3，P3 × 3。F1 的数值差已经用仓内纯函数模块实跑验证（非手算）。

---

## F1 (P2) 掌握度证据账本重放的基准值用了「已含全部历史」的现值 —— 每次吸收都把整段历史再融合一遍，掌握度加速收敛到观测值、跨过 mastered 阈值

**定位**
- 病灶：`backend/app/services/galaxy/stats_service.py:578` —— `belief = recompute_evidence_state(current_mastery, history)`，`current_mastery` 是**当前存储掌握度**（对已有账本的节点，它本身就是历史证据融合的结果），而 `recompute_evidence_state` 的契约是「从 legacy 先验（max uncertainty）出发按时间序重放证据」（`backend/app/services/galaxy/mastery_evidence.py:286-297` docstring：*"Starts from the legacy value at max uncertainty"*）。
- 触达路径 1：`backend/app/services/galaxy/stats_service.py:130`（spark_node 传 `old_mastery`）→ `:134-135` 融合新证据 → `:144` 写回 `status.mastery_score` → `:189-204` 把新观测追加进账本。
- 触达路径 2：`backend/app/services/galaxy/outcome_absorption_service.py:199`（`_load_prior_belief(..., float(status.mastery_score))`）→ `:206-208` 融合 → `status.mastery_score = fused.mean` → `:230-254` 追加审计行。

**失败场景（输入序列 → 错误结果）**
同一节点连续两次携带同类证据的完成事件（如 quiz value=80, confidence=0.9；首事件前 legacy=20）：

| 事件 | 实际代码存储值 | 正确单遍语义存储值 |
|---|---|---|
| 1 | 77.692 | 77.692（一致） |
| 2 | **79.956** | **78.846**（差 +1.11） |
| 3 | **80.000（钉死）** | 79.856 仍未到 80 |

即从第 2 个证据事件起，历史每一行都被**再融合一遍**：第 k 条观测在第 N 个事件时的有效被计入次数是 N−k+1，后验均值加速钉向观测值。后果：
- `calculate_user_stats` 的 `mastery_score >= 80` mastered 计数（`stats_service.py:373`）提前/虚高跨阈值；
- 后验方差每轮被重置到 0.25 再坍缩，信念系统性过信，衰减（DecayService/重放 gap 衰减）对它的拉回被削弱；
- 对低置信通道（chat_signal/material_ref）同样复合，只是幅度小。outcome_absorption 是「真实结果回灌」主线（G-01），任何节点累计 ≥2 条 outcome/quiz 证据即进入该形态。

**旁证（作者知道这个坑但只堵了一半）**：`stats_service.py:561-565` 对 quiz-grade 无 payload 行显式注释 *"their effect is already baked into the stored mastery, so they count as evidence presence but are not re-fused"* —— 同样的 baked-in 逻辑对带 payload 的 `evidence:` 行完全成立，但它们被原样重放。

**可证伪测试草图**
纯函数级、零 DB、确定性（F1 数值即此脚本实跑产出）：
```python
from app.services.galaxy.mastery_evidence import *
t0 = datetime(2026, 9, 20)
row1 = EvidenceHistoryEntry(MasteryEvidenceType.QUIZ, 80.0, 0.9, t0)
obs  = EvidenceObservation(MasteryEvidenceType.QUIZ, 80.0, 0.9)
stored1 = fuse_mastery(*recompute_evidence_state(20.0, []), [obs]).mean        # 77.692，事件1正确值
# 适配器第 2 事件的先验 = 用「存储值」当重放基准（现状）：
prior_actual   = recompute_evidence_state(stored1, [row1])
new_mastery    = fuse_mastery(prior_actual.mean, prior_actual.variance, [obs]).mean
# 期望：历史对同一 legacy 只施加一遍：
prior_intended = recompute_evidence_state(20.0, [row1])
expected       = fuse_mastery(prior_intended.mean, prior_intended.variance, [obs]).mean
assert abs(new_mastery - expected) < 0.2   # 现状 79.956 vs 78.846，红
```
DB 级变体：种 `user_node_status.mastery_score=0` + 两条 `mastery_audit_log` evidence 行，调 `spark_node(outcome=...)`，断言存储值 ≈ `recompute_evidence_state(0, rows).mean` —— 现状必红。
（方向备注：修法是给先验保留「证据前 legacy 基准」——首条 evidence 审计行的 `old_mastery` 即是该值，`_load_prior_belief` 应以它而非现值为重放基准；此处只报缺陷不绑实现。）

---

## F2 (P2) 打卡连胜引擎的 day 边界是 UTC 日，且把调用方显式传入的用户本地日 `activity_date` 丢弃 —— UTC+8 用户会在「没缺勤的本地日」被烧冻结卡/断签，也能「整缺一个本地日」白嫖续签

**定位**
- 病灶：`backend/app/services/achievement_engine.py:2034` —— `today = _utcnow().date()`；`:2065` `delta = (today - last_activity_date).days` 决定续签/断签/冻结分支。`_update_streak_stats` 的 `**kwargs` 全程不读 `activity_date`。
- 调用方给了本地日却没用：`backend/app/api/v1/accountability.py:1392-1393` 用 `_day_range_for_timezone(_user_timezone(current_user))` 算出用户本地「今日」并做打卡去重，`:1448` 显式传 `activity_date=today_start.date()` —— 被引擎丢弃。
- 触达面：全部四类核心活动事件（`achievement_engine.py:2040-2046` 白名单：DAILY_CHECKIN / DAILY_STUDY / TASK_COMPLETED / NODE_MASTERED）源头为 `accountability.py:1445`、`api/v1/tasks.py:1479`、`achievement_event_consumer.py:104/204/272/303`、`galaxy_service.py:3562`。
- 与已裁决契约相悖：V3-FIX-37 已把 statistics/focus 面改用户本地日，wt559/V3-FIX-281 已把 plans/tasks 六测对齐「用户本地日（缺省 Asia/Shanghai）」契约；`UserStreakStats` 连胜引擎是同族漏网，且台账无此行（V3-FIX-59 是移动端文案窗，非此）。

**失败场景（UTC+8，上海）**
- 场景 A（**误烧冻结卡/误断签**）：用户周日 00:30 本地打卡（= 周六 16:30 UTC），周一 23:40 本地打卡（= 周二 15:40 UTC）。本地日连续，UTC 日差 = 2 → `delta=2, days_missed=1` → 走冻结分支烧 1 张冻结卡（无卡则 `current_streak=1` 断签），并把 UTC 周一写成一行 `FROZEN` 的 `user_streak_days`。用户一个本地日都没缺。
- 场景 B（**整缺一天白嫖续签**）：周一 23:50 本地打卡（= 周一 15:50 UTC），周二本地全天不活动，周三 06:00 本地打卡（= 周二 22:00 UTC）→ UTC delta=1 → 连胜 +1、无 MISSED 行。用户可长期隔日打卡仍保「连续」。
- 两个方向的根因同源：连胜「天」的钟表（UTC）≠ 用户日，且与同接口的去重钟表（用户本地日）互相矛盾——「今天已打过卡」按本地日判，连胜按 UTC 日记。

**波及（持久化 + 消费方）**
- `user_streak_days.day` 落的是 UTC 日（`achievement_engine.py:2056-2134`），移动端连胜日历按本地日渲染时格子错位；
- `growth_dashboard_service.py:242-247` `_get_streak_stats_days` 优先读该 UTC 值，fallback 才是 V3-FIX-211 修过的本地日计算器 `_get_current_streak_days`（`:672-712`）——同一面板双钟表；
- `experience_readouts.py:523-557` 直接向用户展示「当前连续 N 天」并按 `0.20 × current_streak/7` 计入复合分；
- 全局榜复合分权重项 `total_checkin_days`/`longest_streak`（`leaderboard_service.py:232-234`）。

**可证伪测试草图**
冻结钟 + 显式钉时区（沿 `test_task_snooze_due_date_local_day.py` 双冻结钟族判例）：
```python
# 冻结 utcnow = 2026-09-28T15:40:00Z（上海 09-28 23:40）；种 last_activity_date = 2026-09-26T16:30:00（= 上海周日 00:30 打卡）
engine = AchievementEngine(db)
await engine._update_streak_stats(user_id, AchievementEvent.DAILY_CHECKIN)
# 本地日序：周日(00:30)→周一(23:40) 连续；UTC 日序：09-26→09-28 差 2
assert stats.current_streak == 2 and stats.freeze_charges == charges_before  # 现状：走冻结分支，charges-1 且 current_streak 被重置路径波及，红
assert not (await db.execute(select(UserStreakDay).where(UserStreakDay.day == date(2026, 9, 27), UserStreakDay.status == FROZEN))).scalar_one_or_none()  # 现状：存在假 FROZEN 行，红
```
镜像用例（场景 B）：`last_activity_date = 周一 15:50 UTC`，NOW = 周二 22:00 UTC（上海周三 06:00），断言 `current_streak` 不增（本地隔了一整日）——现状 +1，红。

---

## F3 (P2) 冻结卡续签分支只加 `current_streak`，不同步 `max_streak`/`longest_streak`/`total_checkin_days` —— 冻结保住的连胜若随后断裂，「历史最长连胜」永久少记

**定位**
- `backend/app/services/achievement_engine.py:2076-2093`（delta==1 分支：`current_streak += 1` 后同步 `max_streak = max(...)`、`total_checkin_days += 1`、`longest_streak` 及 start/end）；
- 对照 `:2098-2103`（冻结分支：`freeze_charges -= days_missed; stats.current_streak += 1`，三者全部不更新，注释只有「今天也算」）。

**失败场景（输入序列 → 永久错数）**
1. 用户 `current_streak=30, longest_streak=30, max_streak=30`，冻结卡 ≥1；
2. 缺 1 日 → 冻结分支 → `current_streak=31`（真实达成了 31 天连胜，含冻结桥接），`longest_streak`/`max_streak` 仍 30；
3. 若次日正常活动（delta==1），`:2079/:2083` 会把两者补齐——错数只短暂可见；
4. 但若在下次 delta==1 到来前连胜断裂（连缺多日、冻结不足，`:2116` `current_streak=1`），`longest_streak`/`max_streak` 永远停在 30 —— 用户真实拥有的 31 天最长纪录**永久丢失**（后续只有再破 31 才会修复）。
消费方：`schemas/achievement.py:163`（成就统计 API 字段）、排行榜权重 1.5、`streak_signal_processor.py:43` 的 `maximum=max(max_streak, longest_streak)`（分子 `current_streak` 可瞬间 > 分母，`streak_consistency` 被 `min(1.0,...)` 掩盖但动机分带错）。

**可证伪测试草图**
```python
stats = await engine._get_or_create_streak_stats(uid)
stats.current_streak = stats.max_streak = stats.longest_streak = 30
stats.freeze_charges = 1; stats.last_activity_date = utcnow_date - 2d
await engine._update_streak_stats(uid, AchievementEvent.TASK_COMPLETED)      # 冻结桥接 → current=31
assert stats.longest_streak == 31                                            # 现状 30，红
await engine._update_streak_stats(uid, AchievementEvent.TASK_COMPLETED)      # 模拟断签前置：先推 last_activity_date 前移 5 日再触发
# 断签后
assert stats.longest_streak == 31                                            # 现状仍 30 —— 31 天纪录永久丢失，红
```

---

## F4 (P3) gRPC 冲突合并的「max-wins」实为无锁 SELECT + 盲写 upsert（TOCTOU）—— 并发窗口内更高的掌握度可被更低的合并值覆盖

**定位**
- `backend/app/services/galaxy_grpc_service.py:221-247`：`reason=="conflict"` 后 `:227-233` 普通 SELECT 当前 mastery（无 `FOR UPDATE`），`:235-238` `merged = max(current, request.mastery)`，`:241-247` 重试 `update_node_mastery` **不带 revision/version**；
- 该重试落入 legacy 分支：`backend/app/services/galaxy_service.py:3346-3350` 的 stale 检查因 `version=None` 被跳过，`:3358-3406` `ON CONFLICT (user_id, node_id) DO UPDATE SET mastery_score = EXCLUDED.mastery_score` —— 无条件覆写（last-writer-wins）。
- 与注释矛盾：`:220` 自称 "CRDT merge: resolve offline sync conflicts with max-wins semantics"。

**失败场景（输入序列 → 错误结果）**
离线设备 A（mastery=30，旧 revision）与服务端写方 W（revision 原子路径，mastery=90，如 error-book/quiz 同步）交错：
1. A 冲突返回；2. A SELECT current=10，merged=30；3. W 原子写 90（rev+1）；4. A 重试盲写 → **最终 mastery=30，90 丢失**（且 B 曾收到 success/new_mastery=90 应答）。max-wins 被破坏；若 W 是服务端一次性事件（outcome 回灌），90 不会重放，错值持久。
窗口为毫秒级（SELECT→upsert 之间），故 P3；但该路径正是为多端离线同步冲突设计的，冲突风暴期窗口变宽。

**可证伪测试草图**
两线程交错测试（或按序注入模拟）：db 会话 1 执行到 grpc 服务的 SELECT 后挂起；会话 2 走 revision 原子路径写 90；放行会话 1 重试；断言 `SELECT mastery_score` == 90 —— 现状 30，红。（单测可用 `update_node_mastery` 直接组合：先冲突，再于合并读后插一次高值原子更新，再跑重试分支。）

---

## F5 (P3) MasteryMergeCRDT 三处语义与自述契约相悖（当前仅 merge_mastery 接线，属潜伏面）

**定位**：`backend/app/services/galaxy/crdt_persistence.py:173-242`（类 docstring 自称 "All merges are commutative, associative, and idempotent (CRDT properties)"）。
- **(a) `merge_task_status` 把 abandoned(3) 排在 completed(2) 之上**（`:187-192`），与 "most-progressed wins" 自述矛盾：一端 completed、另一端（含陈旧离线态）abandoned 时合并结果=abandoned，完成被负向终态覆盖；abandoned 是失败终态而非「更进展」。
- **(b) `merge_node` docstring 说 metadata 走 "updated_at: latest wins (LWW)"，代码是纯 local-wins**（`:207` `merged = dict(local)`，全函数从未比较 `updated_at`）：离线端任何字段（除 mastery/status/revision 外）一律以本地覆盖远端，与文档语义相反。
- **(c) `revision = max(local, remote) + 1`（`:219`）破坏幂等性**：同一批 merge 重放（网络超时重试是 at-least-once 同步的常态）每次 +1，revision 无界膨胀。
**现状**：全仓仅 `galaxy_grpc_service.py:235` 接了 `merge_mastery`（纯 float max，无恙）；`merge_node/merge_batch/merge_task_status` 零调用方，属 APP-005 离线多端合并的预留 API —— 故 P3 潜伏；一旦离线同步卡按此 docstring 接线，上述三类错数直接进库。

**可证伪测试草图**
```python
assert MasteryMergeCRDT.merge_task_status("completed", "abandoned") == "completed"   # 现状 "abandoned"，红
a = {"mastery_score": 1, "status": "pending", "revision": 5}
assert MasteryMergeCRDT.merge_node(a, a)["revision"] == 6                            # 幂等性：重放一次应不变，现状 6→7，红
l = {"mastery_score": 1, "status": "pending", "revision": 5, "note": "local", "updated_at": t0}
r = {"mastery_score": 1, "status": "pending", "revision": 9, "note": "remote", "updated_at": t1 > t0}
assert MasteryMergeCRDT.merge_node(l, r)["note"] == "remote"                         # LWW 契约，现状 "local"，红
```

---

## F6 (P3) state_aggregator 跨钟表比较：本地墙上时间列与 UTC 值进同一个 `max()`/同一日界 —— `last_active_at` 可指向更旧的时刻，「今日空闲时段」按 UTC 日切

**定位**（`backend/app/state_aggregator/service.py`）
- `:523-531` `_build_engagement_state`：`last_active_at = max(latest_focus_at, streak_row.last_activity_date)`。`FocusSession.end_time` 存**客户端本地墙上时间**（mobile `focus_repository.dart:79` 本地 ISO 无时区后缀，`focus_service.py:77` `_to_utc_naive` 对 naive 原样入库——V3-FIX-37 已定界此列为本地墙钟），而 `UserStreakStats.last_activity_date` 由 `achievement_engine.py:2136` 写 **UTC 日零点**。两值钟表不同，`max()` 的语义不成立。
- `:940-941` `_build_calendar_context`：`today_start = now.replace(hour=0,...)`（now 为 naive UTC）→「今天」= UTC 日；事件列为本地墙钟，`time_blocks_today`/`_derive_available_time_blocks`（`:1199-1216`）据此切空闲格。
**失败场景**：上海用户：①凌晨 01:00 本地完成专注（墙钟 01:00 = 前日 17:00 UTC）vs 连胜 UTC 今日零点（= 本地 08:00）→ `max()` 选墙钟 01:00，`last_active_at` 实际指向**更旧**的绝对时刻；②本地 00:00–08:00 期间请求（UTC 仍在前一日），`today_events`/`time_blocks_today` 渲染的是**昨日**日程与空闲格。
**定级说明**：属时区家族但**不在案**——V3-FIX-37 修复面为 `statistics.py`/`focus_service`，wt559 六测为 plans/tasks；本文件两个构建器当时未被触达。消费方为 prompt 上下文/充分性判断（`engagement_state`、`calendar_context`），非持久化写面，故 P3。
**可证伪测试草图**：冻结 `now=2026-09-25T18:30Z`（上海 09-26 02:30），种 FocusSession(end_time=09-25 01:00 本地墙钟 naive) + UserStreakStats(last_activity_date=09-25 00:00 UTC)：断言 `last_active_at` 应为 streak 值（绝对时刻更新）——现状返回墙钟 01:00，红；同钟下断言 `time_blocks_today` 反映上海 09-26 日程——现状混入 09-25 事件，红。

---

## 扫过无发现的域

- **`backend/app/services/evidence/`（belief_state / fusion_engine / unified_evidence / outcome_evidence_adapter / conversational_extractor / reward_model）**：逐一核对概率/方差边界与更新顺序——confidence 钳 [0.01,0.99]、观测/后验方差钳 [0.01,0.25]、mean 走 unbounded 内部值+投影输出、`apply_temporal_decay` 对未来时间戳 `elapsed<=0` 早退、`update_user_state` 已有 WT294-P0 模块级按用户锁、`_decorrelate_same_source_evidence` 按时间序排序、`UnifiedEvidence.from_raw` 对 strength/confidence 钳制并拒 0。未发现可证伪的错数路径。
- **galaxy CRDT 持久化主干（`crdt_persistence.py` 的 snapshot/restore/persist_to_db）**：G-05 二进制安全客户端已收口，restore 有 Redis→PG 回退链；`persist_to_db` 直接 `commit` 不属本轴错数面。
- **galaxy `mastery_evidence.py` 纯函数本体**：clamp 齐全、衰减/重放序确定；F1 的缺陷在适配器层传参，不在纯函数。
- **`outcome_absorption_service` 幂等门**：读侧 `_already_absorbed` check-then-act 无唯一索引兜底存在理论并发双融窗口，但产物（mastery 抬升）方向正确且 F1 的基准值缺陷是其主要放大器，不单独成条，随 F1 复核时一并看。
- **排行榜/统计聚合**：V3-FIX-01/07（guest 污染）修复后 `_get_global_leaderboard` 已 `count(distinct)` 去笛卡尔积 + cohort 过滤（其 `user_score_q` 缺 `not_deleted_filter` 属口径不一致的极小面，且全局榜 D17 已隐藏不路由，不值一条）；mobile 统计 mock 债务已由 D-04 销账（台账在案不重报）。

## 复核提示（给第二轮）

- F1 优先：有纯函数级确定性数值复现（上表即仓内模块实跑），修法方向需产品/架构确认（保留首条 evidence 行 old_mastery 作 legacy 基准 vs 记录冻结先验）。
- F2 与 F3 同文件同函数，可合并为一张修复卡验收（F3 测试不依赖时区，可独立红绿）。
- F5 三点若接线前被删除/重写，整条可消。
