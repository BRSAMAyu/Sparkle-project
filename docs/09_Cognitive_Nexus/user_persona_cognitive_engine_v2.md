# V2.0 生产级多维度用户画像与认知计算引擎方案
# Production-Grade User Persona & Cognitive Computing Engine V2.0

## 1. 方案概述 (Executive Summary)

本方案是对 V1 版本“功能导向”设计的全面重构，旨在构建一个**合规 (Compliant)**、**鲁棒 (Robust)** 且 **可解释 (Explainable)** 的生产级认知计算系统。

核心升级点包括：
1.  **隐私基座**: 从“数据收集”转向“用户授权与透明度管理”。
2.  **置信度系统**: 引入概率模型解决 LLM 标签幻觉与误判问题。
3.  **闭环校准**: 建立从离线数据挖掘 (Offline Mining) 到在线实时推断 (Online Inference) 的完整数学闭环。
4.  **安全路由**: 防止画像数据对 LLM 产生负面诱导 (Negative Priming)。

---

## 2. 隐私与合规基座 (Trust & Compliance Base)

在处理用户“认知与行为”数据时，隐私保护不仅是合规要求，更是用户信任的基石。

### 2.1 画像透明度中心 (Persona Transparency Center)

用户拥有对系统所推断出的“数字孪生”的完全知情权与控制权。

*   **可视化看板**:
    *   用户可在“学习设置”中查看系统对其的推断标签（如：“视觉学习者”、“冲动型答题”、“早起高效型”）。
    *   **置信度展示**: 明确标识标签的确定性（如：“系统 85% 确定您偏好视频讲解”）。
*   **纠错与遗忘机制 (Right to Correction & Erasure)**:
    *   **纠错**: 用户可手动修正标签（例如：系统误判为“粗心”，用户更正为“计算器按错”），该反馈将作为强信号修正模型。
    *   **原子化删除**: 用户可删除特定维度的画像（如“删除所有性格推断数据”），而不影响基础学习记录。
    *   **数据隔离**: 敏感推断（如情绪状态）存储于独立加密分区，不与广告或第三方营销 ID 关联。

### 2.2 未成年人保护策略 (Minor Protection)

*   **心理推断熔断**: 针对 14 岁以下用户，系统**自动关闭**深度心理画像功能（如“焦虑指数”、“抗压能力”），仅保留客观学习能力画像（如“知识点掌握度”）。
*   **非诱导性反馈**: 禁止使用可能导致成瘾的“赌博式”奖励机制（如基于挫败感的随机奖励箱）。
*   **监护人报告**: 涉及认知能力显著下降的异常波动（可能暗示现实生活问题），仅在通过去标识化风险评估后，以建议形式通知监护人，而非直接打标签。

### 2.3 数据最小化与生命周期 (Data Minimization & Lifecycle)

| 数据层级 | 数据内容 | 保留策略 | 存储介质 |
| :--- | :--- | :--- | :--- |
| **L1 原始流** | 点击、滚动、停顿 (Clickstream) | **30天** (用于故障排查与短时校准) | Cold Storage (S3/Parquet) |
| **L2 认知片段** | 会话级特征 (Session Features) | **1年** (用于周期性回顾) | Warm Storage (TimescaleDB) |
| **L3 画像标签** | 稳定的能力与性格标签 | **永久** (直至用户注销或主动删除) | Hot Storage (Redis/Postgres) |

---

## 3. 鲁棒性认知计算链路 (Robust Cognitive Pipeline)

解决 V1 方案中“简单规则触发”导致的误判和不稳定性。

### 3.1 架构设计 (Streaming Architecture)

```mermaid
graph TD
    subgraph Client [端侧采集]
        App[Mobile App] -->|NormEvent| Gateway[Go Gateway]
    end

    subgraph Streaming [流式处理层]
        Gateway -->|Push| Kafka[Kafka/Redpanda]
        Kafka -->|Group: Behavior| Flink[Stream Processor (Flink/Rust)]
    end

    subgraph CognitiveCore [认知计算核心]
        Flink -->|Extract| FeatureStore[Feature Store (Redis)]
        Flink -->|Compute| ConfidenceEngine[置信度评分引擎]
        ConfidenceEngine -->|Output| ValidTags[Validated Persona Tags]
    end

    subgraph FeedbackLoop [闭环校准]
        ValidTags -->|Update| ProfileDB[(UserProfile DB)]
        ProfileDB -->|Context| Orchestrator
        Orchestrator -->|Inject| LLM
        LLM -->|Response| User
        User -->|Action| App
    end
```

### 3.2 关键技术规范

#### A. 事件幂等与乱序处理 (Idempotency & Watermark)
*   **Event ID**: 使用 `UUIDv7` (时间排序友好)，确保同一事件在弱网重传时被精确去重。
*   **Watermark**: 设定 15 分钟的迟到阈值。针对离线学习产生的“批量上传”数据，采用**回溯更新 (Backfill)** 策略：不触发实时推送，但更新长期画像统计值。
*   **Schema Registry**:
    *   严格的版本控制 (`v1.interaction_event` -> `v2.interaction_event`)。
    *   不兼容的旧版客户端数据将被路由至 `Dead Letter Queue` 进行降级处理，防止污染核心计算链路。

#### B. 指标归一化 (Normalization)
排除设备与环境因素对“认知判断”的干扰。
*   **时间归一化**:
    *   $T_{norm} = \frac{T_{client} - T_{network\_latency}}{T_{avg\_read\_speed}}$
    *   在端侧预计算 `reading_speed_baseline`（用户阅读纯文本的平均速度），以此判断用户是在“思考”还是单纯“阅读慢”。
*   **设备性能加权**:
    *   低端机型的“页面加载卡顿”不应计入“犹豫时长”。端侧需上报 `frame_drop_rate` 作为置信度衰减因子。

### 3.3 置信度评分系统 (Confidence Scoring)

解决 LLM 根据一次偶然行为“乱贴标签”的问题。所有标签必须携带置信度 $C \in [0, 1]$。

$$ C_{tag} = \left( \sum_{i=1}^{N} w_i \cdot E_i \right) \cdot D(t) \cdot S_{context} $$

*   $E_i$: 证据强度 (例如：连续3次同类错误 $E=0.9$，单次错误 $E=0.2$)。
*   $w_i$: 证据源权重 (例如：主动纠错 > 行为推断 > 文本分析)。
*   $D(t)$: 时间衰减函数 (旧行为的参考价值随时间指数下降)。
*   $S_{context}$: 上下文一致性因子 (该行为是否为孤立异常点)。

**策略阈值**:
*   $C < 0.4$: **忽略** (作为噪声过滤)。
*   $0.4 \le C < 0.7$: **观察期** (存入后台，但不注入 Prompt)。
*   $C \ge 0.7$: **激活** (注入 System Prompt，驱动个性化反馈)。

---

## 4. 算法落地与校准 (Algorithmic Calibration)

### 4.1 BKT/IRT 离线标定流程 (Offline Calibration)

认知模型参数不是拍脑门定的，需基于历史数据反向拟合。

1.  **数据导出 (Data Export)**: 每周导出 `user_response_logs` (匿名化处理)。
2.  **参数拟合 (Parameter Fitting)**:
    *   **IRT (Item Response Theory)**: 使用 MCMC 方法估算每道题目的 $b$ (难度) 和 $a$ (区分度)。
        *   *产出*: 更新 `question_metadata` 表。
    *   **BKT (Bayesian Knowledge Tracing)**: 对每个知识点 (KC) 拟合 $P(Guess)$ 和 $P(Slip)$。
        *   *产出*: 更新 `knowledge_component_params` 表。
3.  **回测验证 (Backtesting)**: 使用更新后的参数重跑上周数据，计算 AUC (Area Under Curve) 和 RMSE。只有当预测准确率提升时，才将参数推送到线上服务。

### 4.2 冷启动与 A/B 验证

*   **小样本冷启动 (Few-Shot Cold Start)**:
    *   新用户注册后，系统分配一个“通用先验分布” (Global Prior)。
    *   通过 **3-5 道“锚点题” (Anchor Items)** (高区分度题目) 快速定位用户能力区间，大幅修正 $P(L_0)$。
*   **线上 A/B 验证**:
    *   设立对照组 (无个性化反馈) 和实验组 (基于画像的反馈)。
    *   **核心指标**: 不看“点击率”，看 **“学习增益” (Learning Gain)** —— 同样知识点在 T+1 天的留存率差异。

---

## 5. 安全上下文路由 (Secure Context Injection)

防止 LLM 因为画像标签产生偏见或负面诱导（Self-Fulfilling Prophecy）。

### 5.1 Context Orchestrator 安全层

*   **脱敏清洗 (Sanitization)**:
    *   Prompt 中禁止直接出现负面定性词汇。
    *   *Bad*: `User is stupid at math.`
    *   *Good*: `User currently struggles with quadratic equations (Confidence: 0.85).`
*   **注入防御 (Injection Defense)**:
    *   将画像数据封装在 XML 标签中 `<persona_context>`，并指示 LLM 仅将其作为参考背景，严禁在回复中向用户透露画像内容（“系统说你是个急躁的人...”）。

### 5.2 结构化输出校验 (Guardrails)

在 LLM 返回结果后，增加一道校验工序：

1.  **情感检测**: 检测回复是否包含打击性、嘲讽或过度焦虑的词汇。
2.  **标签一致性**: 确保反馈策略与画像意图一致（例如：画像显示用户“受挫”，但 LLM 回复却极其“严厉”，则触发拦截重生成）。

---

## 6. 存储与运维策略 (Storage & Ops)

### 6.1 分层存储架构

*   **Redis Cluster (Hot)**:
    *   存储 `ActiveUserSession`、`CurrentPersonaSnapshots`。
    *   TTL: 24小时 (活跃窗口)。
*   **PostgreSQL + TimescaleDB (Warm)**:
    *   存储 `CognitiveFragments` (时序数据)、`WeeklyStats`。
    *   保留: 12个月。
*   **S3 Data Lake (Cold)**:
    *   存储原始 `Clickstream Logs`、模型训练集。
    *   格式: Parquet (列式存储，优化查询成本)。

### 6.2 监控与报警

*   **标签漂移监测 (Label Drift)**:
    *   报警规则：如果某天被标记为“冲动型”的用户比例从 5% 飙升至 30%，说明算法有 Bug 或前端埋点故障。
*   **负面反馈环路监测 (Negative Feedback Loop)**:
    *   监测高频错误用户的流失率。如果“个性化干预”导致流失率高于“无干预组”，立即熔断该策略。

---

## 7. 澄清问题回复 (Q&A)

针对您提出的关键疑问，回复如下：

**Q1: 用户数据的归属权与可移植性如何保障？**
*   **A**: Sparkle 遵循“数据主权属于用户”原则。我们提供符合 GDPR 标准的“全量数据导出”功能（JSON/CSV格式），包含原始学习记录与推断画像。用户注销时，我们执行物理删除（不仅仅是软删除），仅保留法律规定的最小化财务审计记录。

**Q2: 如何防止模型“幻觉”导致给用户贴上错误的心理标签？**
*   **A**: 我们引入了**双重保险机制**：
    1.  **置信度阈值**: 只有当多源证据（行为+结果+时间）交叉验证后的置信度 > 0.7 时，标签才会生效。
    2.  **白名单机制**: 系统仅允许生成预定义的、经过教育心理学验证的标签集合，严禁 LLM 自行创造形容词。

**Q3: 新用户没有历史数据，如何避免冷启动体验差？**
*   **A**: 采用 **“锚点诊断”策略**。新用户的前 5 分钟交互会被引导至一组高区分度的“锚点任务”。这些任务能以最大信息熵快速收敛用户的能力参数。在此之前，系统采用温和的“鼓励型”通用策略，不进行激进的个性化干预。

**Q4: 高频流式计算与存储的成本如何控制？**
*   **A**:
    1.  **端侧聚合**: 手机端不上传每一个 touch 事件，而是每 30 秒聚合一次特征包（Feature Packet），减少 90% 的网络请求与后端 QPS。
    2.  **分级计算**: 实时链路仅计算简单的统计特征；复杂的深度推断（如 BKT 参数更新）在夜间低峰期通过离线批处理完成。

---
