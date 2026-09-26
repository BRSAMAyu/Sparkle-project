# WT576 第二轮独立复核 — WT573 六条数据正确性发现

工位 wt576 ｜ 复核基线 2e3dfdb8（wt573 报告所在提交）｜ 2026-09-25 ｜ 只验证不修复，未动任何共享台账。
方法：每条先按 file:line 核实代码路径（行号漂移的按符号定位），再把可证伪测试草图真正跑起来（/tmp 一次性脚本，冻结钟 + sqlite 内存库 + 仓内 venv 解释器），复现不了的给反证。台账查重由本工位独立 grep，不采信 wt573 自述。

## 裁决总表

| # | 发现 | wt573 定级 | 复核裁决 | 复现方式 | 关键证据 |
|---|---|---|---|---|---|
| F1 | 掌握度重放融合基准值用已含历史的现值，历史每轮被再融合 | P2 | **存活（P2 维持）** | 纯函数实跑（镜像 `_load_prior_belief`+`spark_node` 适配语义） | 事件2 实际 79.956 vs 单遍语义 78.846（Δ+1.11）；实际语义第 7 个同类事件让 `mastery_score>=80`（SQL 直比 Float 列）判真，单遍语义 30 个事件永不判真 |
| F2 | 连胜引擎日界 = UTC 日，丢弃调用方传入的本地 activity_date | P2 | **存活（P2 维持）** | 真实 `AchievementEngine._update_streak_stats` + 冻结钟 + sqlite，UTC+8 双向场景 | 场景 A（本地连续日）：冻结卡 1→0 误烧 + 假 FROZEN 行 09-27 落库；场景 B（整缺一个本地日）：current 5→6 白嫖 +1 |
| F3 | 冻结续签分支不同步 max_streak/longest_streak/total_checkin_days | P2 | **存活（P2 维持）** | 同上装置（不依赖时区） | 冻结桥接后 current=31 而 longest=30；随后断签 → 31 天纪录永久丢失（longest 恒 30） |
| F4 | gRPC 冲突合并 max-wins 实为无锁 SELECT + 盲写 upsert（TOCTOU） | P3 | **存活（P3 维持）** | 真实 `GalaxyService.update_node_mastery` 按序注入交错 | 冲突→窗口内原子写 90→盲写重试 30 成功→最终 mastery=30.0（90 丢失） |
| F5 | MasteryMergeCRDT 三处违背自述契约（abandoned>completed / 假 LWW / revision+1 破坏幂等） | P3 | **存活（P3 维持）** | 纯函数断言 + 全仓调用方 grep | 三断言全红；merge_node/merge_batch/merge_task_status 零外部调用方（潜伏面确认） |
| F6 | state_aggregator 跨钟表 max() 与 UTC 日界 | P3 | **存活（P3 维持）** | 真实 `StateAggregatorService` 双构建器 + 种子数据 + 冻结钟 | last_active_at 返回墙钟 01:00（绝对时刻比 streak 值旧 7h）；time_blocks_today 按 UTC 日 09-25 切：昨日 14:00–15:00 事件切开「今日」空闲格、本地今日 09:00–10:00 忙碌缺席 |

**六条全部存活，零误报，零降级，零升级。** wt573 的定位、机制描述与定级均经独立复现成立。

---

## F1（P2）掌握度证据账本重放基准值缺陷 — 存活

**路径核实**：全部属实。`stats_service.py:126`（`old_mastery = status.mastery_score`）→ `:130` 传给 `_load_prior_belief` → `:578` `belief = recompute_evidence_state(current_mastery, history)`；`recompute_evidence_state` 契约（`mastery_evidence.py:286-297` docstring）确为「从 legacy 先验（max uncertainty=0.25）出发重放」。触达路径 2 `outcome_absorption_service.py:199/:206-208` 同样把现值当基准。旁证属实：`:561-565` 对无 payload 行明写 "already baked into the stored mastery...not re-fused"，同一逻辑对带 payload 的 `evidence:` 行不成立。

**独立复现**（`/tmp/wt576_f1_repro.py`，镜像适配器真实语义：空账本走 `MasteryBelief(mean=current)`、否则 `recompute_evidence_state(current, rows)`，再 `fuse_mastery` 新观测）：

```
event | actual (code) | intended (single-pass) | delta
  1   | 77.692308      | 77.692308              | +0.000
  2   | 79.955621      | 78.846154              | +1.109
  3   | 79.999573      | 79.423077              | +0.576
  4   | 79.999998      | 79.711538              | +0.288
  5   | 80.000000      | 79.855769              | +0.144
```

wt573 报告数字（77.692 / 79.956 vs 78.846 / 第 3 事件 80.00）逐位对上。

**阈值核证**（`/tmp/wt576_f1_threshold.py`）：`calculate_user_stats`（`stats_service.py:373`）是 SQL `mastery_score >= 80` 直比 Float 列。float64 精度下实际语义第 **7** 个同类事件使该谓词判真（值恰为 80.0）；单遍语义 30 个同类事件后仍 79.9999999957016、**永不判真**。报告表中「第 3 事件钉死 80.00」是二位小数显示口径——严格 DB 阈值跨越在第 7 事件，结论（提前跨 mastered 阈值 + 系统性过信）不变且被加强。

**严重度**：P2 恰当。生产主链可达（spark_node outcome + outcome_absorption 回灌是 G-01 主线），任意节点累计 ≥2 条同类证据即触发，误差方向系统性偏向观测值，且直接影响 mastered 计数与后验方差（每轮重置 0.25 再坍缩）。

**修复方向（一句话）**：重放基准改为「证据前 legacy 锚点」（首条 evidence 审计行的 `old_mastery` 即该值）而非当前存储值，或首次融合时冻结先验快照供后续重放。

**查重**：`DYNAMIC_ISSUES.md` 与 `KNOWN_CODE_DEBT_LEDGER.md` 均 grep 无 `recompute_evidence_state/_load_prior_belief/证据账本/mastery_evidence` 命中，不在案。

---

## F2（P2）连胜引擎 UTC 日界 + 丢弃 activity_date — 存活

**路径核实**：属实。`achievement_engine.py:2034` `today = _utcnow().date()`；`:2031` 签名 `**kwargs` 全函数不读 `activity_date`（grep 全文件仅 `:715` 另一方法用到 kwargs）；`:2065` delta 决定分支。调用方证据属实：`accountability.py` 打卡去重用 `_day_range_for_timezone(_user_timezone(...))` 本地日、`:1445-1448` `process_event(..., activity_date=today_start.date())` 传入后被引擎丢弃（kwargs 经 `:404` 原样透传进 `_update_streak_stats`）。

**独立复现**（`/tmp/wt576_f2_f3_repro.py`：冻结模块级 `_utcnow`，真实引擎直驱，sqlite 内存库）：

- **场景 A（误烧冻结卡）**：last_activity=09-26 16:30 UTC（上海周日 00:30 打卡），冻结 NOW=09-28 15:40 UTC（上海周一 23:40）。本地日周日→周一连续；UTC 日差 2：
  ```
  freeze_charges: 1 -> 0   （正确应为 1：本地连续不该烧卡；日志实证 "used 1 freeze charges"）
  streak days: [('2026-09-27', 'frozen'), ...]   （用户没缺的本地日被写成假 FROZEN 行）
  VERDICT A: freeze wrongly burned = True
  ```
- **场景 B（白嫖续签）**：last_activity=09-28 15:50 UTC（上海周一 23:50），本地整个周二不活动，NOW=09-29 22:00 UTC（上海周三 06:00）：
  ```
  current_streak: 5 -> 6   （本地整缺一日应走冻结/断签，现状 UTC delta=1 免费 +1）
  VERDICT B: skipped local day got free renewal = True
  ```

**严重度**：P2 恰当。非 UTC 用户（缺省 Asia/Shanghai 是产品主群）日常即可触发；双向都产持久错数（`user_streak_days` 假 FROZEN/缺 MISSED 行 + 计数器错），并与已裁决的 V3-FIX-37/wt559/V3-FIX-197~211「用户本地日」家族契约同族漏网。

**修复方向（一句话）**：`_update_streak_stats` 改用调用方透传的 `activity_date`（缺省经 push_preference.timezone 解析用户本地日，沿 accountability/_local_today 先例），today/last_activity/streak-day 行全部同钟。

**查重**：台账 nearest 命中为 V3-FIX-03（mobile mock）/V3-FIX-37（focus/statistics 面），均非本面；`_update_streak_stats/last_activity_date 时区` 无在案行。

---

## F3（P2）冻结续签不同步 max_streak/longest_streak — 存活

**路径核实**：属实。`achievement_engine.py:2076-2093`（delta==1 分支同步 `max_streak`/`total_checkin_days`/`longest_streak`+start/end）对照 `:2098-2103`（冻结分支仅 `freeze_charges -= days_missed; current_streak += 1`，注释只有「今天也算」）；断签 `:2116` `current_streak = 1` 不回填纪录。

**独立复现**（同 F2 装置，不依赖时区）：

```
seed: current=max=longest=30, charges=1, last=NOW-2d
after freeze bridge: current=31 max=30 longest=30 charges=0   ← 红峰值
after break (last 前移 5 日再触发, charges=0): current=1 max=30 longest=30
→ 31 天真实纪录永久丢失（只有日后破 31 才被修复）
```

**消费方核实**：`leaderboard_service.py:232-234` 复合分含 `longest_streak × WEIGHT_STREAK`；`streak_signal_processor.py:43` `maximum = max(max_streak, longest_streak, 1)`、`:52` `streak_consistency = min(1.0, current/maximum × ...)`（min 掩盖方向反转但动机分带错）——与报告一致。

**严重度**：P2 维持（处于 P2/P3 边界）。前提链（持冻结卡→缺勤→冻结桥接→下次 delta==1 前断签）对真实用户常见；错数是永久性的且进排行榜权重。wt573 的 F2/F3 合并验收建议合理。

**修复方向（一句话）**：冻结分支照抄 delta==1 分支的簿记（`max_streak`/`longest_streak`+end/`total_checkin_days` 与 `current_streak += 1` 同步更新）。

**查重**：`max_streak/longest_streak` nearest 为 V3-FIX-257（guest 种子伪造统计），非本面。

---

## F4（P3）gRPC 冲突合并 TOCTOU 盲写 — 存活

**路径核实**：属实。`galaxy_grpc_service.py:221-247`：conflict 后 `:227-233` 普通 SELECT（无 FOR UPDATE）、`:235-238` max 合并、`:241-247` 重试**不带 version/revision**（注释自认 "retry without revision check"）；该重试落 `galaxy_service.py` legacy 分支（`if revision is not None` 为假），postgres 面的 stale 检查因 `version=None` 跳过，`:3397-3405` `ON CONFLICT DO UPDATE SET mastery_score = EXCLUDED.mastery_score` 无条件覆写。

**独立复现**（`/tmp/wt576_f4_repro.py`：真实 `GalaxyService.update_node_mastery`，按序注入模拟交错）：

```
seed: mastery=10, revision=5
step1 A stale write (revision=3, mastery=30): success=False reason=conflict current_revision=5
step2 W atomic write (revision=5, mastery=90): success=True new_mastery=90.0   ← 窗口内
step3 A blind retry (无 version/revision, mastery=30): success=True new_mastery=30.0
FINAL mastery_score = 30.0   (max-wins requires 90)
VERDICT F4: higher value overwritten by lower = True
```

**严重度**：P3 恰当。窗口为 SELECT→upsert 毫秒级且需冲突路径+并发写方同时在场；但一旦命中即持久错值（90 不重放），且该路径正是为多端冲突设计的——风暴期窗口变宽。

**修复方向（一句话）**：重试改为 revision 守护的条件写（compare-and-set 循环内重算 max）或 SELECT...FOR UPDATE 后再写，废弃无版本盲写。

**查重**：`merge_mastery/galaxy_grpc conflict` 两本台账零命中。

---

## F5（P3）MasteryMergeCRDT 三处契约相悖 — 存活

**路径核实**：属实（`crdt_persistence.py:173-242`）：docstring "All merges are commutative, associative, and idempotent" + merge_node 自称 "LWW for metadata"，代码 `:207` `merged = dict(local)` 纯 local-wins、`:189` 序表 abandoned(3)>completed(2)、`:219` `revision = max+1`。

**独立复现**（`/tmp/wt576_f5_repro.py`）：

```
(a) merge_task_status('completed','abandoned') = 'abandoned'   （契约应为 completed）
(b) merge_node(x,x).revision = 6；再合一次 = 7                  （幂等 CRDT 应恒 5）
(c) remote updated_at 09-09 > local 09-01：merged note = 'local'（契约应为 'remote'）
callers outside definition module: NONE（潜伏面确认，仅 merge_mastery 被接线且为纯 max 无恙）
```

**严重度**：P3 恰当。零调用方 → 今日无生产错数路径；但 APP-005 离线同步一旦按 docstring 接线，三类错数直接进库。若接线前删除/重写该 API，整条可消（wt573 复核提示已自我声明）。

**修复方向（一句话）**：接线前重写契约——终态序表把 completed 置于 abandoned 之上（或 abandoned 单独 flag）、metadata 真按 updated_at LWW（或改文档承认 local-wins）、revision 改 `max(local, remote)` 恢复幂等。

**查重**：`MasteryMergeCRDT/crdt_persistence` 两本台账零命中。

---

## F6（P3）state_aggregator 跨钟表 max 与 UTC 日界 — 存活

**路径核实**：属实。`state_aggregator/service.py` `_build_engagement_state`：`last_active_candidates = [latest_focus_at, streak_row.last_activity_date]` → `max()`；列钟表定界与 V3-FIX-37 一致（`focus_service.py:44-48` `_to_utc_naive` 对 naive 原样放行；mobile `focus_repository.dart:79` `end_time.toIso8601String()` 本地 ISO 无时区后缀——行号逐字核实）。`_build_calendar_context:940-941` `today_start = now.replace(hour=0,...)`（now 为 naive UTC）。

**独立复现**（`/tmp/wt576_f6_repro.py`：真实 `StateAggregatorService` 双构建器，冻结 NOW=2026-09-25 18:30 naive-UTC = 上海 09-26 02:30）：

```
=== F6-1 _build_engagement_state ===
seed: FocusSession(end_time=09-25 01:00 本地墙钟) + UserStreakStats(last_activity_date=09-25 00:00 UTC)
绝对时刻：墙钟 01:00 = 09-24T17:00Z；streak 09-25T00:00Z（新 7 小时）
last_active_at returned : 2026-09-25 01:00:00
picked older absolute moment = True   ← max() 选了绝对时刻更旧的值

=== F6-2 _build_calendar_context ===
seed: 本地墙钟事件 上海 09-26 09:00-10:00（用户今日）+ 09-25 14:00-15:00（用户昨日）
time_blocks_today = [07:00-14:00, 15:00-22:00]  ← 参照日=UTC 09-25（=用户昨日）
昨日 14:00-15:00 事件把「今日」空闲格切开；用户本地今日 09:00-10:00 忙碌完全缺席
```

**严重度**：P3 恰当。两面都是 prompt 上下文/充分性判断读面（`engagement_state`/`calendar_context`），非持久化写面；时区家族在案行（37/197/207/208/211）确未触达本文件两构建器。

**修复方向（一句话）**：`last_active_at` 比较前把墙钟列经用户时区换算成同钟（或分别存绝对时刻），calendar 日界沿 time_utils `local_date`/`local_midnight_wall` 先例切用户本地日。

**查重**：`state_aggregator` nearest 为 V3-FIX-11（遥测渗入 :524）/V3-FIX-187/263（路由/mypy），均非钟表面。

---

## 复核附记

1. **F1 数字核对的唯一偏差**是显示口径（「第 3 事件钉死 80.00」实为 79.9996 的二位舍入；严格 float64 跨阈值在第 7 事件）——属报告表述精度问题，不动摇结论，反而说明跨阈值是渐近必然而单遍语义下永不发生。
2. wt573「扫过无发现的域」声明未逐域重扫（超出本轮职责），但 F1 复核顺带验证了 `mastery_evidence.py` 纯函数本体确无缺陷（clamp/重放序确定），缺陷确在适配器传参。
3. 复现脚本存 /tmp（wt576_f1_repro.py、wt576_f1_threshold.py、wt576_f2_f3_repro.py、wt576_f4_repro.py、wt576_f5_repro.py、wt576_f6_repro.py），未入库（仓库整洁规则）。

## 存活项建议派发顺序

1. **F1**（独立修复卡）：核心掌握度主线、确定性红绿、生产任意 ≥2 证据节点即触发；修复方向需产品/架构先拍板（legacy 锚点 vs 冻结先验），红测可先行钉死 wt573 表格数字。
2. **F2+F3 合并一张卡**（同文件同函数）：F3 红测不依赖时区可先落；F2 修完需评估 `user_streak_days` 既有 UTC 行的迁移/回填口径——这一步需要 HUMAN_INBOX 或架构确认，不阻塞 F3 先行。
3. **F6**：沿 V3-FIX-37/208/211 既有双冻结钟红测族与 time_utils 工具接线，机械度高。
4. **F4**：并发面收口（compare-and-set），窗口窄但持久错值，可在 galaxy 并发卡批次搭车。
5. **F5**：潜伏面零调用方，优先级最低；接线卡启动前先做「重写或删除」的架构决定即可。
