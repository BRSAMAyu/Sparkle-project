# V3 决策冻结表

## D01 名称
产品统一称 **Sparkle**。Cosmos 仅可作为历史/工程内部名，不出现在核心用户价值描述里。

## D02 V3 的单位是 User Value Loop，不是 Feature
任务组织按 Journey/Aurora/Memory/Context/Action/Data/UX 等跨模块目标，feature 目录仅作为实现位置。

## D03 首发用户
优先大学生 self-directed builders：比赛、科研、课程项目、作品集、技能成长。底层系统允许更 general，但 V3 不通过“所有人都有目标”推导“所有人都是用户”。

## D04 五 Tab 保留但语义重构
首页=Today；任务=Goals & Actions；对话=Aurora；星图=Outcome/Knowledge Graph；我的=Reflection & Control。

## D05 Seed Persona 只能是显式体验模式
游客种子人生保留为强第一印象资产，但 UI 必须明确“体验示例”；真实 onboarding 不伪造历史、连续天数、画像或成果。

## D06 understanding 不能作为神秘单百分比
内部可计算 multidimensional understanding state；用户侧展示“已确认/待确认/最近更新/依据/可纠正”，除非百分比经过明确可解释的校准。

## D07 Aurora = Adaptive Control + Relationship Layer
Aurora 负责决策与关系呈现；不拥有数据库 root 权限，不自行修改生产代码、schema、安全与计费规则。

## D08 Bounded Plasticity
允许自适应：交互颗粒度、是否澄清、解释方式、intervention preference、proactive cadence、Human/Agent allocation preference。
禁止自主改变：permissions、privacy、billing、user isolation、delete semantics、transaction rules、secrets、production code。

## D09 State / Memory / Knowledge / Events 四分
- Current State：业务真值；
- Memory：用户相关可复用经验；
- Knowledge：外部/用户材料；
- Events：历史发生记录。
任何检索与 Context 都必须保留来源类型。

## D10 Memory 先硬过滤再语义相关
user/status/scope/TTL/permission/purpose 先确定性过滤，之后才 embedding/rerank/LLM recheck。禁止从全量 memory 做一次 top-k 就直接注入。

## D11 Explicit correction 权重最高
同 scope 下：当前明确陈述/纠正 > 更新的明确偏好 > verified system facts > outcomes/observations > inference。行为观察不得静默覆盖明确偏好。

## D12 加 over-personalization guard
Memory “能召回”不等于“该使用”。每次 personalized output 对 retrieved memory 进行 relevance/necessity recheck，防止无关、重复、迎合式引用。

## D13 Human / Agent / Hybrid 一级属性
Action plan 的每个 step 都必须标 `execution_mode` 与 `cognitive_ownership`。默认不以“Agent 能做”推导“Agent 应做”。

## D14 不暴露 hidden chain-of-thought
可以展示可验证工作阶段、tool progress、来源、decision rationale 摘要；不得把 provider reasoning_content 当产品“思考过程”原样暴露。

## D15 Cognition Ladder
L0 deterministic → L1 fast semantic → L2 deliberate decision → L3 agent run。只有语义不确定性需要 LLM；CRUD/权限/TTL/幂等/计费/路由固定规则不用生成模型。

## D16 Agent Runtime 唯一
现有 OpenClaw 等执行模块只可适配到统一 Runtime/Tool Registry，不允许再建第二套 Agent 真值、run state 或权限系统。

## D17 游戏化降权
Achievement 可保留安静反馈；Shop/Photon 从核心旅程降级；Leaderboard 默认隐藏。`is_pro = flame_level >= 3` 必须拆除，商业 entitlement 独立。

## D18 社群不是公共 feed
V3 社群聚焦小队/冲刺/成果 check-in/反馈；私人 Memory 与画像默认不可共享。

## D19 长尾能力 contextualize
Focus/Calendar/ErrorBook/Vocabulary/Translation/Knowledge/Documents 通过 Goal/Action Context 出现。Mirofish/Theater/Simulation 默认 Labs/HIDDEN，除非 V3 测试证明独特价值。

## D20 数据真实性优先
统计 mock 不能进入真实缓存或真实产品表面。无法接真实 API 就隐藏，不用“看起来丰富”换取不可信。

## D21 UI 气质
Calm / Warm / Precise / Alive / Trustworthy；装饰不压过信息。核心流程减少 gradient/particle/glow/confetti。

## D22 V3 Agent-only
任务包不分配人类角色，不等待人工 sign-off。需要产品判断时按本文件已冻结的决策执行；真正外部凭据/账号/法律动作缺失则 BLOCKED，但继续其他任务。
