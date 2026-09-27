# P 线（Proactive 6 卡）深挖章节 —— V4 交接文档素材（wt775）

> 本文是 `v3/V3-COMPLETE-STATUS-FOR-V4.md` §4「各线深度状态」P 线章节的深挖草稿。
> 证据纪律：只写三源证据（git 主干 SHA / 独立审查 receipt / 运行级实测）支撑的事实；逐条标注出处；无法定位证据的验收项显式标注「未定位到证据」。
> 撰写：wt775（2026-09-28，基线 main@ed072fd2）。方法：卡面（v3/07_tasks/cards/P-0*.md）+ wt759 报告逐卡 SHA → `git log -1` 全部 8 个交付 SHA 重验在主干 → 关键代码开文件亲证（pipeline/suppression/relevance/autoexec/notification_settings/config/main.py 接线）→ 测试逐文件计数 → v3-output/WT384-P05-EVAL REPORT 全读 → 台账 FIX-48/120/121/152 逐行复核。**未轻信任何台账/报告结论性文字。**

---

## P.0 线级概览

P 线回答的是「AI 陪伴产品最容易翻车的自愿问题」：主动式触达如何不打扰。6/6 全部 done（tasks.json + fleet 名单 + wt759 逐卡 SHA）。

执行形态的显著特点（V4 设计者需要知道）：

1. **P 线的「灵魂不变量」是零 LLM + fail-closed**：P-01 管线全链（分类/抑制/相关性/记录/投递）没有任何模型调用（pipeline.py 模块 docstring 亲证「本模块不 import 任何 LLM 客户端，测试以 mock 计数器断言调用数 = 0」）；抑制状态 store 在 Redis 故障时全抑制（「宁可少发不可误发」）。
2. **两条主动面通道并存（V4 最重要的结构事实）**：
   - **nudge 家族（活、真投递、被 P-05 纵向评估）**：`comeback_nudge_task`（celery）→ get_comeback_context → suppression → NotificationService.create——P-05 的 14 天评估驱动面就是它；P-03 的四要素 UX 与反馈回路（今天不看/mute/cooldown）明确声明「在既有 nudge 真源之上补齐，不重建真源」（proactive_suggestion_service.py 模块 docstring 亲证）。
   - **P-01 事件管线（已接线、默认 shadow、不真投递）**：main.py:423-440 亲证 lifespan 里构建 ProactiveEventPipeline 并 attach EventBus；`PROACTIVE_PIPELINE_SHADOW` 默认 **True**（config.py:43）——would-notify 只记 Prometheus 计数+有界环形缓冲+可注入 sink，不触发真实出口；live 需显式 env 翻 0，投递经 SystemUpdateService.enqueue（journey consumers 同款系统更新通道，Redis list `system_updates:{user}`），**与 nudge 家族的 NotificationService 是两个出口**。
   - V4 若做「统一主动面」，第一决策就是这两族的合并/分工——P 线交付没有裁决它，而是把两族各自做实。
3. **卡面场景全部落在确定性管线里**：7 触发器（deadline/overdue/slot_missed/user_active/upstream_completed/goal_stalled/run_awaiting，triggers.py:56-62 亲证）由 10 个事件名映射（task.started/created/abandoned/status_changed、focus.session.completed、plan.health.alerted、task.completed、run.status_changed、run.awaiting_user、galaxy.study.recorded，triggers.py 分类分支逐条亲证）。

---

## P.1 意图（卡面目标与验收）

六卡共性 Forbidden 条款（卡面原文，全线一致）：不得重建已存在的权威真源；不得用 mock/seed 冒充真实行为；不得只通过静态代码阅读宣称用户体验通过；不得弱化既有安全/幂等/隔离/审计守卫。

| 卡 | Risk/Resource/Reviewers | 卡面目标（一句话） | 卡面关键验收 |
|---|---|---|---|
| P-01 Event-trigger + Suppression Pipeline | medium/MEDIUM/1 | 主动式做成 event→filter→Aurora，不是定时问 LLM | mute/quiet/cooldown 抑制=100%；无需 LLM 的事件不调用模型；shadow metrics 可审 |
| P-02 NO_ACTION / Relevance Decision | medium/MEDIUM/1 | 让 Aurora 学会保持安静 | 20+ suppression/relevance cases 违规=0；false positive 受控 |
| P-03 Proactive Suggestion UX | medium/HEAVY/1 | 建议以可忽略、可解释、可 mute 方式呈现 | 重复建议不刷屏；拒绝后 cooldown 生效；离线/过期通知点击有合理恢复 |
| P-04 低风险 Auto-execute 授权模型 | critical/MEDIUM/2 | 仅预授权低风险操作允许 proactive auto execution | 未授权=0 auto；revoke 后立即失效；重复 trigger 不重复 side effect |
| P-05 Proactive Longitudinal Evaluation | medium/MEDIUM/1 | 验证主动带来目标恢复而非通知负担 | precision 达阈值并报告；quiet violations=0；不只报 open rate |
| P-06 Notification Burden / Quiet / Low-stimulation 终局 | medium/HEAVY/1 | 用户主动控制与关系策略完全接通 | 24h test-clock 0 超 cap；mute 生效；低刺激默认更保守；in-flight 关停真生效 |

---

## P.2 实际交付逐卡

### P-01 · 事件触发 + 确定性抑制管线

**交付**：`fa96be0d`（R2 CHANGES reworked delta-verified；独立审查 R2 在 commit 标注）。
**真实数据流（代码亲证，`backend/app/aurora/proactive/` 共 2,912 行六模块）**：

```
EventBus(sparkle_events) 消费者组 aurora_proactive_pipeline（继承 idempotency/DLQ/retry）
  → classify_event（9 事件名 → 7 触发器）
  → ProactiveSuppressionStore.load_snapshot（fail-closed：Redis 故障全抑制）
      + per-user 统一设置注入（P-06：quiet_window/daily_cap/timezone，解析失败回退 env 保守基线并告警）
  → evaluate_suppression（quiet window / mute / daily cap / cooldown / recent rejection / novelty，
     suppression.py：in_quiet_window 亲证 22:00-08:00 Asia/Shanghai 默认、cap 3、cooldown 240min、rejection 阈值 2）
  → evaluate_relevance（P-02，四问裁决）
  → ProactiveDecisionRecord → _record（Prometheus PROACTIVE_PIPELINE_DECISIONS_TOTAL 按 trigger/event/decision/reason 分桶
     + deque 有界 recent_records + 可注入 DecisionSink）
  → shadow=True：logger would-notify 记录即止；shadow=False：_default_deliver → SystemUpdateService.enqueue
     （payload 带 pipeline=proactive_v1/trigger/subject_key/correlation 元数据）
```

- **失败语义**：`_on_bus_event` 失败**上抛**（EVENT-ACK-2 判例亲证在 pipeline.py:383-401：原 blanket-except 吞异常使总线恒 ack、失败 metric/重试/DLQ 永不触发——已修为交给总线失败管线；管线内部逐处 contain）。
- **测试**：backend/tests/aurora/test_proactive_event_pipeline.py **32 个 test**；抑制/相关性/投递通道族另有 nudge_channel_delivery 14、proactive_suggestion_feedback 12+3+3、burden_p06 21、inflight_wake_suppression 10、24h_clock 5（逐文件 grep 计数）。
- **shadow metrics 可审**：Prometheus 分桶计数+decision record 结构化（event/trigger/user/decision/reason/step/subject_key/shadow/occurred_at/details）亲证在 pipeline.py:196-247。

**残差**：默认 shadow 是文档化的 by-design（main.py 注释「接通即安全；真实投递需显式 PROACTIVE_PIPELINE_SHADOW=0」），但**当前无任何环境配置翻它**（全仓 grep 该 env 仅 config/pipeline/main 注释三处）——事件管线的用户可见投递为零，V4 必须**显式决策**何时翻 live（见 §P.4-2）。

### P-02 · NO_ACTION / 相关性裁决

**交付**：`a8567153`（R2 PASS）。
**真实数据流（relevance.py 473 行亲证）**：位于 P-01 抑制链**之后**、出口之前；四问裁决固定短路序（新信息？有行动价值？未被看过/处理过？用户近况允许？）——每个 no_action 带稳定结构化 reason，reason ∈ `RELEVANCE_REASONS` 封闭词表（:87「新增值必须进此元组并过契约测试」）；`derive_information_digest`/`derive_information_onset` 确定性派生（同一输入永远同一输出）；USER_ACTIVE 直通语义保持（bare user_active 零改动）；`ProactiveRelevanceStore` Redis 承载 reminder/view/interaction/change 四类记录（scope 分 live/shadow）。
**「仅逾期不够」验收**：has_actionable_step 默认 True 的**正向证据原则**（仅当载荷显式 `actionable=False` 才判非行动）+ 信息摘要/onset 双通道亲证在 pipeline.py:409-449。
**测试**：backend/tests/aurora/test_proactive_relevance.py **29 个 test**（含词表冻结契约）。
**「20+ cases 违规=0」**：用例数 29≥20 达标；违规=0 以封闭词表+契约测试承载。

### P-03 · 主动建议 UX（四要素+反馈回路）

**交付（三波）**

| 波次 | 主干 SHA | 内容 |
|---|---|---|
| 四要素 UX | `78ff5538`（wt370） | 每条建议卡四要素：why now（引擎侧事实构建，只述计划状态/任务账本/下一步，零 guilt 零诊断）/ suggested action / today ignore / mute this type；deep link 到正确 Goal/Proposal |
| 复核修复 | `cc84094e`（wt379） | P-03/J-04 六项猎缺修复（含 P-03 抑制态读写诚实化） |
| 审查轮 | wt424/450/468 | 摩擦门族轮 5/6/7 连续覆盖（wt759 报告口径） |

**主干面亲证**：`mobile/lib/features/notification_center/presentation/widgets/unified_notification_card.dart:687` 注释即「P-03 四要素：why now / suggested action / today ignore / mute this type」——`whyNow`（:691-716）、`onSuggestionIgnoreToday`、`onSnooze`（:58）三 handler 在树；反馈持久层=UserPreferencesCenter.explicit JSONB 独立命名空间（零迁移）；抑制在生成源头（真源不产新通知，非渲染层遮蔽——服务 docstring 亲证）。
**测试**：feedback 12+3+3、concurrent_merge 3、nudge_channel_delivery 14（计数见上）。
**残差**：「离线/过期通知点击有合理恢复」的端到端真机验证未定位到运行级记录（deep link 解析在 `resolve_comeback_destination` 纯函数层有测试：goal_id→Goal 页→Plan 页→chat 回退链，F-7 判例防 plan_id 误用）。

### P-04 · 低风险 Auto-execute 授权模型（critical，双审查）

**交付（双波双审）**：`15bd350e`（主卡，R2 PASS）+ `322988ce`（wt376：类别级预授权面+五条件门/fail-closed）。
**主干面亲证（autoexec.py 981 行）**：
- **allowlist 是封闭词表 + import 期校验**：`AutoExecOperation` StrEnum；每条目 `AutoExecOpMetadata` 必 `risk="low"` 且 `reversible=True`——`validate_autoexec_allowlist` 在 import 期跑，违宪直接 raise ValueError（:206-208「high-risk ops are forbidden」「irreversible ops are forbidden」）；注册表冻结映射+契约测试 sha 双钉。
- **授权面**：`AutoExecGrantStore` grant/revoke 前置校验只有词表内操作可授予（越界 ValueError——「授权面不可能铸出 allowlist 外的能力」）；`compute_grant_policy_version` 授权态指纹。
- **幂等**：`derive_autoexec_idempotency_key`（重复 trigger 不重复 side effect 的机制载体）。
- **receipt**：receipt 三要素（commit 明示）+ receipt_key 存储。
- 五条件门/fail-closed 语义：wt376 commit「高风险/不可逆永远 proposal；revoke 时序」。
**测试**：backend/tests/aurora/test_proactive_autoexec.py **36 个 test**。
**「未授权=0 auto」的运行级背书**：P-05 纵向评估不变量「revoke 后 auto 直通=0」全零（§P.2-P-05）。

### P-05 · 主动面纵向评估（14 天可控时钟 24v24）

**交付**：`761e75a1`（wt384）；产物 v3-output/WT384-P05-EVAL/{summary.json, EVAL_RESULTS.md, raw/*.jsonl}；复跑脚本 scripts/devtools/p05_run_proactive_longitudinal_eval.py（--summarize-only 可从 raw 复算）。
**核心数字（REPORT 全读，全部程序化复算非手填）**：restart 率 0.875 vs 0.542（Δ+0.333）、重启中位 2 vs 7 天、deadline 达成 0.417 vs 0.0、期末账本进度 0.773 vs 0.412；负担轴 112 条建议/14 天（人均 4.67、最坏 14）、disposition accept 45.5%/silent 19.6%/dismiss 26.8%/mute 8.0%；**正确性不变量全零**（mute 后跨天复发=0、沉默<3 天投放=0、revoke 后 auto 直通=0、accept 次日复发=0）。
**诚实声明（REPORT 原文）**：persona 决策是 **seeded 显式模型**（参数全量落 raw/events_timeline.json）——「上述量化是该模型与真实主动面行为的联合结果，不是真人 RCT；效应方向与主动面行为正确性不依赖模型参数，效应量级不可外推为真实用户指标」。这条诚实边界必须带进 V4：**P-05 证明的是「主动面机制行为正确」，不是「真人指标改善」**。
**驱动面口径**：直调生产 celery 任务 comeback_nudge_task（真实 get_comeback_context→suppression→duplicate 窗→NotificationService.create 全链，仅 AsyncSessionLocal 重定向 sqlite）+ 真实 ActionCommandService/ProactiveSuggestionFeedbackService/ActionPermissionService——**驱动的是 nudge 家族，不是 P-01 事件管线**（后者 shadow 默认且评估时点已存在；两族关系见 §P.0-2）。
**反例如实回流**：FIX-48（P3，OPEN 待拍板）——「今天不再看」在每日扫描节奏下只买同日安静（30 dismiss 中 26 次次日仍投放；IGNORE_TODAY_COOLDOWN_HOURS=24h 与 24h 重复窗在两次日 tick 间双双过期）+ 过期窗口每日继续打扰（4 次实证）。完成谱正控：账本 100%→sprint auto-archive→主动面源头停（完成后投放=0）。

### P-06 · 通知负担 / Quiet / 低刺激终局

**交付**：`05cc6328`（wt387：统一设置一处真源+多设备服务端权威+in-flight 关停真生效+统一解析器/quiet 交集/24h cap）。
**主干面亲证**：
- **用户设置真接入管线**：`notification_settings.py`（runtime_v1）EffectiveNotificationPolicy（quiet_supresses/allow_proactive_push/proactive_suppress_hours/to_payload）+ NotificationSettingsResolver（DB）+ widen_quiet_window（低刺激把 quiet 窗**加宽**——「低刺激默认更保守」的机制载体）；main.py:431-440 `make_db_settings_provider(AsyncSessionLocal)` 注入 P-01 管线（P-06 commit 注释亲证「用户设置不再只是展示面，事件管线抑制链据此判定」）。
- **in-flight 关停**：backend/tests/aurora/test_inflight_wake_suppression.py（10 test）——用户关闭后已排程通知被取消/抑制的语义锁；24h cap：test_notification_burden_24h_clock.py（5 test，24h test-clock 口径）+ test_notification_burden_p06.py（21 test）。
- FIX-150 同族守卫（main.py:429-434 注释）：函数级 import AsyncSessionLocal 会致 UnboundLocalError 的红测实录在案。
**残差**：「多设备 state 一致」以服务端权威（DB resolver）承载，真多设备并发实测未定位到运行级记录。

---

## P.3 设计决定与取舍

1. **确定性优先于智能**：整条管线零 LLM；「无需 LLM 的事件不调用模型」不是验收副产品而是模块红线（import 面+mock 计数断言双钉）。LLM 只可能出现在管线之外的内容生成，决策面全是规则。V4 若加语义相关性判断，应作为 P-02 四问之外的旁路证据而非替换短路序。
2. **fail-closed 全链**：快照读失败=全抑制；设置解析失败=回退保守基线+告警；授权词表违宪=import 期崩溃。方向统一为「宁可少发/不执行，不可误发/越权」。
3. **shadow-first 接线**：管线先以默认 shadow 接进 main，出口适配器可注入——把「接通即安全」做成默认态。代价是 live 化成为需要显式决策的悬置面（见 §P.4-2）。
4. **P-03 不重建真源**：在 nudge 家族之上补反馈回路与四要素 payload——尊重「不得重建已存在的权威真源」Forbidden 的正面样本；副作用是「主动面」在架构上仍是两族（§P.0-2），统一裁决被留给了未来。
5. **评估的诚实分层**：P-05 把「机制正确性」（不变量全零，可复用）与「效应量级」（seeded persona 模型，不可外推）显式分离；反例不剪照登进台账（FIX-48 OPEN）。
6. **时间敏感测试的隔离纪律**：p05_proactive 4 例 CI 红的根因是上海 quiet 窗挂钟面——按在库先例补 `PROACTIVE_QUIET_HOURS_ENABLED=False` fixture 收口（FIX-121@eca6493b 内处置，台账亲证）；P 线测试从此对挂钟免疫。

---

## P.4 残差与 V4 注意点（汇总）

1. **FIX-120/121 隔离审计族的 P 线相关现状**：两族均 FIXED（120@765c9b16 wt444 / 121@eca6493b wt446）。与 P 线直接相关的两点已收口：①SRL 族 24 例污染源（裸赋值 settings.AURORA_SRL_MODE 不恢复）以 autouse 复位 fixture 收口——kill_switch/cache_service 进程级共享单例的复位基建从此存在；②p05_proactive 4 例时钟敏感以 quiet 窗关断 fixture 收口。**V4 注意**：autouse 复位 fixture 是后加的，新增全局态仍可能重演——新增 settings 级开关时同步进复位 fixture 是纪律不是选项（台账 120 行协调方补记的 auth 双测互扰同族）。
2. **P-01 管线的 live 化是悬置决策**：shadow 默认+无环境配置翻面+投递通道（SystemUpdateService）与 nudge 家族（NotificationService）并存。V4 设计主动面时必须先裁决：两族合并 or 分工（管线管事件驱动短周期、nudge 管召回/回归长周期）？投递出口统一 or 各自维护？P-05 的纵向评估只覆盖 nudge 族——管线 live 化前应补一次同构纵向评估。
3. **FIX-48 OPEN（待拍板）**：「今天不再看」的 24h 语义在每日扫描节奏下失效（26/30 次日复发）+过期窗口每日打扰。修法涉及产品语义裁决（ignored_until 的锚点从「时刻」改「日界」或扫描节奏改事件驱动），不是机械修。
4. **quiet/mute 状态存储在 UserPreferencesCenter.explicit JSONB**：独立命名空间零迁移是 V3 的速度取舍；V4 若做主动面统一，建议把抑制态提升为一等实体（带审计与跨设备一致性测试），现在的 JSONB 面缺独立观测。
5. **P-03 的恢复路径真机验证欠账**：离线/过期通知点击恢复只有纯函数层测试；建议随 U 线真机批次一并采集。
6. **允许差异**：卡面「shadow metrics 可审」的 Prometheus 分桶已在，但**无 Grafana/告警面**（O 线未覆盖主动面指标看板）——V4 运维设计应把 PROACTIVE_PIPELINE_DECISIONS_TOTAL 的 would-notify 比例作为 live 化前的观察指标。

---

## P.5 本次审查登记

- 本次 P 线深挖**无新缺陷登记**。复核过但不构成新发现的三项：①P-01 默认 shadow（main.py/config.py 文档化 by-design，非隐性脱钩——对照 FIX-500 的 AURORA_DEFAULT_MODE 判例，该例是「声明面零读者」，本例是显式注释+无误导声明）；②P-05 评估驱动 nudge 族而非事件管线（REPORT 口径声明明确，非证据失实）；③FIX-48 反例回流（已在账 OPEN）。
- 交叉登记：P 线无关但本次发现的 U 线台账缺行（377）与 HUMAN_INBOX 回填缺口见 U-line.md §U.5（507/508）；S 线 demo 群标记见 S-line.md §S.5（506）。
- 号占用核验：500-504 已占用；505 空闲备而不用；本线未占用新号。
