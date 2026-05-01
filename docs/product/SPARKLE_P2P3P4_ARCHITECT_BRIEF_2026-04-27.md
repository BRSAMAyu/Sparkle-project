# Signal-to-Action Spine — 架构师裁定书

> **日期**: 2026-04-27
> **状态**: 等待架构师裁定
> **当前测试**: 628/628 通过
> **代码规模**: 42 信号模块 / 12,018 行 / 127 类 / 322 公开方法

---

## 一、现状总结

### 已完成

| 层级 | 完成度 | 关键产出 |
|------|--------|---------|
| P0 (10 项) | 10/10 ✅ | 8 层架构全通，FirstMinuteSnapshot → CausalTrace 完整链路 |
| P1 (6 项) | 6/6 ✅ | AchievementReinforcement, AuroraWake, ReplyOption, Recall, SelfModel, CommunitySignal |
| 数据对象 | 27 类 | ActionableSignal, StateEntry, 9 种 Directive, AuroraControlSignal, AuroraAgenda 等 |
| 信号排序 | 10 维 | goal_impact → privacy_sensitivity, 10 条冲突规则, Iron Law 合规 |
| 策略裁决 | 13 state_key | 固定规则表, risk_level(4级), which_directives(9类) |
| 学习层 | 完整 | PolicyExperiment, StrategyBelief, SkillEntry, SourceEffectiveness, SelfModel |
| E2E 验收 | 12 场景 | 考试冲刺 7 天全链路 + 退化模式 + 社群 + 疲劳 |
| 生产连接 | 已接线 | orchestrator_production.py 实际消费 ResponseDirective/RetrievalDirective/Chronicle/Fatigue |

### 不存在的（需要专家裁定再做）

P2/P3/P4 在 Final Spec Section 30 只有一段文字清单，没有 P0/P1 级别的详细任务书。

---

## 二、Final Spec P2 清单 vs 代码现状

| P2 项目 | Spec 原文 | 代码现状 | 差距 | 需要裁定 |
|---------|----------|---------|------|---------|
| **完整关系模型** | Section 4.2: Aurora 维护 relationship_stance, open_questions, self_correction | `relationship_model.py` 存在(219行)，有 RelationshipModel + RelationshipStance | 模型结构在，但只有静态姿态，没有动态演化逻辑（信任度变化、交互风格自适应、边界协商） | **Q1**: 关系模型需要多复杂？是简单 FSM 还是连续状态？ |
| **长期个性化 policy learning** | Section 20/23: SparkleSelfModel 建模自己的策略有效性 | `self_model.py`(303行), `learning_base.py`(243行), `policy_experiments.py`(279行) 均存在 | 基础框架在，但缺少：真正的长期学习循环（跨 sprint 保留信念）、置信度反证机制(Section 23.3)、自动策略晋升 | **Q2**: learning_base 的信念更新是纯贝叶斯还是混合规则+贝叶斯？跨 sprint 保留多久？ |
| **复杂 skill extraction** | Section 21: 3 级 skill (personal/cohort/system), 触发条件, 隐私规则 | `skill_extraction.py`(177行), `skill_lifecycle.py`(393行) 存在 | 有 inject/extract/recommend/deprecate 生命周期，但缺少：多条件触发（不只 outcome_positive）、skill 版本管理、cohort→system 晋升流程 | **Q3**: skill 晋升 personal→cohort→system 的门槛是什么？需要多少样本？ |
| **多策略实验系统** | Section 22: Decision Realization Score, 多指标验收 | `policy_experiments.py`(279行) 有 create/trial/promote | 当前只有 A/B shadow 模式，缺少：多变量实验、用户分群、自动结论+置信区间 | **Q4**: 实验系统是否需要统计显著性检验？还是规则阈值即可？ |
| **社群责任伙伴闭环** | Section 18.1: Commitment Loop — 提醒/见证/反馈 | `community_loops.py`(168行) 有 cohort/resource/partner 3 个循环 | Partner loop 有基本结构，但缺少：承诺→伙伴提醒→见证→外部观察候选→用户确认 的完整流程 | **Q5**: 伙伴信号是否能写入用户的 ActionableStatePacket？如果可以，scope 是什么？ |
| **完整 Full Aurora Core Session** | Section 9: AuroraAgenda + 多消息队列 + 打断恢复 | `core_session.py`(161行), types.py 有 AuroraAgenda/AuroraAgendaItem | 有议程管理，但缺少：真正驱动 LLM 的多轮校准对话、打断→恢复的 prompt 工程、SessionClosure | **Q6**: L3 Aurora Core Session 是直接用现有 LLM 服务，还是需要专门的 session prompt template？ |
| **多消息队列** | Section 9.2: InterruptionPolicy + ResumePolicy | AuroraAgenda 有 interruption_policy 字段 | 字段在，但没有消费逻辑——打断后如何暂停议程、回答用户问题、然后恢复 | **Q7**: 打断恢复是前端驱动（Flutter 发恢复信号）还是后端驱动（Spine 检测话题完成自动恢复）？ |
| **复杂 quota/cooldown** | Section 4.2: max_full_aurora_sessions_per_day | `aurora_wake.py`(174行) 有 AuroraWakeEligibility | 有基本 quota/cooldown，但缺少：分用户配额、配额恢复规则、紧急配额覆盖 | **Q8**: 配额是全局统一还是按用户等级/目标类型不同？ |
| **学习基地 Learning Base** | Section 21.3: System Skill / 平台级策略资产 | `learning_base.py`(243行) 有 Bayesian 更新 | 有冷启动和后验更新，但缺少：平台级 skill 市场、用户贡献 skill→验证→上架→推荐 | **Q9**: Learning Base 是后端服务还是需要前端 UI（浏览/搜索/采纳 skill）？ |

---

## 三、Final Spec 架构层 vs 代码覆盖率

| 层 | Spec 定义 | 代码 | 覆盖率 | 缺什么 |
|----|----------|------|--------|--------|
| Layer 1: RawEvent | 事件进入 spine | task_timeout_detector, exam_rescue_detector, mistake_signal, material_signal, external_integration | ~80% | 缺 calendar event→signal、achievement event→signal 的完整映射 |
| Layer 2: ActionableSignal | 事件→可能意味什么 | signal_ranker (10维排序) | ~90% | alternative_explanations 字段存在但从未填充 |
| Layer 3: Signal Ranking | 排序+冲突 | signal_ranker (10维+10冲突规则) | 95% | 动态权重调整（当前硬编码） |
| Layer 4: State Register | 只存影响决策的状态 | state_register, state_packet_builder | ~85% | 15 个 state_key 中只实现了 13 个；cognitive_load, affective_pressure 未实现 |
| Layer 5: Policy Engine | 固定规则裁决 | policy_engine (13 rules) | ~75% | 只有硬编码规则，缺少 Section 23 的置信度写入规则矩阵 |
| Layer 6: Directives | 9 类控制指令 | 9 种 Directive 类型全实现 | ~80% | ModelWriteDirective 的实际写入逻辑（写到哪个 DB 表？）未连接 |
| Layer 7: Audit | 验证输出是否满足 directive | directive_applier, DirectiveAuditor | ~90% | overridden_constraints 字段存在但下游很少填充 |
| Layer 8: Outcome | 因果归因 | outcome_recorder, causal_trace_store | ~70% | attribution 只有 3 种(inconclusive/effective/insufficient)，缺少 Section 8 的反事实分析 |

---

## 四、Aurora 能级调度 vs 代码现状

| 能级 | Spec 定义 | 代码 | 差距 |
|------|----------|------|------|
| **L0 Rule Sensor** | 不调用 LLM，每次事件运行 | task_timeout_detector, stale_state_guard 等 | ✅ 基本完整 |
| **L1 Light Aurora** | 每轮运行，小模型/规则 | policy_engine (规则) + aurora_wake (判断升级) | ⚠️ 缺少"每轮运行"的入口——当前只在 _run_signal_pipeline 触发 |
| **L2 Mid Aurora** | 非每轮，触发条件运行 | _run_signal_pipeline 内部逻辑 | ⚠️ 触发条件存在，但 L1→L2→L3 的显式分层不存在 |
| **L3 Full Aurora Core** | 稀缺、限时、交互式 | core_session.py 有骨架 | ❌ 没有真正的 L3 实现——缺 LLM session prompt、多轮对话管理、session 生命周期 |
| **L4 Async Deep Learning** | Celery/batch 后台 | learning_base, skill_extraction, policy_analytics | ⚠️ Celery 任务存在（5 个 beat schedule），但缺少跨天行为分析、错因聚类 |

---

## 五、需要专家裁定的 12 个决策点

### 架构决策（影响整体设计）

**D1. Aurora 能级调度实现策略**
- 选项 A: 在现有 SpineOrchestrator 内部分层（if/elif 判断 energy level）
- 选项 B: 拆成独立服务，L1/L2/L3 各自有入口和 prompt
- 选项 C: 保持现有结构，L3 作为 Aurora Runtime (runtime_v1) 的职责，Spine 只负责 L0-L2
- **影响**: 如果选 C，P2 的 "Full Aurora Core Session" 不在 Spine 代码范围内

**D2. 状态词汇表扩展**
- 当前 13 个 state_key，Spec 定义 15+ 个。是否需要实现全部？
- cognitive_load 和 affective_pressure 需要什么信号源？是否需要 LLM 推断？
- **影响**: 如果需要 LLM，这些不能是 L0，至少是 L1

**D3. ModelWriteDirective 的实际写入目标**
- Spec 说写入 user_state / sparkle_self_model / cognitive_profile
- 当前代码只记录 directive，没有实际执行写入
- 写到哪里？state_aggregator？独立的 Redis hash？PostgreSQL 表？
- **影响**: 决定了 Layer 6 的闭环是否真正完成

**D4. 关系模型的复杂度**
- 选项 A: 简单 FSM（5 种姿态，规则转换）
- 选项 B: 连续向量（信任度 0-1 + 亲密度 0-1 + 自主性偏好 0-1）
- **影响**: B 更符合 Full Vision 但复杂度显著增加

### 产品决策（影响 P2 范围）

**D5. P2 的优先级排序**
- 9 个 P2 项目，哪些是阻塞产品 Demo 的？
- 我的建议优先级：Learning Base > Policy Learning > Full Aurora Session > 关系模型 > 其他
- **需要确认**: 用户的下一个里程碑是什么？Demo? 内测? 公测?

**D6. Full Aurora Core Session 的交互模式**
- 选项 A: 前端驱动——Flutter 发送 "start_aurora_session"，后端返回 agenda items，前端逐个展示
- 选项 B: 后端驱动——LLM 自主决定是否进入 Core Session，通过 WebSocket 推送 agenda
- **影响**: 决定了前后端接口设计

**D7. Skill 晋升门槛**
- personal→cohort: 需要多少有效样本？3? 5? 10?
- cohort→system: 需要多少用户验证？是否需要人工审核？
- **影响**: 决定了 learning_base 和 skill_lifecycle 的晋升逻辑

**D8. 伙伴信号的隐私边界**
- 伙伴观察只能作为 external_observation_candidate + needs_user_confirmation？
- 还是允许低置信度自动写入（如"伙伴注意到你最近没完成"）？
- **影响**: 铁律 7 和隐私设计的边界

### 技术决策（影响实现路径）

**D9. 实验系统的统计方法**
- 选项 A: 简单规则——连续 3 次有效则晋升
- 选项 B: 贝叶斯 A/B——后验概率 P(有效|数据) > 0.8 则晋升
- 选项 C: 频率学派——p-value < 0.05 则晋升
- **影响**: policy_experiments.py 的 suggest_promotions 实现

**D10. 配额系统复杂度**
- 统一配额（每天 2 次 Full Aurora）？
- 按场景配额（考试冲刺 3 次，普通模式 1 次）？
- 是否需要配额恢复机制（如：如果上次 session 被证明有效，返还 1 次配额）？

**D11. 多消息队列的实现**
- 选项 A: AuroraAgenda 存 Redis，前端轮询 current_item()
- 选项 B: WebSocket 推送 agenda items，前端逐个确认
- 选项 C: 单次 LLM 调用返回多步，后端拆分存储
- **影响**: 前后端协议设计

**D12. 代码组织——P2 是继续在 app/signals/ 还是拆分？**
- 当前 42 个模块全在 app/signals/
- P2 加入 Learning Base, 完整 Core Session 等是否应该拆成 app/spine/ 和 app/aurora_core/？
- **影响**: 代码可维护性

---

## 六、我的建议

### 分 3 批推进

**Batch 1 (P2 核心，~5 天)**:
1. 补全 Layer 4 状态词汇（cognitive_load, affective_pressure）— 不需 LLM 的规则实现
2. ModelWriteDirective 实际写入连接（写到哪里等 D3 裁定）
3. Learning Base 完善（长期信念保留 + skill 晋升逻辑）
4. Policy Learning 升级（置信度反证 + 策略自动晋升）

**Batch 2 (P2 增强，~5 天)**:
5. 完整关系模型（等 D4 裁定复杂度）
6. 多策略实验系统升级（等 D9 裁定方法）
7. 伙伴闭环完善（等 D8 裁定隐私边界）
8. 配额系统升级（等 D10 裁定策略）

**Batch 3 (P3/P4，~5 天)**:
9. Full Aurora Core Session（等 D1/D6 裁定架构）
10. 多消息队列（等 D11 裁定协议）
11. L4 异步深度学习增强
12. 平台级 Learning Base 市场（等 D9 裁定）

### 如果专家不裁定，我默认的保守路线

按最简实现走：
- D1 选 A（内部 if/elif 分层）
- D3 选 Redis hash（state_aggregator 已有写入基础设施）
- D4 选 A（简单 FSM）
- D6 选 A（前端驱动）
- D7 选 5 次有效 / 10 次验证
- D8 选严格（必须用户确认）
- D9 选 A（简单规则）
- D10 选统一配额
- D11 选 A（Redis + 前端轮询）
- D12 选保持 app/signals/

---

*等待架构师裁定后开始 Batch 1 实现。*
