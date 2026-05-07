# Sparkle V2 路演 PPT 附录页技术信息与设计指导（组员版）

> 用途：供组员手工打磨 PPT 附录页。  
> 原则：附录不是“堆技术名词”，而是答辩时证明 Sparkle 不是概念项目，而是一个已经有真实工程、真实产品模块、真实验证和长期愿景的系统。  
> 建议：主讲 8 分钟时只轻触这些内容；答辩中根据评委问题跳转对应附录。

---

## 总体设计原则

附录页每一页都要回答一个评委可能追问的问题：

| 附录 | 回答的问题 |
|---|---|
| A 社群 / 责任伙伴 | “Sparkle 只有 AI 对话吗？用户真的能坚持执行吗？” |
| B 安全 / 隐私 / 可追溯 | “AI 建议可信吗？出错怎么办？用户数据安全吗？” |
| C Aurora | “你们说更懂用户，底层到底不是 prompt wrapper 吗？” |
| D 知识星图 | “长期学习资产到底沉淀在哪里？” |
| E Skill Extraction / Learning Base | “系统怎么越用越好？不是每次都重新开始吗？” |
| F MirrorFish / 多 Agent / SGW | “策略怎么验证？你们如何降低试错成本？” |
| G 技术架构 | “系统工程上怎么跑起来？不是单页面 demo 吗？” |
| H 工程验证 | “你们到底做到什么程度？有什么可检查证据？” |

每页建议都包含四层：

1. **一句话判断**：评委 5 秒内应该读懂这页想证明什么。
2. **结构图 / 机制图**：用图展示系统关系，少放长段文字。
3. **真实证据**：代码、API、测试、验收报告、指标。
4. **答辩口径**：如果评委追问，这页该怎么讲。

### 图片 prompt 统一风格基准

当前 PPT 已切换为深蓝科技风，因此所有 AI 生成图都建议统一遵循：

- 主色：deep navy / midnight blue / dark graphite。
- 强调色：electric cyan、soft blue、少量 violet 或 emerald，不要大面积紫色渐变。
- 气质：可信、工程化、产品真实、路演级，而不是炫技海报。
- 画面：优先 UI mockup、机制图、系统流程图、证据 dashboard；少用纯抽象光效。
- 禁忌：不要 emoji、不要卡通机器人、不要赛博朋克城市、不要过度霓虹、不要密密麻麻小字。

如果新增“核心创新性分析”页，可以使用：

```text
Create a premium dark-blue innovation analysis slide visual for an AI-native learning and goal achievement system called Sparkle. Show a central transformation axis: User Goal -> Aurora Decision Entry -> Goal Path Orchestration -> Feedback Replanning -> Personal Method Assets. Around the axis, place four clean innovation modules: 1) Aurora decides before answering, 2) minimum passing path and active trade-off, 3) failure attribution and dynamic replanning, 4) long-term personal method asset accumulation. Use a deep navy / midnight blue background, refined glass cards, electric cyan flow lines, soft blue labels, restrained violet highlights for Aurora, and emerald highlights for verified progress. The style should be credible, technical, and competition-ready, suitable for a university innovation roadshow. Avoid emoji, avoid cartoon robots, avoid cyberpunk city scenes, avoid abstract decorative blobs, avoid dense text, avoid exaggerated sci-fi effects.
```

---

# Appendix A：社群 / 责任伙伴机制

## 1. 这一页要证明什么

Sparkle 不是一个孤立的 AI 对话工具。它把“AI 规划”延伸到真实执行环境中，通过责任伙伴、冲刺群、学习小队、打卡、资源分享和社群反馈，帮助用户把目标坚持下去。

**推荐标题：**  
社群不是聊天广场，而是目标推进结构

**核心一句话：**  
Sparkle 的社群层不是泛社交，而是把目标、任务、打卡、资源和伙伴关系组织成可执行、可见证、可反馈的支持系统。

## 2. 可以放进 PPT 的真实信息

### 已有模块

- 好友系统：好友请求、好友列表、好友推荐、共同目标匹配。
- 学习小队：围绕长期目标组织，如每日算法、考研数学、课程复习。
- 冲刺群：围绕短期 deadline，如期末考试、竞赛、项目 DDL。
- 群聊：支持文本、任务分享、进度分享、成就分享、打卡消息、系统消息。
- 打卡：记录学习时长、内容、连续天数、火苗贡献。
- 火堆系统：把个人和群组学习活跃度可视化。
- 责任伙伴：一对一目标互相监督，支持邀请、接受、check-in、鼓励、提醒节奏。
- 社群资源分享：计划、任务、知识节点、种子库内容可以变成共享卡片。

### 代码 / 文档证据

- 社群功能文档：`docs/01_核心模块文档/08_社群功能模块.md`
- 社群 API：`backend/app/api/v1/community.py`
- 责任伙伴 API：`backend/app/api/v1/accountability.py`
- 责任伙伴模型：`backend/app/models/accountability.py`
- 移动端社群页面：`mobile/lib/features/community/presentation/screens/`
- 移动端社群组件：`mobile/lib/features/community/presentation/widgets/`
- 责任伙伴组件：`mobile/lib/features/community/presentation/widgets/accountability/`
- 社群闭环报告：`docs/product/parallel_closeout/CXP-13_community_social_learning_REPORT_2026-05-02.md`
- 责任伙伴报告：`docs/product/parallel_closeout/CXP-15_accountability_social_REPORT_2026-05-02.md`

### 可引用事实

- 责任伙伴支持 `check_in_days` 节奏，不是每天骚扰用户。
- 提醒会尊重用户时区、勿扰、通知偏好，并做同一天去重。
- Goal Mates / Squad / Following / Global Feed 有不同 feed 语义。
- 非群成员不能枚举群组共享资源；被拉黑或软删除内容不会继续泄露。
- 责任伙伴数据进入 Aurora 时，会做角色化、脱敏处理，避免泄露具体姓名和内容。

## 3. 建议页面结构

**版式：三段式机制图**

左侧：用户场景  
用一个小故事开头：

> “第 3 天晚上任务没完成，用户想放弃。”

中间：社群推进机制  
画成一个闭环：

```text
目标承诺
→ 责任伙伴
→ 每日 check-in
→ 任务 / 资源分享
→ 鼓励与提醒
→ Aurora 读取脱敏信号
→ 调整任务节奏
```

右侧：工程证据  
放 4 个小证据块：

- `AccountabilityPartnership`
- `check_in_days`
- `SocialSignalBridge`
- `403 / block / soft-delete guards`

## 4. 建议页面文案

页面主文案：

> AI 能给计划，但很多目标失败在执行阶段。Sparkle 的社群层把“计划”变成“被看见的承诺”和“可恢复的节奏”。

四个小卡片：

1. **责任伙伴**  
   一对一目标承诺、check-in、鼓励、错过提醒。

2. **冲刺群**  
   围绕考试 / 项目 deadline 的短期协同。

3. **资源分享**  
   任务、计划、知识节点、种子内容可安全分享与采纳。

4. **社群信号进入 Aurora**  
   只进入脱敏后的角色信号，不泄露伙伴身份与原文。

## 5. 可选图片 prompt

如果需要生成一张页面主视觉，可以用：

```text
Create a premium dark-blue technology roadshow illustration for an AI learning app called Sparkle. Show a modern mobile-app ecosystem where a student goal sits in the center, connected to an accountability partner, a sprint group, daily check-ins, shared task cards, and an AI guidance layer. Use a deep navy / midnight blue background, clean glass-like UI panels, electric cyan and soft blue accents, with a small amount of emerald for positive progress. The visual should feel credible, high-end, and product-real, suitable for a university innovation competition appendix slide. Use clear UI-like modules, subtle connecting lines, restrained glow, and readable hierarchy. Avoid emoji, avoid cartoon characters, avoid cyberpunk city scenes, avoid generic social media feeds, avoid excessive neon.
```

## 6. 答辩口径

如果评委问“社群是不是可有可无”，回答：

> 对 Sparkle 来说，社群不是流量功能，而是执行闭环的一部分。AI 负责诊断和规划，但目标真正落地需要外部承诺、节奏提醒和社会反馈。我们做责任伙伴、冲刺群和资源分享，是为了让计划在现实中有承接结构。

## 7. 不建议这样讲

- 不要说“我们做了一个社交平台”。
- 不要把火苗、打卡讲成游戏化噱头。
- 不要承诺社群数据会直接用于个人画像，必须强调脱敏、用户控制和隐私边界。

---

# Appendix B：安全 / 隐私 / 可追溯体系

## 1. 这一页要证明什么

Sparkle 的 AI 决策不是黑盒。关键建议有 trace，有 receipt，用户可以纠正，系统可以回滚；同时用户数据经过权限、脱敏、隐私预算和安全边界保护。

**推荐标题：**  
可信不是“保证不出错”，而是出错后能看见、能纠正、能回到正确轨道

**核心一句话：**  
Sparkle 把 AI 建议设计成可追溯、可解释、可纠正、可审计的决策链，而不是一次性黑盒输出。

## 2. 可以放进 PPT 的真实信息

### 关键机制

- **CausalTrace**：记录从 signal、policy、directive、audit 到 receipt 的链路。
- **User-visible Receipt**：用户能看到“系统为什么这么判断”。
- **Calibration Receipt**：用户纠正后，系统生成“我改了什么、为什么改、下次如何影响”的回执。
- **PII Redaction**：外部 LLM 调用前对邮箱、电话、身份证、银行卡等敏感信息脱敏。
- **Privacy Community Engine**：社群聚合信号经过 k 匿名、差分隐私、隐私预算控制。
- **RBAC / JWT / WebSocket 安全**：身份访问控制、连接安全、错误脱敏、rate limiter。
- **Kill Switch**：关键功能有三态开关，可 live / shadow / off 控制。

### 代码 / 文档证据

- Trace 存储：`backend/app/signals/causal_trace_store.py`
- Trace 类型：`backend/app/signals/types.py`
- Orchestration trace：`backend/app/orchestration/orchestration_trace.py`
- AI 记忆隐私说明：`docs/product/SPARKLE_AI_MEMORY_PRIVACY_2026-05-01.md`
- 社群隐私引擎：`backend/app/signals/privacy_community_intelligence.py`
- 社群隐私报告：`docs/product/parallel_closeout/FV-05_privacy_community_REPORT_2026-05-02.md`
- LLM 安全包装器：`backend/app/core/llm_security_wrapper.py`
- Go 安全头：`backend/gateway/internal/middleware/security.go`
- Aurora closeout：`docs/product/SPARKLE_AURORA_CLOSEOUT_FINAL_ACCEPTANCE_2026-05-02.md`
- Phase I Exit Gate：`docs/product/SPARKLE_AURORA_PHASE_I_EXIT_GATE_2026-04-22.md`

### 可引用事实

- CausalTrace 默认保存 30 天；压缩摘要可保留 90 天。
- 每个用户保留最近 trace 列表，超过后会 compact old traces。
- 社群聚合默认 k 阈值为 5；小于 5 不共享，5-15 只共享趋势，16+ 才共享匿名聚合。
- 隐私预算有 `epsilon` 和 `max_epsilon` 控制，预算耗尽会拒绝查询。
- Aurora closeout 中 WebSocket 安全、错误脱敏、纠错协议、校准回执、session 连续性均已通过验收。

## 3. 建议页面结构

**版式：一条纵向信任链 + 右侧隐私边界**

左侧 70%：决策链路图

```text
Raw Event
→ Actionable Signal
→ Policy Decision
→ Execution Directive
→ Audit
→ User-visible Receipt
→ Outcome
→ Correction / Rollback
```

右侧 30%：隐私边界卡片

```text
个人数据：用户私有
社群信号：k>=5 + DP + budget
外部模型：PII redacted context only
系统权限：JWT / RBAC / rate limit / kill switch
```

页面底部放一句：

> AI 教育产品真正的安全感，不是永远不犯错，而是每次关键决策都可追踪、可解释、可纠正。

## 4. 建议页面文案

主文案：

> Sparkle 不让 AI 建议停留在“它这么说”。每一次关键建议都要能追问：依据是什么、影响了什么、用户如何纠正、系统如何更新。

证据小字：

- `CausalTraceStore`: signal / policy / directive / audit / receipt
- `CalibrationReceipt`: what / why / next_time
- `PrivacyPreservingCommunityEngine`: k 匿名 + 差分隐私 + 隐私预算
- `LLMSecurityWrapper`: 输入净化、配额、输出验证、监控

## 5. 可选图片 prompt

```text
Create a premium dark-blue technical trust architecture diagram for an AI learning system. Show a clean decision trace pipeline from user event to signal, policy decision, directive, audit, user-visible receipt, outcome, and correction. On the side, show privacy boundaries: personal data vault, anonymized cohort analytics with k-anonymity and differential privacy, and redacted LLM context. Use a deep navy / dark graphite background, luminous cyan trace lines, soft blue labels, and small emerald highlights for verified states. The style should be a polished engineering appendix slide for a university AI product roadshow: crisp, credible, minimal, and readable. Avoid emoji, avoid cyberpunk, avoid cartoon locks everywhere, avoid dense tiny text, avoid dramatic hacker aesthetics.
```

## 6. 答辩口径

如果评委问“AI 建议错了怎么办”，回答：

> 我们不把可信建立在“AI 永远正确”上，而是建立在可追踪和可纠正上。关键建议会进入 trace，用户纠正后会生成 calibration receipt，并影响下一轮上下文和策略。出错不是结束，而是系统学习和校准的入口。

## 7. 不建议这样讲

- 不要说“我们的 AI 不会幻觉”。
- 不要说“社群数据会直接训练用户画像”。
- 不要把隐私页做成法律条款，要讲用户能感知的信任机制。

---

# Appendix C：Aurora 自适应认知控制层

## 1. 这一页要证明什么

Aurora 不是普通聊天人格，也不是 prompt 模板。它是 Sparkle 的自适应认知控制层：读取系统仪表盘，判断当前目标状态和用户缺口，再决定下一步该诊断、规划、安抚、追问、缩短任务还是重规划。

**推荐标题：**  
Aurora：不是更会聊天，而是每次回答前先完成目标决策

**核心一句话：**  
Aurora 把“裸模型回答”变成“带目标、状态、偏好、资料和反馈的自适应决策”。

## 2. 可以放进 PPT 的真实信息

### Aurora Runtime v1 的三层架构

```text
用户看到的对话
Chat Layer：根据 Aurora 决策生成自然语言

Aurora 认知核心
Decision Loop：读仪表盘、做认知推理、不直接生成用户文本

系统脚手架
State Aggregator / Exam Sprint Policy / Galaxy / Task Manager / Memory / Achievement
```

### 6 个模块

- `AuroraState`：Aurora 当前怎么看用户和场景。
- `Control Surface`：可调参数和硬边界。
- `DashboardReadout`：系统脚手架产出的预处理读数。
- `AuroraDecisionLoop`：LLM 认知推理层。
- `ChatLayerAdapter`：把 Aurora 决策翻译成用户可见对话。
- `Skill-as-Manual`：按需读取的能力说明书。

### 已实现 / 已有代码证据

- Aurora Runtime 规格：`docs/product/SPARKLE_AURORA_RUNTIME_V1_SPEC_2026-04-24.md`
- Aurora skill registry：`backend/app/aurora/runtime_v1/skills.py`
- Orchestration trace：`backend/app/orchestration/orchestration_trace.py`
- Correction payload / receipt 验收：`docs/product/SPARKLE_AURORA_CLOSEOUT_FINAL_ACCEPTANCE_2026-05-02.md`
- Aurora Phase I：`docs/product/SPARKLE_AURORA_PHASE_I_EXIT_GATE_2026-04-22.md`

### 可以讲的关键技术点

- Aurora 不直接和用户聊天，它先做认知决策，Chat 层再生成用户可读表达。
- Aurora 能根据 surface 加载不同 skill affordance，例如：
  - `proactive_intensity`
  - `conversation_style`
  - `task_density_hint`
  - `wake_scheduling`
  - `agenda_priority`
- 硬边界由系统强制，例如勿扰、隐私、禁用动作、安全红线，不允许 Aurora 自行覆盖。
- 用户纠正会进入 correction protocol，并影响下一轮 prompt/context。

## 3. 建议页面结构

**版式：三层架构剖面图**

从上到下：

1. 用户看到的对话：自然语言、多条消息、任务卡、回执。
2. Aurora 认知核心：state、tension、intent、decision。
3. 系统脚手架：任务、计划、知识星图、记忆、社群、成就、安全。

右侧放一个“7 天计网例子”：

```text
用户输入：7 天后考计网，基本没学

普通 AI：给完整复习计划

Aurora 决策：
1. 进入 exam_sprint
2. 先诊断高收益点
3. 缩短任务粒度
4. 放弃低 ROI 章节
5. 失败后重规划
```

## 4. 建议页面文案

主文案：

> Aurora 的核心不是“更像朋友说话”，而是让每一次回答都不是裸模型输出，而是经过用户状态、目标约束、资料证据和反馈历史校准后的决策。

三个技术标签：

- `DashboardReadout`: 先读干净状态，不处理原始噪声。
- `Decision Loop`: 先判断缺口与下一步，不直接输出长文。
- `Control Surface`: 可调但受硬边界约束。

## 5. 可选图片 prompt

```text
Create a premium dark-blue layered architecture diagram for an AI-native learning system named Aurora. Show three horizontal layers: top "User-visible conversation" with chat bubbles and task cards; middle "Aurora cognitive decision loop" with state, tension, intent, and decision nodes; bottom "System scaffolding" with task manager, knowledge graph, memory, community signals, safety boundaries, and model router. Use a midnight blue background, refined glass panels, electric cyan control-flow lines, soft blue typography, and restrained violet highlights only for the Aurora decision loop. The diagram should feel like a high-end product architecture appendix slide: clean, technical, precise, and credible. Avoid emoji, avoid generic robot imagery, avoid fantasy holograms, avoid overcomplicated code visuals.
```

## 6. 答辩口径

如果评委问“这和 prompt engineering 有什么区别”，回答：

> Prompt engineering 是用户自己组织上下文。Aurora 是系统持续维护用户状态、目标状态和反馈历史，在每次回答前自动做上下文和决策编排。它不是写一段固定 prompt，而是一个 adaptive harness。

## 7. 不建议这样讲

- 不要说 Aurora 已经完全是独立意识或人格。
- 不要把 Aurora 讲成“比所有模型都聪明”。
- 不要展示太多内部类名，把技术翻译成“用户能感知到的决策质量”。

---

# Appendix D：知识星图 / 个人知识库

## 1. 这一页要证明什么

Sparkle 的长期记忆不是聊天记录，而是围绕目标、知识点、掌握度、错因、资料来源和复习建议构建的个人知识世界模型。

**推荐标题：**  
知识星图：长期资产不是笔记堆，而是可行动的知识状态

**核心一句话：**  
知识星图把“我学过什么”变成“我掌握到什么程度、为什么薄弱、下一步该做什么”的可计算资产。

## 2. 可以放进 PPT 的真实信息

### 核心能力

- 获取用户知识星图：节点、边、用户状态。
- 点亮知识点：任务完成后更新掌握度、学习时长、学习次数。
- 语义搜索：基于 pgvector / 向量相似度搜索知识节点。
- 自动归类任务：任务标题自动匹配知识点。
- 复习建议：基于掌握度和遗忘曲线推荐复习。
- LLM 拓展：学习次数满足条件后可触发知识点拓展。
- 事件来源：文档、翻译、错题、任务完成等可成为图谱节点来源。

### 学习状态字段

CXP-09 中新增了更可解释的节点状态：

- `unknown`
- `learning`
- `weak`
- `ready_for_review`
- `mastered`
- `connected_to_goal`
- `blocked_by_prerequisite`

每个节点可带：

- `learning_state`
- `learning_state_reason`
- `recommended_action`
- `recommendation_reason`
- `blocked_by_prerequisite_node_ids`
- `graph_event_sources`

### 掌握度规则

- 1-29：微光，刚接触。
- 30-79：闪耀，有一定掌握。
- 80-94：璀璨，掌握良好。
- 95-100：精通。
- 复习间隔：低分 1-3 天，高分 7-14 天。

### 前端表现

- L0-L4 五级 LOD 渲染。
- 视口裁剪、RepaintBoundary、TextPainter 缓存。
- Tap 选中节点，Long Press 进入详情。
- 节点亮度与粒子表现随掌握度变化。

### 代码 / 文档证据

- 知识星图文档：`docs/01_核心模块文档/03_知识星图模块.md`
- 详细设计：`docs/02_技术设计文档/02_知识星图系统设计_v3.0.md`
- CXP-09 报告：`docs/product/parallel_closeout/CXP-09_knowledge_galaxy_REPORT_2026-05-02.md`
- 移动端知识模块：`mobile/lib/features/knowledge/`
- Knowledge Theater：`mobile/lib/features/theater/presentation/widgets/knowledge_theater_graph.dart`
- 知识节点模型：`mobile/lib/features/knowledge/data/models/`

### 需要保守表达的点

内部审计曾指出：知识图谱向 AI 主聊天上下文的注入链路需要持续修复和验证。因此路演中不要说“AI 已经完全实时读取全部星图”。更稳妥的说法是：

> 知识星图已经作为用户知识世界模型和长期学习资产存在，正在持续接入任务、复习、错因与 AI 决策链路。

## 3. 建议页面结构

**版式：中心星图 + 右侧节点详情**

左侧大图：知识星图网络  
节点颜色代表：

- 已掌握
- 待复习
- 薄弱
- 前置阻塞

右侧卡片：选中节点 `TCP 可靠传输`

卡片字段：

```text
学习状态：weak / ready_for_review
原因：最近真题中报文段推理错误
推荐动作：先做 2 道高频题，再补概念
前置阻塞：滑动窗口 / 差错检测
证据来源：任务完成、错题、文档、翻译保存
```

底部一句：

> 星图不是展示层，而是 Sparkle 判断“下一步该学什么”的世界模型。

## 4. 建议页面文案

主文案：

> 用 ChatGPT 一年，留下的大多是聊天记录；用 Sparkle 一年，留下的是关于你知识结构、错因模式和有效学习路径的可迁移资产。

证据小字：

- `LearningGraphState`
- `recommended_action`
- `graph_event_sources`
- `semantic_search`
- `spark_node`

## 5. 可选图片 prompt

```text
Create a premium dark-blue product UI illustration of a personal knowledge galaxy for a learning app. Show a clean graph of knowledge nodes around "TCP reliable transmission", with connected nodes such as subnetting, error detection, congestion control, application layer, and transport layer. Use clear node states for mastered, weak, ready for review, and blocked by prerequisite. On the right side, show a crisp inspector panel with learning state, reason, recommended next action, prerequisite blockers, and evidence sources. Use a deep navy background with subtle star-map texture, cyan and soft blue graph edges, emerald for mastered nodes, amber for weak nodes, and muted red for blockers. The image should feel like real product analytics, not fantasy astronomy. Avoid emoji, avoid cyberpunk, avoid magical galaxy art, avoid unreadable micro text.
```

## 6. 答辩口径

如果评委问“这不就是知识图谱吗”，回答：

> 我们不是单纯做知识点可视化。每个节点都带用户状态、掌握证据、推荐动作和事件来源。它服务于任务规划、复习建议、错因修复和长期迁移，是 Sparkle 的个人知识世界模型。

## 7. 不建议这样讲

- 不要把星图讲成“漂亮视觉效果”。
- 不要说“我们已经解决所有知识图谱上下文注入问题”。
- 不要在主视觉里放太多节点，保持 8-12 个关键节点即可。

---

# Appendix E：Skill Extraction / Learning Base / Seed Library

## 1. 这一页要证明什么

Sparkle 不是每次从零开始。一次目标中被验证有效的策略，会被提取、保存、复用，并能从个人策略扩展到种子库、Domain Pack 和长期成长资产。

**推荐标题：**  
Skill Extraction：从一次成功中提取可复用方法

**核心一句话：**  
Sparkle 不是只记录结果，而是把“什么策略在什么情境下有效”沉淀成可复用的策略资产。

## 2. 可以放进 PPT 的真实信息

### Skill Extraction 触发条件

在 `SkillExtractionService` 中，策略提取条件包括：

- 同一个 `policy_key` 连续有效次数达到阈值。
- 当前阈值：`effective_count >= 3`。
- 平均置信度达到门槛。
- 当前门槛：`avg_confidence >= 0.7`。
- 最近有效样本中没有负向反馈打断。

### SkillEntry 包含什么

- `skill_id`
- `scope`
- `source_policy_key`
- `strategy`
- `applicable_when`
- `evidence`
- `privacy`
- `contraindications`
- `effective_count`
- `sample_size`

### Seed Library / Content Capsules

种子库不只是内容收藏，而是“可行动的成长 starter”：

- 教学内容 → 生成学习计划。
- 练习内容 → 创建任务。
- 知识内容 → 创建知识节点草稿。
- 闪卡 → 进入复习。
- 模板 / few-shot → 用于 Aurora / Chat。
- 种子库 / 种子项 → 可安全分享到社群，并产生私有副本。

### Skill Store

用户自己的技能库：

- `UserSkill` 支持创建、更新、删除、启用 / 停用。
- 用户技能上限：`50`。
- 可 fork shared skill，进入用户私有技能库。
- 记录 `usage_count` 与 `last_activated_at`。

### Seed Bridge

`seed_bridge.py` 可把 seed item 转成 `DistilledStrategy`：

- `strategy_type`
- `applicability_scope`
- `evidence_strength`
- `diversity_score`
- `safety_audit`
- `shareability`

### 代码 / 文档证据

- Skill Extraction：`backend/app/signals/skill_extraction.py`
- Episode Logger：`backend/app/causal/episode_logger.py`
- Skill Store：`backend/app/services/skill_store/service.py`
- Seed Library：`backend/app/services/seed_library_service.py`
- Seed Bridge：`backend/app/learning/seed_bridge.py`
- CXP-10 报告：`docs/product/parallel_closeout/CXP-10_seed_library_content_capsules_REPORT_2026-05-02.md`
- 移动端技能管理：`mobile/lib/features/user/presentation/screens/skill_management_screen.dart`
- 移动端种子库：`mobile/lib/features/seed_library/`

## 3. 建议页面结构

**版式：从 Episode 到 Skill 的流水线**

```text
Episode
一次任务 / 考试过程

↓

Policy Effect
策略是否有效、置信度、用户反馈

↓

Skill Extraction
连续 3 次有效 + 置信度 >= 0.7

↓

SkillEntry
策略、适用条件、证据、禁忌

↓

Learning Base / Seed Library
下一个目标自动复用
```

右侧放一个例子：

```text
计网冲刺中有效策略：
“先做真题，再补理论”

适用场景：
deadline 短、基础不均、考试题型固定

下次迁移：
数据库期末 / 操作系统复习
```

## 4. 建议页面文案

主文案：

> 一次通过考试不只是结果。Sparkle 会追踪策略、结果和反馈，把被验证有效的方法提取成用户自己的可迁移资产。

小卡片：

- `3 次连续有效`：防止偶然成功。
- `0.7+ 置信度`：避免低质量策略沉淀。
- `applicable_when`：记录什么时候适用。
- `contraindications`：记录什么时候不该用。

## 5. 可选图片 prompt

```text
Create a premium dark-blue technical product diagram showing how a learning system extracts reusable skills from successful goal episodes. Visual flow: Episode -> Policy Effect -> Confidence Gate -> Skill Entry -> Learning Base -> Next Goal. Include a small example card: "Exam sprint strategy: practice past papers before theory review" with applicable conditions and evidence count. Use a midnight blue background, clean glass data cards, cyan pipeline arrows, soft blue labels, emerald confidence indicators, and a small amber caution tag for contraindications. The slide should look like a serious AI product strategy appendix, clean and engineering-grounded. Avoid emoji, avoid cartoon robots, avoid overcomplicated code, avoid generic database stock art.
```

## 6. 答辩口径

如果评委问“系统怎么越用越好”，回答：

> 我们不是简单保存聊天记录，而是保存策略效果。一个策略在类似场景中连续有效，且没有负向反馈，才会被提取为 SkillEntry。这样用户下次遇到类似目标时，系统不是重新猜，而是带着过去验证过的方法进入决策。

## 7. 不建议这样讲

- 不要说“系统自动学会一切”。
- 不要把 Skill 说成普通 prompt 模板。
- 不要忽略 privacy 字段，个人策略默认应是用户私有资产。

---

# Appendix F：MirrorFish / 多 Agent / SGW / 推演系统

## 1. 这一页要证明什么

Sparkle 不只在真实用户身上试错。我们建立了推演、模拟、benchmark 和 RL 脚手架，用来提前发现策略风险、验证目标路径，并持续改进系统策略。

**推荐标题：**  
MirrorFish / SGW：先在模拟世界里压力测试策略

**核心一句话：**  
在真实用户执行前，Sparkle 可以用推演和模拟系统发现失败路径、策略冲突和高风险场景，降低真实试错成本。

## 2. 可以放进 PPT 的真实信息

### Mirofish / Prediction Theater 能力

已有测试和 benchmark 中包含：

- Chat → Theater：用户说“帮我推演一下学 Python 的路径”，系统返回 prediction preview 和 deep link。
- Chat → Simulation：用户说“我想模拟一下学习场景”，系统返回 simulation preview。
- Chat → Report：用户说“生成学习表现分析报告”，系统返回 report preview。
- 支持 freeform topic，即使没有现成知识节点，也可以生成路径预览。
- 支持 hybrid semantic，将自由主题与已有知识星图节点语义映射。

### SGW v2 / RL Scaffolding

SGW 是更偏工程和研究的策略验证系统：

- Phase 0：MDP 抽象冻结。
- Phase 1：可复现 run_id、config_hash、历史数据。
- Phase 2：对话生成层重构。
- Phase 3：评估层解耦。
- Phase 4：元编排与归因闭环。
- Phase 5：通用化脚手架。
- Phase 6：观测与长期运行。
- RL Scaffolding Phase 0-8 已验收，包括 trajectories、failure_library、policy router、guardrails、rollout gate、simulation env、policy zoo。

### 代码 / 文档证据

- Mirofish benchmark：`backend/scripts/mirofish_bridge_benchmark.py`
- Mirofish 测试：`backend/tests/unit/test_mirofish_phase0_acceptance.py`
- Theater 工具：`backend/app/tools/theater_tool.py`
- Prediction Theater：`backend/app/services/theater/prediction_theater_service.py`
- Seed Extractor：`backend/app/services/simulation/seed_extractor.py`
- SGW 验收矩阵：`docs/sgw/03_acceptance_matrix.md`
- SGW Phase 0-8：`docs/sgw/06_phase0_8_acceptance.md`
- RL 代码：`scripts/sgw_v2/rl/`

## 3. 建议页面结构

**版式：真实执行前的“模拟沙盘”**

左侧：用户真实目标  

```text
“我 7 天后考计网”
```

中间：推演沙盘

```text
Persona
Goal
Constraints
Knowledge State
Candidate Strategy
Failure Paths
```

右侧：输出

```text
Prediction Preview
Simulation Preview
Report Preview
Policy Adjustment
```

底部：SGW / RL 技术底座

```text
Scenario Recipe → Simulation Env → Policy Router → Rollout Gate → Episode Report
```

## 4. 建议页面文案

主文案：

> 普通产品只能等用户失败后再改；Sparkle 希望先在模拟世界里发现失败路径，再把更稳的策略交给真实用户。

小证据块：

- `chat_to_theater`
- `chat_to_simulation`
- `chat_to_report`
- `PolicyRouter`
- `RolloutGate`
- `SimulationEnv`

## 5. 可选图片 prompt

```text
Create a premium dark-blue AI strategy simulation slide visual. Show a "digital sandbox" where a student's goal, constraints, knowledge state, and candidate strategies are simulated before real execution. Include three output panels: prediction preview, simulation preview, learning report. Add a lower technical rail with Scenario Recipe, Simulation Env, Policy Router, Rollout Gate, Episode Report. Use a deep navy / dark graphite background, subtle grid texture, cyan simulation paths, soft blue panels, emerald pass indicators, and muted amber risk markers. The style should be clean, editorial, high-end university AI product deck, not a sci-fi movie scene. Avoid robots, avoid emoji, avoid cyberpunk cities, avoid excessive hologram glow, avoid unreadable tiny labels.
```

## 6. 答辩口径

如果评委问“你们怎么验证策略有效”，回答：

> 我们有两层验证：一层是真实 benchmark，例如 SparkleGoalBench；另一层是模拟和推演，例如 Mirofish / Theater / SGW。真实用户前，系统可以先在模拟场景中检查路径、失败点和策略风险，再决定是否进入真实执行。

## 7. 不建议这样讲

- 不要说模拟能完全替代真实用户。
- 不要把 RL 说成已经完全上线自动优化用户策略。
- 不要让这页变成算法论文页，重点是“降低真实试错成本”。

---

# Appendix G：技术架构全图

## 1. 这一页要证明什么

Sparkle 是完整工程系统，不是一个套壳聊天页面。移动端、Go 网关、Python AI Engine、数据库、Redis、对象存储、事件总线、安全层和模型路由共同支撑产品体验。

**推荐标题：**  
模型能力之外，是一套目标实现系统

**核心一句话：**  
Sparkle 的核心能力来自完整系统编排，而不是单次 LLM API 调用。

## 2. 可以放进 PPT 的真实信息

### 三层架构

```text
Flutter Mobile
用户界面、任务卡、聊天、星图、社群、设置

Go Gateway
WebSocket / HTTP / JWT / Rate Limit / gRPC Bridge

Python AI Engine
Orchestration / Planning / RAG / Aurora / Signals / Tools
```

### 基础设施

- PostgreSQL + pgvector：业务数据、向量检索、知识节点。
- Redis：缓存、streams、event bus、runtime state。
- MinIO / Object Storage：用户文件、资料、资产。
- gRPC AgentService：AI 主通信协议。
- WebSocket：移动端实时聊天主链路。
- OpenClaw：外部执行层。
- 多模型路由：后续可接 DeepSeek、OpenAI 等模型，不绑定单一模型。

### 当前主聊天路径

```text
Flutter
→ /ws/chat
→ Go Gateway
→ gRPC AgentService
→ Python ChatOrchestrator
→ context / tools / model
→ stream back
```

### 代码 / 文档证据

- README：`README.md`
- 技术架构：`docs/00_项目概览/02_技术架构.md`
- Proto：`proto/agent_service.proto`
- Python gRPC：`backend/app/services/agent_grpc_service.py`
- Go Gateway：`backend/gateway/`
- Flutter：`mobile/lib/`
- WebSocket handler：`backend/gateway/internal/handler/`
- Orchestration：`backend/app/orchestration/`

## 3. 建议页面结构

**版式：系统架构大图**

上层：用户体验层

```text
Chat / Tasks / Galaxy / Community / Insights
```

中层：接入与治理层

```text
Go Gateway
JWT / WS / Rate Limit / gRPC / Error Sanitization
```

下层：智能与数据层

```text
Python AI Engine
Aurora / Causal Spine / RAG / Planning / Tools

PostgreSQL / Redis / Object Storage / Event Bus
```

右侧放“为什么这不是 wrapper”：

- 有任务系统。
- 有知识星图。
- 有社群执行层。
- 有 trace / receipt。
- 有 benchmark。
- 有安全治理。

## 4. 建议页面文案

主文案：

> 如果只是调用大模型，用户仍然要自己组织上下文、拆任务、判断执行。Sparkle 的工程系统把这些负担放进产品链路里。

技术标签：

- `Flutter Mobile`
- `Go Gateway`
- `Python AI Engine`
- `PostgreSQL + pgvector`
- `Redis Streams`
- `gRPC / WebSocket`
- `OpenClaw`

## 5. 可选图片 prompt

```text
Create a polished dark-blue system architecture diagram for an AI-native learning and goal achievement platform called Sparkle. Show three clear layers: Flutter Mobile user experience layer, Go Gateway access and governance layer, Python AI Engine intelligence layer. Connect to PostgreSQL + pgvector, Redis streams, object storage, event bus, model router, and OpenClaw execution layer. Include user-facing modules: Chat, Task Cards, Knowledge Galaxy, Community, Insights. Use a deep navy background, crisp cyan connection lines, glass-like architecture blocks, soft blue typography, and small emerald status markers for stable services. The diagram should feel like a credible engineering platform slide for a university technology competition. Avoid emoji, avoid cyberpunk, avoid decorative gradients, avoid server-room stock imagery, avoid excessive complexity.
```

## 6. 答辩口径

如果评委问“是不是大模型套壳”，回答：

> 如果只是把用户消息转发给模型，就是套壳。但 Sparkle 的关键链路包括目标状态、任务系统、知识星图、社群执行层、trace、反馈学习和安全治理。大模型是能力源之一，Sparkle 做的是把能力变成可执行系统。

## 7. 不建议这样讲

- 不要在主讲中展开完整架构图。
- 不要把多模型路由当成主要护城河。
- 不要讲太多微服务术语，答辩时按评委问题展开。

---

# Appendix H：工程验证与当前完成度

## 1. 这一页要证明什么

Sparkle 已经不是概念稿，而是有代码、有测试、有验收、有 benchmark、有可运行链路的系统。这里要给评委“项目真的做出来了”的证据。

**推荐标题：**  
不是概念：已有可运行、可测试、可继续迭代的系统底座

**核心一句话：**  
我们不只讲愿景，也用工程验证证明关键链路已经被反复压测和收口。

## 2. 可以放进 PPT 的真实信息

### 可引用硬指标

来自 `docs/benchmarks/2026-05-02_local-fv03-final.md`：

- SparkleGoalBench：`24/24` 通过。
- 总通过率：`100.0%`。
- ExamSprintBench：`12/12` 通过。
- ProjectDeliveryBench：`4/4` 通过。
- JobSearchBench：`4/4` 通过。
- MultiGoalLifeBench：`4/4` 通过。
- Gate status：`PASSED`。

来自 Aurora closeout：

- 总任务数：`15`。
- 总验收 checkbox：`74`。
- `72/74` verified。
- 完成率：`97.3%`。
- 结论：`PASS-WIP`。

来自 Phase I Exit Gate：

- Kill Switch 三态化：`12/12`。
- Mobile black-hole rate：`0.000%`。
- Core/Phase top-50 hot files 覆盖率：`100%`。
- kill-switch 家族单测：`31/31 PASS`。
- Stage 36-40 功能单测：`55/55 PASS`。

### 可引用工程规模

根据本地文件统计：

- `backend/app` 中服务 / API / signals / aurora / core / models 相关文件约 `2140` 个。
- `mobile/lib/features` 相关文件约 `844` 个。
- `backend/tests`、`mobile/test`、`scripts` 中 test / acceptance / benchmark 相关文件约 `3101` 个。

注意：这些是文件数量，不是代码行数。不要和上一版 PPT 的代码行数混用，除非重新跑精确 LOC 统计。

### 代码 / 文档证据

- Benchmark：`docs/benchmarks/2026-05-02_local-fv03-final.md`
- Aurora closeout：`docs/product/SPARKLE_AURORA_CLOSEOUT_FINAL_ACCEPTANCE_2026-05-02.md`
- Phase I Exit Gate：`docs/product/SPARKLE_AURORA_PHASE_I_EXIT_GATE_2026-04-22.md`
- 产品 gap reports：`docs/product/gap_reports/`
- 测试目录：`backend/tests/`、`mobile/test/`
- 验收脚本：`backend/scripts/`、`scripts/`

## 3. 建议页面结构

**版式：证据仪表盘**

左侧：产品截图 / 手机界面  
建议放真实产品截图，不放概念图。优先截图：

1. 任务卡页面。
2. Aurora 对话 / 校准回执。
3. 知识星图。
4. 社群 / 责任伙伴。

右侧：4 个证据数字

```text
24/24
SparkleGoalBench 全场景通过

12/12
ExamSprintBench 通过

72/74
Aurora closeout verified

12/12
Kill switch tri-state
```

底部：一条说明

> 这些数字不是为了炫工程量，而是证明系统已经进入可验证、可迭代阶段。

## 4. 建议页面文案

主文案：

> 一个路演项目最怕只有愿景。Sparkle 当前最重要的证据是：我们已经把产品链路、工程治理和压力场景验证接起来了。

辅助文案：

- `ExamSprintBench` 对应北极星考试救急。
- `SparkleGoalBench` 扩展到项目交付、求职、多目标生活。
- `Aurora Closeout` 证明关键体验和安全治理已收口。
- `Phase I Exit Gate` 证明进入下一阶段不是拍脑袋。

## 5. 可选图片 prompt

这页最好不用 AI 图，优先使用真实截图。如果必须生成概念图：

```text
Create a premium dark-blue product evidence dashboard slide for an AI learning app. Show one realistic mobile app screenshot mockup on the left with task card, countdown, progress, and knowledge graph. On the right, show four clean evidence metrics: 24/24 SparkleGoalBench, 12/12 ExamSprintBench, 72/74 Aurora closeout verified, 12/12 kill switch tri-state. Use a midnight blue background, dark glass metric cards, electric cyan numerals, soft blue labels, and emerald verification marks. The mood should be credible, product-real, and competition-ready, not marketing hype. Avoid emoji, avoid generic SaaS cards, avoid excessive neon, avoid claiming the mockup is a real screenshot, avoid unreadable small text.
```

## 6. 答辩口径

如果评委问“这些 benchmark 是什么”，回答：

> 它们是我们为目标实现系统设计的本地场景验证，不是公开行业 benchmark。我们用极端目标场景检查系统是否保持 spine integrity、用户自主性、长期模型不污染、策略不回退。它回答的是：这个系统在我们定义的关键目标链路里是否能稳定跑通。

如果评委追问“是否等于真实用户效果”，回答：

> 不等于。Benchmark 证明工程链路和策略约束能跑通，真实效果还需要校园试点验证 PMF。这也是我们下一阶段从北邮试点开始的原因。

## 7. 不建议这样讲

- 不要把本地 benchmark 说成行业权威 benchmark。
- 不要把概念截图说成真实截图。
- 不要只放数字不解释语境。

---

# 附录页之间的推荐顺序

建议顺序仍然是：

1. 社群 / 责任伙伴
2. 安全 / 隐私 / 可追溯
3. Aurora
4. 知识星图
5. Skill Extraction / Learning Base
6. MirrorFish / SGW
7. 技术架构
8. 工程验证

如果答辩只有一个问题，优先跳转：

| 评委问题 | 跳转页 |
|---|---|
| “你们和 ChatGPT / DeepSeek 有什么区别？” | C Aurora 或 G 技术架构 |
| “长期成长怎么证明？” | D 知识星图 + E Skill Extraction |
| “AI 建议可信吗？” | B 安全 / 可追溯 |
| “用户真的会坚持用吗？” | A 社群 / 责任伙伴 |
| “你们做到什么程度？” | H 工程验证 |
| “策略怎么验证？” | F MirrorFish / SGW |
| “是不是大模型套壳？” | G 技术架构 + B 可追溯 |

---

# 最后提醒

附录页可以比主线页更密，但不能失控。每页最多放：

- 1 个主判断；
- 1 个核心机制图；
- 3-5 个真实证据；
- 1 句答辩口径。

不要把所有代码路径都放进 PPT 页面正文。代码路径适合放在备注、讲稿或极小号证据脚注里。评委真正需要看到的是：这些技术不是名字，而是已经嵌入了用户目标、执行反馈、长期学习和可信治理的完整系统。
