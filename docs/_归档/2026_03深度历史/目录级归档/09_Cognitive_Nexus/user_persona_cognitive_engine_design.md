# 智能反馈模块核心驱动：多维度用户画像与认知计算增强方案
# Core Driver for Smart Feedback Module: Multi-dimensional User Persona and Cognitive Computing Enhancement Plan

## 1. 多维度画像体系设计 (Multi-dimensional Persona Framework)

为了支撑超越普通学习软件的“智能反馈”，我们需要构建一个立体、动态的用户模型。该模型不仅仅记录“用户学会了什么”，更核心的是捕捉“用户是如何思考的”。

### 1.1 四大核心维度 (The 4D Model)

#### A. 知识维度 (Knowledge Dimension) - "What the user knows"
这是画像的基石，基于 `Galaxy` (知识星图) 数据。
*   **节点掌握度 (Node Mastery)**: $P(K)$，用户掌握某个知识点的概率 (0.0 - 1.0)。
*   **记忆稳定性 (Memory Stability)**: 知识点在无复习情况下的半衰期（天）。
*   **知识广度 (Knowledge Breadth)**: 已解锁节点占总图谱的比例。
*   **学习速度 (Learning Velocity)**: 单位时间内掌握的新节点数量（反映吸收能力）。

#### B. 认知维度 (Cognitive Dimension) - "How the user thinks"
这是本方案的亮点，引入“元认知”分析。
*   **元认知水平 (Metacognition Score)**: 用户自我评估（“我觉得我会了”）与实际测试结果的偏差值。偏差越小，元认知越强。
*   **行为定式 (Behavior Patterns)**: 
    *   *猜题倾向 (Guessing Propensity)*: 快速作答且错误率高的频率。
    *   *顽固倾向 (Stubbornness)*: 连续错误时不查看解析/提示的频率。
    *   *规划谬误 (Planning Fallacy)*: 实际完成时间与预估时间的偏差。
*   **认知负荷 (Cognitive Load)**: 答题时长与题目难度的比率异常值。

#### C. 动力维度 (Motivation Dimension) - "Why the user learns"
用于调整反馈的情感色彩和激励策略。
*   **自我效能感 (Self-Efficacy)**: 面对高难度挑战时的坚持时长和重试次数 (Retry Count)。
*   **学习风格 (Learning Style)**: 
    *   *视觉/文本偏好*: 查看图表 vs 阅读文字的时长占比。
    *   *深究/速成偏好*: `curiosity_preference` (现有字段) 的具体化体现。
*   **兴趣图谱 (Interest Graph)**: 对特定学科或话题的交互热度。

#### D. 协作维度 (Collaboration Dimension) - "How the user interacts"
为社区和多人任务服务。
*   **社区贡献度 (Contribution Impact)**: 发布内容被点赞/引用的次数。
*   **求助偏好 (Help-Seeking Profile)**: 倾向于独立解决还是寻求帮助。
*   **沟通风格 (Communication Tone)**: 严肃学术型 vs 轻松幽默型 (基于 NLP 分析历史发言)。

---

## 2. 实时数据处理架构 (Real-time Adaptive Pipeline)

我们需要从“离线分析”转向“流式认知计算”。

### 2.1 架构图 (Architecture)

```mermaid
graph TD
    subgraph Client [端侧采集]
        App[Mobile App] -->|TrackingEvent| Gateway[Go Gateway]
    end

    subgraph Streaming [流式处理层]
        Gateway -->|Push| EventBus[Event Bus / Redis Stream]
        EventBus -->|Consume| CogWorker[Cognitive Worker (Python)]
        EventBus -->|Consume| StatsWorker[Stats Worker (Go)]
    end

    subgraph Computing [认知计算层]
        CogWorker -->|Pattern Recognition| PatternEngine[行为定式引擎]
        CogWorker -->|Knowledge Tracing| BKTModel[BKT/IRT 模型]
        
        PatternEngine -->|Update| CogFrag[Cognitive Fragments Table]
        BKTModel -->|Update| GalaxyState[Galaxy User State]
    end

    subgraph Serving [服务层]
        Orchestrator[Context Orchestrator] -->|Query| RedisCache[(Redis Snapshot)]
        Orchestrator -->|Query| DB[(PostgreSQL)]
        
        CogFrag -->|Sync| RedisCache
        GalaxyState -->|Sync| RedisCache
    end
```

### 2.2 认知计算层 (Cognitive Computing Layer)
这是一个新增的逻辑层，位于 `backend/services/learning/` 下。
*   **输入**: 原始行为流 (e.g., "PageEnter", "OptionSelect", "Scroll", "Pause").
*   **转换**: 
    *   `Session Analyzer`: 将一系列点击流切分为一个“学习会话”。
    *   `Feature Extractor`: 提取特征（如：题目停留时间、选项切换次数）。
    *   `Label Generator`: 生成语义标签（如：tag="hesitant", tag="distracted"）存入 `CognitiveFragment`。
*   **输出**: 实时更新画像快照。

---

## 3. 核心算法模型升级 (Algorithmic Core)

### 3.1 知识追踪：引入 BKT (贝叶斯知识追踪)
目前的掌握度计算可能过于线性。建议对核心知识点采用 BKT 模型：

$$P(L_t) = P(L_{t-1} | \text{Result}_t)$$

其中：
*   $P(L_t)$: $t$ 时刻掌握知识的概率。
*   $P(G)$: 猜对率 (Guess) - 即使不会也能答对的概率。
*   $P(S)$: 失误率 (Slip) - 会了但粗心答错的概率。

**升级动作**: 在 `GalaxyService` 中实现 BKT 状态机。

### 3.2 难度校准：引入 IRT (项目反应理论)
用于评估题目难度和区分度，从而更准确地更新画像。
$$P(\theta) = c + \frac{1-c}{1 + e^{-a(\theta - b)}}$$
*   $\theta$: 用户能力值 (来源于画像)。
*   $b$: 题目难度。
*   $a$: 题目区分度。

### 3.3 记忆衰减与复习机制
基于 Ebbinghaus 遗忘曲线的改进版 (类似 SuperMemo/Anki 算法)：

**掌握度衰减公式**:
$$M_{new} = M_{last} \cdot e^{-\frac{\Delta t}{S}}$$
*   $M$: 掌握度。
*   $\Delta t$: 距离上次复习的时间。
*   $S$: 记忆稳定性 (Stability)，每次成功复习后 $S$ 会指数级增长 ($S_{n+1} = S_n \cdot \text{Gain}$)。

**错误惩罚机制**:
如果用户对高掌握度 ($M > 0.8$) 的知识点答错：
*   惩罚系数 $P = 1 + (\text{Confidence} \times 2)$
*   掌握度大幅回退，强制进入“紧急复习队列”。

---

## 4. 智能反馈对接机制 (Smart Feedback Integration)

画像数据必须转化为 LLM 能理解的 Prompt，才能驱动“智能反馈”。

### 4.1 Context Orchestrator 升级
现有的 `ContextOrchestrator` (in `backend/app/core/context_manager.py`) 需要增强：

1.  **Schema Definition**: 定义标准的 `UserPersonaSchema` JSON 结构。
2.  **Prompt Injection**:
    在 System Prompt 中注入：
    ```text
    [USER_PERSONA]
    - Knowledge Level: Expert in Math, Novice in Physics.
    - Cognitive Style: Impulsive (often guesses), Low Metacognition.
    - Motivation: High (Resilient).
    - Current State: Frustrated (3 consecutive errors).
    
    [FEEDBACK_STRATEGY]
    - Tone: Encouraging but firm.
    - Instruction: Do NOT give the answer directly. Ask guiding questions to slow them down.
    ```

### 4.2 个性化反馈策略引擎 (Feedback Strategy Engine)
这是一个规则+模型引擎，根据画像决定反馈策略：

| 画像特征 | 策略指令 (System Prompt Instruction) | 示例话术 |
| :--- | :--- | :--- |
| **高掌握度 + 粗心错误** | "Point out the contradiction strictly. Ask to re-check." | "你之前这部分掌握得很好，是不是看错符号了？再检查一遍。" |
| **低掌握度 + 频繁试错** | "Provide scaffolding. Break down the problem." | "我们先不看答案。这道题的第一步是定义变量，你觉得应该怎么设？" |
| **低元认知 (盲目自信)** | "Socratic questioning. Challenge their logic." | "你确定是这样吗？如果 X=0 会发生什么？" |
| **高焦虑 (检测到 frustration)** | "Empathize first. Reduce cognitive load." | "这道题确实很难，很多人都在这里卡住。我们深呼吸，换个角度看..." |

---

## 5. 演进路线图 (Roadmap)

### Phase 1: 基础建设 (短期 - 1个月)
*   **数据库**: 扩展 `users` 表，完善 `cognitive_fragments` 表结构。
*   **采集**: 在 Mobile 端完善埋点 (PageDuration, InteractionDepth)。
*   **计算**: 实现基础的“掌握度衰减”定时任务 (Celery)。

### Phase 2: 算法接入 (中期 - 2-3个月)
*   **模型**: 实现 BKT 算法 Python 模块。
*   **引擎**: 开发 `Feedback Strategy Engine`，硬编码初步的反馈规则。
*   **可视化**: 在前端展示“遗忘曲线”和“能力雷达图”。

### Phase 3: 认知智能 (长期 - 3-6个月)
*   **AI 标注**: 使用 LLM 异步分析 `CognitiveFragment`，自动生成定式标签。
*   **自适应**: 全面上线 IRT，实现题目难度的动态自适应推荐。
*   **完全体**: 智能反馈模块完全由画像驱动，实现“千人千面”的 AI 导师。
