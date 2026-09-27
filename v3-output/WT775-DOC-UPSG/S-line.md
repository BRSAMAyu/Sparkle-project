# S 线（Community 5 卡）深挖章节 —— V4 交接文档素材（wt775）

> 本文是 `v3/V3-COMPLETE-STATUS-FOR-V4.md` §4「各线深度状态」S 线章节的深挖草稿。
> 证据纪律：只写三源证据（git 主干 SHA / 独立审查 receipt / 运行级实测）支撑的事实；逐条标注出处；无法定位证据的验收项显式标注「未定位到证据」。
> 撰写：wt775（2026-09-28，基线 main@ed072fd2）。方法：卡面（v3/07_tasks/cards/S-0*.md）+ wt759 报告逐卡 SHA → `git log -1` 全部 8 个交付 SHA 重验在主干 → 关键代码开文件亲证（community_context_boundary 528 行 import 面/两证据表/community_sync worker/guest_seed 演示群标记）→ 测试逐文件计数 → v3-output/WT760-S01 REPORT 全读 + WT763 独立审查 receipt 抽读 + WT307/WT312/WT314 报告抽读 → 台账 FIX-495 逐行复核。**未轻信任何台账/报告结论性文字。**

---

## S.0 线级概览

S 线把社群从「公共 feed 社交产品」收敛为「围绕 Goal outcome 的小队协作」，并立起群上下文隐私红线。5/5 全部 done（tasks.json + fleet 名单 + wt759 逐卡 SHA；S-01 另有 wt763 独立审查 APPROVE 销账，V3-COMPLETE-STATUS §3 已载）。

执行形态的显著特点（V4 设计者需要知道）：

1. **S 线是「真相先行」的样板线**：S-01（真相复测）排在线首且卡面明示「先确认 V2.5 当前 M-3/502 等是否仍存在，不直接重写」——其结论直接改写了后四卡的前提（实时面已健康、CQRS 投影是闲置面，不需要救援式重写）。
2. **S-01 的两段式交付**：段一（wt361，09-23）headless 读模审计实锤「CQRS 双向死链」；live 段（wt760，09-27）两真实账号经 :8080 网关全环实测；wt763 独立审查 APPROVE（独立复跑 26 passed+五面探针重放+驱动脚本静态审查）后销账。**一段 headless+一段 live+一段独立审查**是本线最高的证据密度。
3. **「红线先立、消费面后建」**：S-02 的 528 行守卫面在群 AI 面存在之前就交付并登记 orphan-by-design 豁免（rule_at_exceptions.md:39——B 线章已载，本章 §S.2-S-02 亲证复核）——守卫的「生产消费方=后续群 AI 面」。

---

## S.1 意图（卡面目标与验收）

五卡共性 Forbidden 条款（卡面原文，全线一致）：不得重建已存在的权威真源；不得用 mock/seed 冒充真实行为；不得只通过静态代码阅读宣称用户体验通过；不得弱化既有安全/幂等/隔离/审计守卫。

| 卡 | Risk/Resource/Reviewers | 卡面目标（一句话） | 卡面关键验收 |
|---|---|---|---|
| S-01 Community Realtime/Read-model 真相复测 | medium/HEAVY/1 | 先确认 V2.5 遗留疑项是否仍存在，不直接重写 | 当前状态有可重复 report；live 失败不 fallback 假 realtime |
| S-02 Community Context Privacy Boundary | critical/MEDIUM/2 | 群聊/小队绝不能自动访问私人 Memory/Profile | private memory leakage=0（两账户 adversarial）；群内 AI 说明它看到什么 |
| S-03 Squad/Sprint/Check-in 表面收敛 | medium/HEAVY/1 | 从公共 feed 转向围绕 Goal outcome 的小组协作 | 单人核心 journey 不受依赖；小组 journey 自解释；seed/demo group 明确标演示 |
| S-04 Artifact Feedback → Outcome/Evidence | medium/MEDIUM/1 | 同伴反馈变成可选择的 Goal evidence 而非社交孤岛 | GJ16 能从 check-in 回到 Goal trajectory；撤回后派生引用更新；feedback/ack 不自动成为 mastery |
| S-05 Reconnect/Retract/Two-account E2E | high/HEAVY/2 | 真实验证实时、权限、撤回、离线和跨用户隔离 | WS 真实通过；cross-user/private memory leak=0；duplicate check-in=0；失败态不冒充 live |

---

## S.2 实际交付逐卡

### S-01 · Realtime/Read-model 真相复测（「五面真相」——本卡是 V4 读社群面的第一入口）

**交付（两段+独立审查）**

| 段 | 主干 SHA | 内容 |
|---|---|---|
| 段一 headless | `02515b39`（wt361） | 读模审计：**gateway CQRS 社区读模投影双向死链实锤**（outbox.Insert 全仓零非测试调用方→cqrs:stream 零投递） |
| live 段 | `5e7a2443`（wt760，READY_FOR_REVIEW；源码零改动，交付=报告+证据+495 登记） | 两真实测试账号（wt760s01_a/b）经 :8080 网关 join/chat/checkin/reconnect 全环 90.5s 时间线全绿（evidence.jsonl 逐帧+可复跑驱动脚本 wt760_s01_live.py/followup.py） |
| 独立审查 | `51b9c659`（wt763） | **APPROVE**：独立复跑 sqlite security 12+e2e 14=26 passed、go cqrs/worker 5 包 ok、evidence.jsonl 75 行逐项对账一致、live 只读抽验（A 重登录同 uid、群/8 消息 nonce 全链、火堆 29）+ CQRS 五面探针重放全复现；no-mock-fallback 代码级核验（isDemoMode 默认 false+WS 失败 error/重连/终态）；3 轻微备注不阻塞 |

**五面逐面结论（v3-output/WT760-S01/report.md §2 亲读+关键点代码复核）**：

| 面 | 结论 | 本次复核锚点 |
|---|---|---|
| ① WS path | **健康**：群/个人双端点 5 次握手 24-65ms 全 OPEN；非成员 4003 闸+401 闸在位；**V2.5 快照 M-3（社群 WS 502）已消解** | report §2①② |
| ② Gateway 转发 | **健康**：WsAuthMiddleware→HandleCommunityWS（websocket_proxy.go:127 UUID 防穿越）反向代理；消息/typing/checkin 帧双向逐帧可达 | report §2② |
| ③ Projection | **闲置但健在**：XLEN=0、consumer group last-delivered-id 0-0（自建组从未投递）、pending=0、post:view:* 0 键、feed:global ZCARD=0；群聊/打卡实时**不经过**投影——走引擎进程内 ConnectionManager+Redis pub/sub 直达 | report §2③；backend/gateway/internal/worker/community_sync.go 在树亲证 |
| ④ Outbox | `event_outbox` 521 行全部 published（galaxy 321/memory 142/action 31/run 27），**community.post.* 0 行**——posts 写路径不产 outbox 行；网关 UnitOfWork 写入方仅 galaxy/task/user_preferences 三服务 | report §2④（galaxy CQRS 是活的、community CQRS 是死的——同仓对照） |
| ⑤ DLQ | XLEN=0 无死信；PEL 恒空——**461/469/481 三代耐久幂等修复在 community 流上零真实流量可锻炼**，正确性由单测承载（base_pel_redelivery_test.go 等三文件本卡点名重跑过） | report §2 尾段 |

**M-3 消解/引擎内实时/CQRS 闲置三点的 V4 读法**：①「实时是引擎内进程实时」=ConnectionManager 单进程广播+Redis pub/sub 个人通道——单引擎实例内成立；**多实例/跨进程扩 stride 时这套实时面是第一个要重设计的点**（群 WS 不注册 user_connections 表，nonce ACK 只在个人通道可达是设计语义非缺陷，wt760 followup 双向钉死）。②CQRS community 投影是「零生产者+零读取者」的完整闲置接线→ **V3-FIX-495 OPEN**（P3）。③live 失败路径无 mock 回退（mobile mock 仅 demo 开关门控、WS 失败走 error 态+调度重连、feed 断网回退带 fromCache/asOf 时点标记的诚实降级）——wt763 代码级核验在案。
**seed/mock 清单（卡面 Work 3）**：guest 登录播种 6 演示群+演示用户（friend 行共享）+种子痕迹（flame_level=15 非真实 earned）——**其中 6 个演示群无任何 demo 标记**（→ 本次登记 V3-FIX-506，§S.5）。

### S-02 · Community Context Privacy Boundary（critical，双审查）

**交付**：`83ed09ee`（wt375；4 文件 +1,092 行：守卫 528 行+测试 551 行+business_metrics 计量 12 行+豁免登记 1 行）。
**主干面亲证**：
- `backend/app/services/community_context_boundary.py` 528 行在树；**生产 import 面为零**（本次全仓 grep：仅 3 个测试文件 import——unit/test_community_context_privacy_boundary.py 16 test、security/test_q05_redteam_final.py、api/test_s05_community_reconnect_retract_two_account_e2e.py 复用）；orphan-by-design 豁免在 docs/aurora/rule_at_exceptions.md:39（B 线章登记处复核一致，移除条件=群 AI prompt/tool 面接入时）。
- 守卫语义（commit message 逐条亲证）：shared context allowlist 单一守卫面——群 prompt/tool 组装只收用户**主动分享进群**的 Goal/Action/Artifact（真源=既有 SharedResource 群分享行；词表外载体 seed/cognitive 族永不进群 AI 上下文）；纯函数滤芯（固定维度 identity→type→share→lifecycle+封闭 reason 词表冻结+Prometheus 逐维度计量 sparkle_community_group_context_rejections_total）；resolve_prompt_context/group_tool_context_permits 只读群 permission 面，fail-closed（非活跃成员/群不存在即拒、无 ctx 全拒 no_group_surface）；revoke 软删+分享者离群即失效（陈旧候选精确归因 share_revoked/sharer_left_group）；owner 绑定校验（伪造借道他人 share 行→owner_mismatch）+payload 七键形状冻结（零私人 memory/profile 字段）。
- 证据：红测 base 78ff5538（ModuleNotFoundError 无守卫实证+私人 llm_context 面 surface-blind 对照）→绿（定向 16/16）；邻域回归 129+989 passed；冷 mypy 基线零漂移。
**「群内 AI 说明它看到什么」**：payload 形状冻结+语义提示文案的守卫侧承载在库；**群 AI 会话面本身不存在**（无群 AI prompt 组装生产方）——该验收项的完整兑现以 V4 群 AI 面接线为前提（这是豁免条款的「移除条件」本体）。

### S-03 · Squad/Sprint/Check-in 表面收敛

**交付（两波收口）**：`41d83f83`（wt307 v1）+ `83f599ff`（wt377 收口+四入口契约锁）。
**交付内容（WT307 REPORT 亲读+commit 双证）**：社群主屏 tab 从 [伙伴(默认), 动态, 群组] 重排为 **[群组协作(默认), 伙伴, 动态]**——公共 feed 让出核心位（FAB 随 feed 新索引）；新增 `_TodayCheckinSection`（我的群组今日打卡段：冲刺群排前、真源计数直显、复用群聊同款打卡对话框，回执「+N 火苗喂进群火堆」把 Flame 锚定群活跃）；孤儿组件 `SharedResourceCard` 接回产品面（fetchSharedResources/adoptResource 此前产线零调用方）；demo 模式顶部常驻 `_DemoModeBanner`（不可关闭）；BonfireWidget 包 Semantics（gdFlameSemantics：火苗代表群活跃度——「Flame 不与付费绑定」的后端 entitlement 守卫早已在 core/entitlement.py，mobile 全库 grep 零 flame→付费耦合）；mock 仓库 4 个 demo 群名追加「（演示）」后缀（l10n demoGroupSuffix）。
**验收「seed/demo group 明确标演示」的双面现状**：mobile demo-mode 组有标记（mock 仓库后缀+横幅）；**guest_seed_service 后端播种的 6 个真·访客可见演示群无任何标记**（本次开文件亲证：guest_seed_service.py:2815-2867 `_ensure_group(name="算法冲刺小队"...)` defaults 无 is_demo/marker 字段，models/community.py 无 is_demo 列；wt760 §5 同口径发现并指向「S-03 验收承接」——但 S-03 当时已销账，承接链断裂）→ V3-FIX-506。
**「单人核心 journey 不受依赖」**：单人群组外全功能可走（S-01 两账号走的就是纯社群路径；核心 GJ01-GJ08 均无社群依赖——B-01 CORE 15 项映射在案）。

### S-04 · Artifact Feedback → Outcome/Evidence

**交付（两波）**：`c026f0c1`（wt312 v1：新表 shared_resource_feedbacks + Alembic 迁移）+ `8656eaa9`（wt382：结构化证据+flywheel）。
**主干面亲证**：backend/app/models/community.py:574 `shared_resource_feedbacks` + :625 `community_outcome_evidence`（FK→shared_resource_feedbacks.id ondelete=CASCADE——撤回级联的 schema 层载体）两表在树。
**「feedback/ack 不自动成为 mastery」**：wt382 commit 语义——同伴反馈采纳才落**结构化 outcome evidence**（用户可选择采纳为 Goal evidence，走 evidence 族权重面），ack/like 本身不写 mastery；与 G-01 的 SELF_REPORT 单独通道原则同构（G-line 章互证）。
**「事件进入 flywheel」**：8656eaa9 明示 S-03 第 4 入径上加两块结构化不留断头路+flywheel 事件。
**测试**：backend/tests/api/test_s04_community_outcome_evidence.py 4 test + tests/test_s04_community_feedback_evidence.py 9 test（逐文件计数）。
**「撤回后派生引用更新」**：CASCADE FK 承载 schema 级；应用层撤回路径的显式测试未逐条定位（S-05 的 retract 谱系覆盖 retract 行为本身）。

### S-05 · Reconnect/Retract/Two-account E2E（high，双审查）

**交付（两轮）**：`911dbeb7`（wt383：**30 case 全谱 headless 真实验证+当场修 3 缺陷**）+ `64e6cdff`（wt396 轮 3 清扫 F5/F6/F7：里程碑位置 join 错位/离群 kick 无补偿/评估引擎事件通道污染——三项独立复核全 CONFIRMED 红绿修复）。
**主干面亲证**：backend/tests/api/test_s05_community_reconnect_retract_two_account_e2e.py **30 个 test**（逐文件计数，覆盖 reconnect/dup event/out-of-order/leave/revoke/block 谱系）+ security/test_q05_redteam_final.py 跨用户隔离对抗面复用。
**卡面「Android/Web/macOS applicable flows」**：headless 谱系承载；三端实机流未发生（无设备——U 线同款欠账，转出链缺口见 508）。
**「失败态不冒充 live」**：与 S-01 的 no-mock-fallback 代码级核验同构（isDemoMode 默认 false+WS 失败终态）。
**「duplicate check-in=0」**：S-01 live 时间线双打卡 streak=1→count=2、12+17=29 火堆对账平（幂等/计数控）+wt383 谱系内 dup case。

---

## S.3 设计决定与取舍

1. **「先测真相再动刀」**：S-01 卡面明示不直接重写；结果是 M-3 免了一次救援重写、CQRS 闲置面从「疑项」变「实锤登记」（495）——后四卡的前提全部建立在实测上。V4 群面设计应从 S-01 报告出发而非从 V2.5 快照出发。
2. **红线先行、豁免显式**：S-02 在消费面（群 AI）存在前立守卫+登记 orphan-by-design 豁免（带移除条件）——把「V4 接线义务」写成机器可查的登记而非口头承诺。这是「验收模型前置」的变体：守卫的红测（16/16）在无生产流量时就跑通。
3. **实时面复用引擎进程内基建**：群聊/打卡实时走 ConnectionManager+pub/sub，不迁 CQRS——「不重建真源」+「闲置接线如实登记」的组合取舍。代价是 495 的悬置与多实例扩展的未决。
4. **Flame 语义主动去货币化**：S-03 把火焰显式锚定为群活跃（Semantics 文案+回执话术），配合既有 entitlement 守卫（flame_level 永久禁作权益判据）——「付费绑定」从产品语言层和后端判据层双向封死。
5. **两段真实账号+nonce 逐帧对账**：S-01/wt760 的 live 方法论（guest 账号明标测试身份、步进≥1.2s、逐帧 JSONL、A/B 交叉读侧核验、火堆总数对账）是可复用的社群面验收 harness——wt763 独立审查能逐项重放正因证据链是机器可读的。
6. **收口而非铺开**：S-03/S-04/S-05 都经历「v1（wt307/312/383）→收口轮（wt377/382/396）」两波——v1 交付主体，收口轮修 v1 真红面（如 wt377 亲证 v1 改 TabBarView children 漏改 tabController.length 的真缺陷）+ 补契约锁。

---

## S.4 残差与 V4 注意点（汇总）

1. **FIX-495 的裁量建议素材（主会话待产品裁决项，本章供给料）**：
   - **事实面**：community post CQRS 投影=完整闲置接线（零生产者+零消费者+零流量）；461/469/481 耐久幂等链在 community 流零真实流量锻炼（单测承载）；而 posts/feed 功能本身经引擎 API+网关纯代理正常服务（S-01 live 全绿）。
   - **留档接线（keep）的论据**：V4 若做 feed 规模化/多实例（ConnectionManager 跨进程失效时投影是现成的读扩展路径）；galaxy 流（321 行）证明同构管线在真流量下工作；拆除后再建成本高于维护。
   - **拆除（remove）的论据**：零流量管线自带腐烂风险（461/469/481 的修复在真实流量为零时回归锚只剩单测）；「死接线」对 V4 新人是误导性复杂度；wt639 审计的 ORPHAN 判据（入口可达/下游消费/测试在测/宣称 vs 实现）四问全不过。
   - **折中建议**：post-RC（10/7 后）裁决；若 V4 群 AI/feed 面立项则接线并补集成测试，否则按 FIX-341 判例走「撤面+AT 豁免+重建须三件齐上」的 by-design 收口。
2. **群 AI 面的接线义务**：community_context_boundary 豁免（rule_at_exceptions.md:39）的移除条件=群 AI prompt/tool 面接入。V4 做群 AI 时第一件事就是接它（fail-closed 语义+七键 payload+Prometheus 计量全部现成），否则隐私宣称持续大于保障面。
3. **实时面的多实例边界**：引擎内 ConnectionManager 是单实例语义；V4 若横向扩引擎，群广播/个人通道/ACK 路由需重设计（495 的投影是候选承载之一——与 1 的裁决联动）。
4. **演示群标记（506）**：guest 可见的 6 个种子群无 demo 标记；V4 若动 guest/演示面，随 S-03 语义（横幅+后缀）补齐后端标记。
5. **461/469/481 的流量真空**：不只 community——任何 CQRS 流的真实故障注入演练（Q-07 chaos 终验未做）之前，耐久链的运行级置信度都来自单测。V4 排期 chaos 面时应把 community 流的故障注入纳入（若 495 裁决为保留）。
6. **S-04 的应用层撤回测试**：CASCADE FK 承载了 schema 级撤回；「撤回后派生引用更新」的显式应用层测试未逐条定位——V4 若扩展 evidence 派生面（引用/快照/聚合），补一条端到端 retract 测试。

---

## S.5 本次审查登记

- **V3-FIX-506**（本次新登记，台账行已入本 worktree commit）：S-03 验收「seed/demo group 明确标演示」对 guest_seed_service 后端播种的 6 个演示群未兑现——`_ensure_group` defaults 无任何 demo 标记字段（guest_seed_service.py:2815-2867），models/community.py 无 is_demo 列；wt760（09-27）发现后注记「→S-03 验收承接（S-03.md:27）」，但 S-03 已于 wt377（09-25）销账——**承接链断裂：指向一张已 done 的卡**。mobile 侧 demo-mode 组有标记（mock 仓库「（演示）」后缀+常驻横幅），真实访客经 guest 登录看到的种子群反而无标记。修法方向：种子群名追加演示后缀或加 is_demo 列+读面透传（与 O1 种子计划「示例」来源标记同构）。
- 复核过但**不构成新发现**的三项：①CQRS 闲置面（已登记 FIX-495 OPEN，本章 §S.4-1 供裁量素材）；②community_context_boundary 零生产 import（orphan-by-design 豁免在案 rule_at_exceptions.md:39，属已知设计态）；③wt763 receipt 三轻微备注（live_run1_full.log 指针失实未入库/握手计数口径/members 装饰性断言）——均不阻塞且已由 receipt 在案，不重复登记。
- 号占用核验：500-504 已占用；505 空闲备而不用；本线取 506（grep 全仓 `V3-FIX-506` 零命中后占用）。507/508 见 U-line.md §U.5。
