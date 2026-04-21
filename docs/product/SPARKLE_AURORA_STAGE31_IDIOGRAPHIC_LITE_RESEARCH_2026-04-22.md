# Stage 31: Idiographic Lite — 前置理论与代码探索报告

> **文档类型**: 研究报告（Dispatch Plan 前置参考）
> **阶段**: Aurora Stage 31
> **核心约束**: 仅允许关联分析 (association only)，不允许因果推断 (no causal claims)
> **日期**: 2026-04-22
> **状态**: Final (经批判性自审修订)

---

## 0. 关键事实修正

本报告初稿存在以下事实性错误或模糊之处，已在定稿中修正：

| 初稿问题 | 修正 |
|---------|------|
| 未区分 PersDyn 5 维与 Big Five 人格特质 | **PersDyn** = 行为动力学 (study_pace, completion_rate, engagement_level, mood_valence, plan_adherence)；**BigFive** = 人格特质 (openness, conscientiousness, extraversion, agreeableness, neuroticism)，位于 `user_insight_state.py`，两套独立系统 |
| 声称 14 天 × 5 维 = 70 数据点"充分" | **统计功效不足**：14 个观测点的 Spearman 相关需 \|r\| > 0.53 才达 p<0.05，大量真实关联会被遗漏。30 天窗口 (\|r\| > 0.36) 才是最低可行阈值 |
| 未讨论多重检验校正 | 10 维 C(10,2) = 45 对关联，每周重算，必须有 Benjamini-Hochberg FDR 校正 |
| 冷启动"群体先验"未具体化 | 需要明确定义先验来源和退化策略 |
| 实现量估算过于乐观 | 初稿"1 service + 2 schema + 1 PG 表"遗漏了测试、EventBus、API 暴露、Alembic 迁移 |
| 禁用词黑名单策略过于简单 | 中文中隐性因果暗示远比关键词匹配复杂 |

---

## 1. 方法论推荐

### 方法 A: 滚动窗口个体内关联矩阵 (Rolling Within-Person Correlation)

**核心思路**: 每个用户独立，在 **30-60 天**滑动窗口上计算 Spearman 偏相关矩阵，每周重算一次。30 天是最低可行阈值（Spearman |r| > 0.36 才达 p<0.05，可检测中等强度关联）；60 天窗口允许检测弱关联（|r| > 0.25）。当有效观测点 ≥ 40 时，可选启用 L1 正则化（graphical LASSO）做稀疏网络估计。

**为什么选 Spearman 而非 Pearson**: Sparkle 的行为数据（完成率、学习节奏、情绪效价）普遍非正态、含离群值（如考试周爆发），Spearman 的秩相关对此更鲁棒。

**为什么不用更复杂的方法**:

| 方法 | 排除理由 |
|------|---------|
| graphicalVAR (lag-1 VAR + LASSO) | 需 50-100+ 均匀间隔 EMA 观测点，Sparkle 用户活跃度不均匀，稀疏性严重 |
| DSEM (Bayesian Dynamic SEM) | 依赖 Mplus 商业软件，不适合生产部署 |
| GIMME (Group Iterative Multiple Model) | 需要 ≥10 个用户做群体层估计，违反"个体内独立"约束 |
| 深度学习时序模型 (GRU-ODE, Transformer) | 单用户数据量不足以训练，计算成本与 ROI 不匹配 |

### 方法 B: 贝叶斯在线变点检测 (BOCPD)

**核心思路**: 在 PersDyn 5 维 EMA 序列上运行独立的 per-user BOCPD 实例，维护 run-length posterior，实时检测行为模式突变。

**为什么选 BOCPD 而非 PELT**: BOCPD 是在线算法（每次新观测 O(1) 更新），天然适配用户持续产生数据的场景。PELT 是离线批处理，需要全量数据才能运行，更适合定期批量审计而非实时检测。两者可互补：BOCPD 实时 + PELT 月度审计验证。

**组合策略**: 方法 A 发现"哪些维度同步变化"，方法 B 发现"什么时候发生了突变"。当 BOCPD 检测到变点时，可触发关联矩阵的重算（跳过滑动窗口等待），实现"变点→重新学习关联"的自适应循环。

---

## 2. 统计功效与多重检验分析

### 2.1 样本量 vs 可检测效应量

| 窗口天数 | 有效观测点 (估) | 最小可检测 \|r\| (α=0.05) | 覆盖的关联强度 |
|----------|---------------|--------------------------|--------------|
| 14 天 | ~12 (扣除不活跃日) | > 0.58 | 仅强关联 |
| 30 天 | ~24 | > 0.40 | 中等偏强 |
| 45 天 | ~36 | > 0.33 | 中等 |
| 60 天 | ~48 | > 0.28 | 中等偏弱 |

**结论**: 默认窗口应为 **45 天**，兼顾检测灵敏度和时效性。14 天 PersDyn 现有窗口只适合单变量 EMA/stddev/slope（已在做），不适合多维关联分析。

### 2.2 多重检验校正

10 维关联矩阵产生 C(10,2) = 45 个关联对。不加校正时，α=0.05 下期望 2.25 个假阳性。

**强制策略**: Benjamini-Hochberg FDR 校正，目标 FDR = 0.10。只有通过 BH 校正的关联对才可呈现给用户。未通过校正的关联保留在内部日志中供未来分析，但标记为 `fdr_rejected=True`。

### 2.3 最小观测阈值

关联分析激活条件：
- 有效观测天数 ≥ **25 天**（扣除不活跃日后）
- 每个维度缺失率 < **30%**
- 不满足时，使用退化策略（见 §4.1 冷启动）

---

## 3. 数据充分性评估

### 3.1 现有数据源审计

| 数据源 | 文件 | 粒度 | 可用变量 | 充分性 |
|--------|------|------|---------|--------|
| PersDyn 吸引子 | `persdyn_attractor_service.py` | 日级 | 5 维 × (baseline, variability, recovery_rate) = 15 个连续值 | **充分** — 可直接做关联矩阵的 5 个核心维度 |
| BigFive 人格 | `user_insight_state.py` | 更新不频繁 | 5 维 × (value, confidence) | **低频** — 人格特质变化缓慢，不适合做日级关联，但可作为调节变量 |
| 任务数据 | Task 模型 | 事件级 | 完成率、超时比、反馈类别分布 | **充分** — 需聚合为日级指标 |
| 专注会话 | FocusSession | 事件级 | 时长、时段 | **充分** — 需聚合 |
| 学习记录 | StudyRecord | 事件级 | study_minutes | **充分** — 需聚合 |
| Source-State 7 维 | `source_state_encoder.py` | 每轮决策 | 离散枚举 | **有限** — 离散值，只能做列联表关联（Cramér's V），不能做 Spearman |
| 路由决策日志 | `route_history_service.py` | 事件级 | decision_type + outcome 4 类 | **有限** — 可作为结果变量，样本量取决于用户交互频率 |
| 行为信号 | `behavior_signal_collector.py` | 事件级 + 24h 冷却 | 6 类模式检测 | **低频** — 事件稀疏，不适合做连续关联，但可标记特殊时段 |
| JITAI 触发 | `jitai_trigger_service.py` | 事件级 | 10 模板 × 触发/跳过 | **有限** — 可作为"干预时机"的标记变量 |
| SRL Phase | `state_aggregator/schema.py` | 会话级 | current_phase + confidence | **待验证** — 依赖 Stage 29/30 实现质量 |

### 3.2 关联分析的候选维度 (10 维提案)

基于以上审计，建议关联矩阵使用以下 10 个日级连续变量：

```
核心行为 (PersDyn 5 维，已有):
  1. study_pace        — 日学习时长 (标准化为小时)
  2. completion_rate   — 7 天滚动任务完成率
  3. engagement_level  — 综合交互深度评分
  4. mood_valence      — 情绪效价 (当前从 reflection 推导，粒度粗)
  5. plan_adherence    — 计划偏离度

行为补充 (需新增聚合，但数据源已有):
  6. focus_duration    — 日专注总时长 (从 FocusSession 聚合)
  7. task_accuracy     — 任务时间预估偏差 (actual/estimated ratio, 从 Task 聚合)
  8. session_frequency — 日会话数 (从 StudyRecord 聚合)

元认知补充 (依赖 Stage 30):
  9. metacog_accuracy  — 元认知准确性 (预测 vs 实际偏差)
  10. strategy_flex    — 策略切换频率 (从路由日志推导)
```

### 3.3 关键数据缺口

1. **情绪粒度不足**: `mood_valence` 当前仅从 6 种 reflection category 推导（映射到 0.1-0.4），分辩力极低。**建议**: 增加 1-item 每日快速情绪自评（1-5 分，5 秒完成），作为 Stage 31 的前置 UI 改动。
2. **无主动 EMA 取样**: 当前全部依赖被动行为推断，没有每日固定时点的自评数据。文献共识是被动+主动融合显著优于纯被动。**建议**: 在 Stage 31 中引入最小化 EMA（1 题/天），通过 JITAI 触发时机投放。
3. **日级聚合精度**: 现有数据多在事件级（Task, FocusSession），需统一聚合为日级指标。这本身不是缺口，但需要在实现中定义清晰的聚合规则（如：当日无专注记录时 focus_duration = 0 还是 missing? 建议分活跃日/沉默日分别处理）。

---

## 4. 技术架构建议

### 4.1 独立服务: IdiographicAssociationService

**不扩展现有 BayesianLearner 的理由**: BayesianLearner 是离散 source→target 的 Beta 更新模型（`RouteStats(alpha, beta)`），专为路由决策设计。关联分析是连续变量的多维时序分析，数据结构和计算模型完全不同。强行扩展会导致职责混乱和 API 歧义。

### 4.2 架构图

```
┌──────────────────────────────────────────────────────────┐
│ IdiographicAssociationService (新建)                       │
│                                                          │
│  输入 ────────────────────────────────────────────────    │
│  │ PersDyn 5 维 EMA 序列 (从 PersDynAttractorService 读) │
│  │ Task/Focus/Study 日级聚合 (直接 DB 查询)              │
│  │ SRL Phase (条件性, Stage 30 依赖)                     │
│  │                                                      │
│  计算 ────────────────────────────────────────────────    │
│  │ RollingCorrelator: 45d 窗口 Spearman + BH 校正       │
│  │ BOCPD: per-dim per-user 在线变点检测                  │
│  │ EffectSizeGate: 仅通过 |r| > 0.25 的关联 (实用性阈值) │
│  │                                                      │
│  输出 ────────────────────────────────────────────────    │
│  │ AssociationSnapshot: 通过 BH 校正的关联对 + 置信度     │
│  │ ChangePointRecord: 变点时刻 + 前后对比                │
│  │                                                      │
│  存储 ────────────────────────────────────────────────    │
│  │ PG: idiographic_association (user_id, dim_pair, r,    │
│  │     p_raw, p_bh, window_start, window_end, n_obs)     │
│  │ PG: idiographic_changepoint (user_id, dim, detected_at,│
│  │     run_length_before, confidence)                     │
│  │ Redis: per-user BOCPD 状态 (run-length posterior)      │
│  │                                                      │
│  触发 ────────────────────────────────────────────────    │
│  │ 每周 Celery beat: 全量重算关联矩阵                     │
│  │ EventBus → ATTRACTOR_UPDATED: 增量更新 BOCPD          │
│  │ EventBus → TASK_COMPLETED / FOCUS_ENDED: 聚合更新     │
│  │                                                      │
│  集成 ────────────────────────────────────────────────    │
│  │ UserStateV1 新字段: idiographic_summary               │
│  │ JITAITriggerService: 关联发现增强触发条件              │
│  │ Prompt Assembly: 发现注入上下文                        │
│  │                                                      │
│  安全 ────────────────────────────────────────────────    │
│  │ Rule AM: 置信度上限 = min(0.80, statistical_power)     │
│  │ 关联语言守卫: ASSOCIATION_LANGUAGE_TEMPLATES            │
│  │ 反证机制: 用户可标记"这对我不准" → 降权               │
└──────────────────────────────────────────────────────────┘
```

### 4.3 实现量估算 (修订)

| 组件 | 文件 | 说明 |
|------|------|------|
| Service | `backend/app/services/idiographic_association_service.py` | 核心逻辑：聚合、关联、变点、校正 |
| Correlator | `backend/app/learning/rolling_correlator.py` | Spearman + BH 校正纯函数 |
| Change Point | `backend/app/learning/bocpd.py` | BOCPD 在线算法实现 |
| Schema | `backend/app/state_aggregator/schema.py` | +2 字段: `IdiographicSummaryValue`, `ChangePointItemValue` |
| PG Model | `backend/app/models/aurora_stage31.py` | 2 张表: `IdiographicAssociation`, `IdiographicChangepoint` |
| Migration | `backend/alembic/versions/xxxx_idiographic_lite.py` | Alembic 迁移 |
| Aggregator | `backend/app/state_aggregator/aggregator.py` | 注册新字段 |
| Celery Task | `backend/app/core/celery_tasks.py` | 每周重算任务 |
| EventBus | 3 个消费者 | ATTRACTOR_UPDATED, TASK_COMPLETED, FOCUS_ENDED |
| Tests | `backend/tests/unit/test_rolling_correlator.py` 等 | 单元 + 集成 |
| **合计** | **~10 文件** | 初稿"1+2+1"低估了实际工作量 |

### 4.4 冷启动与退化策略

| 阶段 | 观测天数 | 行为 |
|------|---------|------|
| 冷启动 (< 15 天) | 不启动关联分析，仅积累数据 | PersDyn 已在运行 |
| 弱先验 (15-25 天) | 计算关联但不呈现给用户 | 内部日志标记 `visibility=internal` |
| 最低可行 (25-40 天) | BH 校正后呈现，但附加"初步发现"标签 | 置信度额外 30% 折扣 |
| 充分 (> 40 天) | 完整呈现 | 正常置信度 |

**不使用"群体先验"作为关联初始值**: 群体级关联可能是伪关联（Simpson 悖论在个体内不适用，但跨用户的聚合关联方向可能与个体内相反）。更安全的做法是"先验=无关联"（r=0），让数据自己说话。

---

## 5. 安全合规框架

### 5.1 代码层面强制"关联≠因果"

**三层防护**:

**第一层 — 输出模板强制**:
```python
ASSOCIATION_LANGUAGE_TEMPLATES = {
    "positive": "你的{dim_a}和{dim_b}在最近{n}天有同步变化的趋势（相关强度：{strength}）",
    "negative": "当你的{dim_a}升高时，{dim_b}倾向于降低（相关强度：{strength}）",
    "change_point": "在{date}前后，你的{dim}模式出现了明显变化",
}
```

**第二层 — 禁用表达审查** (regex 模式，不只关键词):
```
禁止: (因为|导致|causes?|because of|因此|所以|改善了|提高了|使得|let? to|results? in)
禁止因果方向词: (改善了.{0,5}成绩|提高了.{0,5}效率|降低了.{0,5}焦虑)
```

**第三层 — 强制标注**:
每条发现必须附带:
- "基于你最近 N 天的数据" (样本透明)
- "这只是你数据中的模式，不代表因果关系" (每条发现都必须包含)
- 置信度等级 (高/中/初步)

### 5.2 用户反证机制

当用户反馈"这对我不准"时:
- 标记该关联对为 `user_disconfirmed=True`
- 该对在后续 30 天内不再呈现
- 但仍保留在内部日志中（用户可能误判，数据应保留）
- 反证信号写入 `routing_decision_log` 作为 user_correction

### 5.3 Rule Z 合规

个体内分析天然不涉及跨用户数据。所有计算在单用户数据上完成。如果未来要做跨用户聚合，必须经过 HMAC-SHA256 哈希（Rule Z）。

### 5.4 Rule AM 合规 (置信度封顶)

```python
def capped_confidence(raw_r: float, n_obs: int, bh_pass: bool) -> float:
    """关联发现的最终置信度"""
    if not bh_pass:
        return 0.0  # BH 校正未通过，不呈现
    statistical_power = min(1.0, n_obs / 45.0)  # 45 天满功率
    effect_weight = min(1.0, abs(raw_r) / 0.4)  # 中等效应以上才满分
    return min(0.80, statistical_power * effect_weight)
```

封顶 0.80（而非 0.95）因为关联分析的固有不确定性（不可观测混淆变量）不应被赋予过高置信度。

---

## 6. 与 Stage 30 的衔接

### 6.1 如果 Stage 30 已完成（元认知监控）

Stage 30 的输出可作为关联分析的第 9、10 维变量（见 §3.2）。具体衔接:

| Stage 30 信号 | 关联分析角色 | 优先级 |
|--------------|-------------|--------|
| SRL Phase (forethought/performance/reflection) | 离散调节变量 | P1 — schema 已预留 |
| 元认知准确性 (预测 vs 实际偏差) | 连续变量 | P1 — 核心新增维度 |
| 策略切换频率 | 连续变量 | P2 — 可从路由日志推导 |

### 6.2 如果 Stage 30 未完成或数据不足

Idiographic Lite **必须能在无元认知信号的情况下独立运行**。降级路径:
- 使用 8 维关联矩阵（PersDyn 5 维 + 行为补充 3 维），跳过第 9、10 维
- `IdiographicSummaryValue` schema 中元认知字段设为 `Optional`
- 检测到 SRL Phase 数据可用时自动扩展到 10 维

### 6.3 关键衔接约束

- Stage 30 的 SRL Phase 数据需 ≥ 14 天积累才能纳入关联分析
- Rule AM 双重封顶：元认知信号本身置信度低 × 关联分析置信度 → 取 min
- Stage 30 → Stage 31 的数据流应该是单向的（30 写 → 31 读），避免循环依赖

---

## 7. 推荐阅读

| # | 标题 | 作者/期刊 | 年份 | 关键发现 |
|---|------|----------|------|---------|
| 1 | Beyond Nomothetics and Idiographics: Towards a Systematization | Conner et al., SAGE | 2024 | Idiographic-nomothetic 不是二元对立而是连续谱系；hybrid 方法（群体先验 → 个体模型）是数字健康最佳路径 |
| 2 | Systematic Scoping Review of Fully Idiographic Network Analysis | Epskamp et al., Springer | 2025 | graphicalVAR + LASSO 是个体内网络分析主流方法；需 50-100+ 观测点；滑动窗口优于全量模型 |
| 3 | Idiographic Lapse Prediction with State Space Modeling | PMC | 2025 | 稀疏 EMA 数据上用状态空间模型做个体化预测的完整案例 |
| 4 | Integrating Active and Passive Digital Phenotyping | Nature Digital Medicine | 2025 | 12 月数据证明被动+主动融合优于纯被动；被动数据质量维护是关键挑战 |
| 5 | Key Features of Digital Phenotyping for Monitoring Mental Disorders | JMIR Systematic Review | 2025 | 覆盖度-重要性四象限框架；加速度计+步数+心率+睡眠是跨设备核心特征包 |
| 6 | It's All About Timing: Exploring Temporal Resolutions for Analyzing Digital Phenotyping Data | AMPPS | 2024 | 时间分辨率选择不是中性的，塑造可检测关联的类型；日级 vs 小时级结论可能不同 |
| 7 | Introducing Change Point Detection Analysis in Relationship Research | Sels et al., SAGE | 2022 | PELT 在个体内行为变化检测中的应用；稀疏数据上的表现评估 |
| 8 | Recovering Within-Person Dynamics from Psychological Time Series | Molenaar & Campbell | 2021 | 采样频率不足如何影响个体内动态恢复；最小采样率理论框架 |

---

## 8. 自审遗留风险

本报告经批判性审查后，仍存在以下不确定性，需在 Dispatch Plan 阶段解决:

| 风险 | 说明 | 缓解措施 |
|------|------|---------|
| 情绪数据粒度 | mood_valence 从 6 类 reflection 推导，分辩力 0.1-0.4 | 需增加每日 1-item 快速自评作为前置 UI 改动 |
| 用户活跃度不均 | 学生学期/假期模式差异大，45 天窗口可能跨学期 | 考虑自适应窗口：活跃期缩短、沉默期延长 |
| 虚假关联 | 即使 BH 校正后，30% FDR 意味着约 1/3 呈现的关联可能是假的 | 反证机制 + "初步发现"标签 + 持续监测 |
| 计算成本 | 每用户每周重算，千级用户约 1000 × 45 对 × O(n) | 可接受，但需监控 Celery 队列积压 |
| 与 JITAI 的耦合深度 | 初稿提出关联发现增强 JITAI 触发，但具体接口未定义 | Dispatch Plan 阶段需明确 JITAI → Idiographic 的消费方式 |

---

## 附录 A: 现有代码关键发现摘要

### BayesianLearner (bayesian_learner.py)
- 纯 Beta 分布: `(source, target) → RouteStats(alpha, beta)`
- 仅支持二元成功/失败更新，不支持连续变量多维关联
- **结论**: 不应扩展，应独立新建

### PersDynAttractorService (persdyn_attractor_service.py)
- 5 维行为动力学: study_pace, completion_rate, engagement_level, mood_valence, plan_adherence
- 14 天 EMA 序列 (`_build_series`)，28 天置信度回看
- 已有 EMA、stddev、slope、recovery_rate 计算
- **可直接复用**: `_build_series()` 输出作为关联分析的输入序列
- **关键限制**: `_build_observation_for_day()` 中 mood_valence 仅从 reflection category 推导

### SourceStateEncoder (source_state_encoder.py)
- 7 维离散枚举 (tool_category, sufficiency_level, conflict_outcome, skill_domain, achievement_tier, calendar_pressure, cohort_segment)
- 最大组合数 128，有优先级剪枝
- **关联分析适用性**: 只能做列联表分析（Cramér's V），不能做连续相关

### BehaviorSignalCollector (behavior_signal_collector.py)
- 6 类行为模式检测 + 24h 冷却去重
- 已有推断偏好更新 (`_maybe_update_task_inferred_preferences`)，含加权中位数、滞后分箱
- **关联分析适用性**: 事件级，需聚合成日级指标

### JITAITriggerService (jitai_trigger_service.py)
- 10 模板（5 维 × above/below），日预算 ≤3，24h 冷却
- 自动降级机制（3 天 misfire 率超阈值 → shadow mode）
- **关联增强点**: 当前模板基于固定 above/below 阈值，关联发现可让触发条件变为"当 dim_A 偏低且与 dim_B 正相关时"

### RouteHistoryService (route_history_service.py)
- 决策日志: source_state_v2 + decision_type + outcome (4 类) + skills_injected
- 已有 outcome backfill → BayesianLearner 更新链路
- **关联分析角色**: outcome 可作为结果变量（"哪些 source-state 条件下路由成功率更高"），但样本量取决于交互频率

### StateAggregator Schema (state_aggregator/schema.py)
- UserStateV1 v1.10: 15 个字段，含 traits_prior (BigFive) 和 srl_phase
- **新增字段**: 需添加 `idiographic_summary: StateFieldEnvelope[IdiographicSummaryValue]`
- BigFive 与 PersDyn 是独立系统，不应混淆

---

*报告终稿。本报告仅作为 Stage 31 Dispatch Plan 的理论参考，不包含实现代码。所有方法建议受"仅关联、不因果"硬约束约束。*
