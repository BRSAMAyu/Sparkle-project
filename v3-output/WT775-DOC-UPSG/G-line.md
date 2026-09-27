# G 线（Galaxy 5 卡）深挖章节 —— V4 交接文档素材（wt775）

> 本文是 `v3/V3-COMPLETE-STATUS-FOR-V4.md` §4「各线深度状态」G 线章节的深挖草稿。
> 证据纪律：只写三源证据（git 主干 SHA / 独立审查 receipt / 运行级实测）支撑的事实；逐条标注出处；无法定位证据的验收项显式标注「未定位到证据」。
> 撰写：wt775（2026-09-28，基线 main@ed072fd2）。方法：卡面（v3/07_tasks/cards/G-0*.md）+ wt759 报告逐卡 SHA → `git log -1` 全部 9 个交付 SHA 重验在主干 → 关键代码开文件亲证（mastery_evidence.py 603 行/stats_service.spark_node/task_service 完成链/outcome_absorption_service/consistency_service/age_client 全部消费方）→ 测试逐文件计数 → v3-output/WT314-G04、WT395-G05-GALAXY、WT307/WT312 报告抽读 → AGE 使用面全仓追踪。**未轻信任何台账/报告结论性文字。**

---

## G.0 线级概览

G 线把星图从「学习分钟堆出来的视觉锤」升级为「证据驱动的成长地图」，并保证删除/纠正后图谱不残留错误派生。5/5 全部 done（tasks.json + fleet 名单 + wt759 逐卡 SHA）。

**产品主张核心的亲证结论（V4 必读）——「星图数据源是学习分钟还是真证据？」答案是：三条写入路径并存，证据化是真实的但不是唯一的**：

| 写入路径 | 触发 | 走哪条数学 | 主干证据 |
|---|---|---|---|
| ① 任务完成 spark（主流量） | TaskService.complete（task_service.py:780/803 两处）与 subtask 完成（subtasks.py:133） | **legacy 时间公式，封顶 LEGACY_TIME_MASTERY_CAP=40**（mastery_evidence.py:119）——调用**不带 outcome 参数**，study_minutes=resolve_spark_study_minutes（只认真实时长缺省 0，不再 estimated 回填，task_completion_evidence.py:157-161） | spark_node 分支亲证（stats_service.py:163-172）：`if outcome is not None: 融合 else: capped_legacy_mastery` |
| ② 显式 outcome 证据 | spark API 请求体带 outcome（galaxy.py:437-445：EvidenceObservation(type/value/confidence)） | **Kalman 融合**（fuse_mastery，先验=重放该节点证据账本） | stats_service.py:166-170 亲证 |
| ③ outcome.recorded 吸收（G-02） | X 线 outcome 账本事件→OutcomeAbsorptionConsumer（main.py:509-512 启动）→ absorb（幂等标记+TASK_OUTCOME 权重 0.6 融合） | **Kalman 融合** | outcome_absorption_service.py:202-207 亲证 |

即：**「同样 30 分钟不同 outcome 不同 mastery」的验收在证据路径上成立（卡面核心主张真实兑现），但日常任务完成的主流量仍走封顶 40 的时间公式**——用户可见的星图亮度是三路混合结果。这不是缺陷（封顶恰恰是「无 evidence 不凭空精通」验收的实现），但 V4 若宣称「星图=证据地图」，主流量（任务完成）与证据路径（outcome.recorded）的融合比例是必须显式设计的产品参数。

其他执行形态特点：
1. **G-04 是「同一家族缺口第二遍清点」的样板**：70eb9b68（G-02 的缓存失效）修了吸收链缺口；wt314 用同一镜头清点出 6 个同族缺口（删错题/删草稿节点/任务硬删零清理零失效+三个异步事件写不失效）一次修完（consistency_service 新模块）——「修一个缺口时把同族镜头过一遍」是 V3 后期效率最高的修法（与 FIX-489/490 孤儿清查同思路）。
2. **G-05 用一次性库做规模终验**：wt395 在 sparkle_db 容器内新建 `wt395_g05` 库（alembic 迁移到当时 head，跑完自动清理）、Redis 走 db5、真实 DashScope embedding——「真数据规模、隔离库、可复跑」的性能证据形态。

---

## G.1 意图（卡面目标与验收）

五卡共性 Forbidden 条款（卡面原文，全线一致）：不得重建已存在的权威真源；不得用 mock/seed 冒充真实行为；不得只通过静态代码阅读宣称用户体验通过；不得弱化既有安全/幂等/隔离/审计守卫。

| 卡 | Risk/Resource/Reviewers | 卡面目标（一句话） | 卡面关键验收 |
|---|---|---|---|
| G-01 Mastery 从「学习分钟」升级 Evidence-aware | medium/MEDIUM/1 | 节点亮度代表有证据的成长，而非时间即掌握 | 同样 30 分钟不同 outcome 不产生相同 mastery；公式透明可测；无 evidence 不凭空精通；旧数据标 legacy estimate |
| G-02 Artifact/Outcome → Galaxy/Trajectory 接线 | medium/MEDIUM/1 | 真实成果自动成为图谱证据与用户可见成长 | GJ05/GJ08 图谱变化可解释可追 source；不重复点亮；失败/撤销 outcome 正确处理 |
| G-03 Galaxy Goal-focused UX 重设计 | medium/HEAVY/1 | 保留视觉锤同时让图可读、可行动 | 新用户能解释星图表达什么；5 screenshots A/B=0；缩放/点击跨端稳定 |
| G-04 对 Correction/Delete/Version 的一致性 | high/MEDIUM/2 | 删除材料/纠正 evidence 后图谱不保留错误派生结论 | 删除后相关 edge/node state 正确；不跨用户泄露；有回归测试与事件重放 |
| G-05 性能/手势/视觉终验 | medium/HEAVY/1 | 真实数据规模下视觉资产不变成卡顿/演示风险 | 无 A/B 视觉问题；核心操作无 overlap；性能达平台可用基线，异常 graceful；语义搜索走真实 embedding |

---

## G.2 实际交付逐卡

### G-01 · Evidence-aware Mastery（Kalman 六证据型）

**交付**：`19b467ff`（Kalman 6 证据型融合+self_report 隔离通道+legacy 封顶）。
**主干面亲证（mastery_evidence.py 603 行，纯函数零 DB/Redis 依赖——「公式透明可测」的架构载体）**：
- 六证据型封闭词表：QUIZ 1.0 / TASK_OUTCOME 0.6 / CHAT_SIGNAL 0.35 / MATERIAL_REF 0.2 / SELF_REPORT **不参与融合**（单独通道）/ TIME_ON_TASK **0 权重**（仅活动痕迹）——EVIDENCE_WEIGHTS 字典亲证。
- 融合数学=M 链证据引擎同构的 1D Kalman（confidence→观测方差，gain 决定每步移动量），每步暴露 prior/observation/kalman_gain/posterior。
- **审计三分类**（V3-FIX-299 信任边界，MasteryEffectKind）：`evidence`（重放融合）/`set_point`（exam-sprint 诊断/惩罚的绝对赋值）/`projection`（shadow/trace 行，重放跳过）——**服务端定性写死，客户端伪造 reason 词表拿不到任何重放效果**；unknown/NULL fail-closed 归 projection（「宁丢效果不注入数值」）。三条客户端可控入口（/sync/mastery、/nodes/{id}/mastery、gRPC UpdateNodeMastery）默认 projection——galaxy_service.py:3170 docstring 亲证。
- legacy 数据：`legacy_estimate` 标记保留旧值，真证据到位后清除（模块 docstring 属性 5）。
**测试**：backend/tests/services/galaxy/test_mastery_evidence.py **36 test** + test_mastery_effect_kind_replay.py **18 test**（重放分类面）+ test_stats_service.py 14（逐文件计数）。
**验收对照**：「同样 30 分钟不同 outcome 不产生相同 mastery」=证据路径成立（§G.0 表）；「无 evidence 不凭空精通」=TIME_ON_TASK 0 权重+legacy 封顶 40 双机制；「公式透明可测」=纯函数模块+全步骤暴露。**「兼容旧数据并标 legacy estimate」在既有节点上的存量回填状态**：读侧按 audit 行 effect_kind 重放分类（classify_audit_reason），未发现全量回填迁移——旧节点在无新证据时保持 legacy 口径，符合「标 legacy」而非「洗白」。

### G-02 · Outcome → Galaxy 接线

**交付（三段）**：`aced25a2`（主接线）+ `7bd6ade3`（wt381 不重复点亮：同 outcome 重放直接跳过融合——absorbed_outcomes 快照键 O(1) 极性翻转）+ `70eb9b68`（NBP-4：outcome 吸收后失效读模图缓存——吸收链失效缺口首修）。
**主干面亲证**：outcome_absorption_service.py——消费 `outcome.recorded`（OUTCOME_RECORDED_EVENT，X 线 outcome_capture_service 同源）；幂等标记 `outcome=<outc_id>` 与 X-08 账本幂等 id 同源（append-only、无界、重放安全）；**同因合并**（任务完成 outcome 与 agent run receipt outcome 是同一逻辑 outcome 的两个事件面，D-02 契约）；极性翻转在上游 task_service._VALID_TRANSITIONS 收口；OUTCOME_EVIDENCE_AUDIT_REASON=TASK_OUTCOME 权重 0.6 融合；OUTCOME_PROVENANCE_SOURCE_TYPE="outcome_ledger" 落快照溯源。
**「图谱变化可解释可追 source」**：mastery_audit_log（reason/effect_kind/request_id/revision）+node_status 快照 provenance source_type 双承载；GJ05/GJ08 的用户可见解释经 G-03 节点详情 why/来源面。
**「失败/撤销 outcome 正确处理」**：上游极性翻转约束+吸收面幂等键极性标记（wt381）——**「撤销后 mastery 回滚」的显式逆融合未定位到**（吸收面按「不再重复点亮+翻转不再点亮」处理；负向 Kalman 观测语义在 fuse_mastery 支持负 delta，但 outcome 撤销→自动回滚融合效果的端到端路径未在代码中定位，见 §G.4-3）。
**测试**：test_outcome_absorption.py **16 test** + test_outcome_read_model_visibility.py 5 + api/test_task_complete_galaxy_outbox.py 4。

### G-03 · Goal-focused UX 重设计

**交付**：`f2fb8c2b`（wt305）——focus-follows-camera 锚（resolveNearestNodeId 纯函数：默认聚焦当前 Goal 子图，相机移动即跟随）+ Review now/controls 重叠修复+空态合理化+粒子/光效降干扰。
**mobile 面现状（本次开文件亲证）**：`mobile/lib/features/galaxy/data/services/` 12 个服务件（force_engine/layout_engine/render_engine/spatial_index/gesture_recognizer/galaxy_accessibility_service/performance_monitor/predictive_viewport_preloader 等）+ repositories 三件（galaxy/enhanced/draft）——视觉锤工程面完整；数据源=ApiEndpoints.galaxyGraph/galaxyEvents/galaxyNodeDetail/galaxySearch 等（galaxy_repository.dart:31-275 亲证），mastery 显示来自 relational 读面（user_node_status），非 AGE。
**「新用户能解释星图表达什么」**：G-03 的 why/来源/next step 节点详情+G-01 的 evidence_badge 面承载；「5 screenshots A/B=0」以 B-04 golden 链 android 批口径（U 线同款欠账：macOS ENV-1 豁免、真机批未采集——508 同族）。
**「缩放/点击跨端稳定」**：headless 交互正确性由 G-05 的 7/7 flutter 交互测试承载（跨端真机未发生）。

### G-04 · Correction/Delete/Version 一致性（high，双审查）

**交付（三段）**：`05155fff`（wt314 六缺口清零）+ `0d7cda55`（wt718 验收补强：FIX-431 跨用户隔离收口）+ `6656df34`（wt718 收账：tasks.json 置 done）。
**六缺口（WT314 REPORT 亲读，逐条 file:line 在 base 2421a04f 上定位）**：
- A1 delete_error 软删零清理：溯源行悬空引用已删错题+`signal:weak_at` 弱点标记不摘除→**学习状态 WEAK 复活**（schemas/galaxy.py:511 以该标记判 WEAK）+读面失效缺失；
- A2 delete_draft_node 零失效：被删节点在星图读面活到 TTL 600s（字面残影节点）；
- A3 TaskService.delete 硬删零失效；
- B1/B2/B3 三个异步事件写（error_created/task_completed/mastery_updated）不失效——B3 时序性最差：在 update_node_mastery 失效**之后**改边强/标记，读面以旧值回填存活到 TTL（失效被后写穿越）。
**修法**：新模块 consistency_service（242 行）：provenance pruning 带节点定界+copy discipline（剪溯源不复活灯亮——红测实证）、弱点从存活错题重算、canonical invalidation；Correction/Version 自洽以 audit 行幂等门承载。
**跨用户隔离（FIX-431，FIXED@e824a39f）**：recompute_weak_signals 的证据判据从「挂全局 keyword 的错题」改为按节点全量存活错题面——双用户共享知识节点（KnowledgeNode 全局行、keywords 全员共读）时，他用户的错题不再影响本用户弱点标记（ledger 431 行+0d7cda55 commit 亲证）。
**测试**：test_delete_correction_consistency.py **12 test** + test_f16_galaxy_weak_node_injection.py 11 + test_galaxy_concurrency.py 3 + test_error_mastery_idempotency.py 8 + integration/test_error_book_galaxy_mastery_sync.py 21（「避免全图重建昂贵路径」=pruning 定界+弱点重算局部化）。

### G-05 · 性能/手势/视觉终验

**交付**：`47898b9f`（wt395）——**33/35 判定 PASS，2 FAIL 如实保留**；一次性库 wt395_g05+Redis db5+真实 DashScope embedding。
**规模梯度（50/500/5000 真实 ORM 行，n≥30/操作，REPORT 表亲读）**：图取数冷缓存 p50 12.1/57.2/681.7ms；user_stats 恒 2-4ms；node_detail(gRPC) 恒 3-7ms err=0；语义搜索（真 embedding）域内 top1 命中 0.6（阈值边界，跨批 0.6~1.0 波动如实入档）+域外零命中 1.0。**2 FAIL=5000 档 p95 尾部**（热缓存 823.8ms 超 3%/学习路径 1141.2ms），根因=30 样本中 1-2 次 >1s 环境级停顿（离群 far=2/30 同签名、p50 仅 25.8ms），非算法缺陷。
**恢复风暴（5000 档 16 并发×5 轮）**：断线重连冷缓存 p50 **10317ms→401.7ms**（singleflight 修后，max/单发冷中位=1.41×）；CRDT 并发首连 6/16 丢单→**16/16 并入**；混合风暴 p50=365ms 零错误。
**5 处产品修复（全部红测先行+回归锁在库）**：①cache.py @cached singleflight（同 key in-flight 合并，异常不粘/异 key 不合并，test_g05_cached_singleflight.py 3 用例）；②galaxy_grpc 会话 get-or-create 原子化（并发首连丢单修复）；③GetLearningPath BFS parent-map 重构；④CRDT 快照二进制安全客户端（decode_responses=False，否则引擎重启后首台重连 restore 必败）；⑤retrieval_service 两处（embedding 故障显式降级——REST /galaxy/search 此前在供应商故障时 500；keyword_search jsonpath 显式 cast——asyncpg 类型化参数 UndefinedFunctionError，psql 字面量隐式转换掩盖的生产必炸面）。
**「性能达平台可用基线，异常 graceful」**：viewport 800 上限精确生效、LOD zoom<0.5 三档收窄、向量不可用→熔断+空返回+keyword 兜底、BFS 有界 MAX_VISITED=500 远对 path_found=False 诚实返回。真机截图/FPS 段转 HUMAN_INBOX（自带 WT395-G05-GALAXY/HUMAN_INBOX_G05_VISUAL.md 清单——中央收件箱未收编，508 同族）。
**Flutter 交互测试**：mobile/test/features/galaxy/unit/g05_galaxy_interaction_scale_test.dart 7/7 绿；galaxy 全域 flutter 测试 31 文件（find 计数）。

---

## G.3 设计决定与取舍

1. **「封顶」而非「清零」legacy 时间路径**：保留 spark_node 时间公式但 cap 40——兼容既有用户数据与主流量（任务完成必然触发 spark），同时兑现「无 evidence 不凭空精通」。代价是「星图=证据地图」的产品宣称打了折扣（§G.0 主流量事实）；收益是迁移零风险。V4 若要强化证据主张，路径是给任务完成链接 outcome 证据（completion evidence 分型函数 expected_evidence_kinds 已在 task_completion_evidence.py:169 就绪）而非改公式。
2. **信任边界写在写入口而非读出口**：FIX-299 把 effect_kind 定性放在 INSERT 点（服务端显式定性），重放按列分支而非猜 reason 字符串——客户端可控入口默认 projection。这把「伪造 mastery」从读侧过滤问题降维成「写侧根本没有效果」问题。
3. **同因合并的幂等设计**：任务完成 outcome 与 agent run receipt outcome 是同一逻辑 outcome 的两个事件面（D-02）——吸收面用账本幂等 id 同源标记解决「不重复点亮」，而非在事件面去重。V4 做任何「一个事实多个事件投影」时这是现成范式。
4. **失效是写路径的一部分**：70eb9b68（吸收后失效）→wt314（六缺口 canonical invalidation）确立「每个异步写路径自带失效」的纪律；B3 缺口（失效被后写穿越）说明失效顺序必须跟随后写顺序而非先于。
5. **性能证据用一次性库+真实依赖**：wt395 不在演示库跑压测（零污染），也不 mock embedding（真实 DashScope）——「真数据规模」与「隔离可复跑」同时成立。
6. **视觉锤的令牌豁免显式化**：galaxy 零 context.typo 采用是 E1 冻结豁免预算内的登记态（U 线 wt676 矩阵亲证）——视觉锤面不追令牌统一，把裁决权留给视觉 owner。V4 若动 galaxy 视觉，先解 E1 豁免再动代码。

---

## G.4 残差与 V4 注意点（汇总）

1. **AGE 图查询的实际使用面（专项结论）**：**Galaxy 星图本体不存 AGE**——knowledge_nodes/node_relations/user_node_status/study_records 全是关系表（models/galaxy.py `__tablename__` 逐一亲证），移动端星图读 relational 读面（@cached 600s+shield 10s）。AGE（apache-age，graph `sparkle_galaxy`）的真实使用面=**两处**：①GraphRAG 检索（orchestration/graph_rag.py:1928/2114/2519 三段真 Cypher：实体邻域/用户-知识关系/路径），由 chat 编排管线活调用（orchestrator.py:2020 GraphRAGRetriever，带 timeout 与全路径异常降级——AGE 不可达时回落实体抽取/RRF 序，且 mastery rerank 反向消费 galaxy_service 的掌握度分：G 线与 chat 检索的真实耦合点）；②graph_sync_worker（main.py:585 启动，消费 stream:graph_sync 写 AGE）。**但 stream:graph_sync 的唯一生产者类 graph_knowledge_service 已是 orphan-by-design**（rule_at_exceptions.md:41：唯一消费方 graph_monitor router 随 FIX-341 撤面删除，wt646 登记；预留消费方=后续 GraphRAG 可视化/运维面）——即 **AGE 写侧镜像当前零生产流量，AGE 里的图数据新鲜度无保障**；GraphRAG 读的是「上次同步时的 AGE 态+关系表回退」。V4 决策点：GraphRAG 要吃「实时星图」就必须接写侧（或改 GraphRAG 直接查关系表）；否则应诚实把 AGE 定位为检索辅助索引。
2. **主流量证据化是 V4 的最大产品杠杆**：任务完成链（最频繁的写入）不带 outcome（§G.0①）；expected_evidence_kinds/completion evidence 分型已在（X-01 词表复用）——把「任务完成的证据分型」接进 spark/outcome 链是让星图真变「证据地图」的最低成本路径，且 G-01/G-02 的数学与幂等面全部现成。
3. **outcome 撤销→已吸收效果的回滚未闭环**：吸收面按幂等+上游极性约束处理「不重复点亮/翻转不再点亮」，但「撤销一个已吸收的 outcome →回退它对 mastery 的 Kalman 贡献」的端到端路径未定位到代码或测试（G-02 卡面「失败/撤销 outcome 正确处理」的部分兑现——失败面成立，撤销回滚面未证）。S-04 的 evidence 撤回（CASCADE）同样只保 schema 级。V4 若宣称「图谱可纠正」，这是显式缺口。
4. **5000 档两个 p95 FAIL 未复验**：根因归因环境级停顿（同签名离群）且 p50 良好，如实保留 FAIL；V4 性能基线应复跑 wt395 同构脚本确认。
5. **弱信号/WEAK 判据的跨用户语义**：FIX-431 收口后按「节点全量存活错题面」判——共享节点上的弱点标记语义（他用户错题驱动我方 WEAK 的产品合理性）是 V4 可以重新审视的产品参数（当前实现是按用户过滤后的节点全量，已防跨用户泄露）。
6. **G-03/G-05 的真机段**：跨端缩放/点击稳定与真机 FPS 截图未采集（清单就绪：G05 自带 HUMAN_INBOX_G05_VISUAL.md）——与 U 线真机欠账同批解决。

---

## G.5 本次审查登记

- 本次 G 线深挖**无新缺陷登记**。复核过但不构成新发现的三项：①AGE 写侧镜像零生产流量（graph_knowledge_service orphan-by-design 豁免在 rule_at_exceptions.md:41 在案、带移除条件与退役裁决条款——属已知设计态，本章 §G.4-1 已作为 V4 决策点展开）；②主流量走 legacy 封顶路径（§G.0 表，是验收「无 evidence 不凭空精通」的实现手段而非违背，产品宣称折扣已如实写入 §G.0/§G.4-2）；③G-05 两个 5000 档 p95 FAIL（wt395 如实保留并归因，属已登记运行态）。
- 交叉登记：G 线相关的真机段转出未入中央 HUMAN_INBOX 已并入 U 线登记的 **V3-FIX-511**（G05 自带 WT395-G05-GALAXY/HUMAN_INBOX_G05_VISUAL.md 为证据锚之一）；号段使用全景见 U-line.md §U.5（507/508）与 S-line.md §S.5（506）。
- 号占用核验：500-504 已占用；505 空闲备而不用；本线未占用新号。
