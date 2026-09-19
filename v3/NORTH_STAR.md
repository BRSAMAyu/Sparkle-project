# Sparkle V3 North Star

## 1. 产品定义

**Sparkle 是一个面向长期成长目标的 Adaptive Human–AI Action System。**

它持续理解：
- 用户真正想完成什么；
- 当前处于目标轨迹的哪里；
- 现在为什么卡住；
- 过去什么帮助对这个用户在这个情境中有效；
- 下一步应由用户、AI，还是二者协作完成；
- 这次行动是否真的产生了目标相关结果。

然后把这些结果再次写回系统，形成：

`Evidence → Understanding → Decision → Intervention → Action → Outcome → Better Understanding`

这就是 Sparkle 的数据飞轮。

## 2. 用户问题

Sparkle 不解决“世界上缺少答案”。它解决的是 **intention–action gap**：用户往往已经有目标，却在开始、持续、遇到现实约束、判断下一步以及复盘时失败。

首发 wedge 不是“所有人”，而是 **self-directed builders**：有一个持续数天到数月、有真实产出、需要边学边做并不断调整的大学生/年轻创造者，例如：
- 比赛项目；
- 科研/论文；
- 技能学习与作品集；
- side project；
- 内容创作；
- 考试/课程项目。

## 3. 产品承诺

用户长期使用 Sparkle，应感受到五个递进层次：

### P1 — 我现在知道下一步是什么
不是一个长计划，而是一个做得下去、完成后有真实价值的 Smallest Useful Step。

### P2 — 它知道我为什么卡住
Sparkle 不把“没做”粗暴归因为懒惰或能力不足，而能区分时间、难度、入口、成果标准、材料、情绪负荷、依赖、目标变化等不同 friction。

### P3 — 它能和我一起做，而不是只告诉我做
Action 明确 Human / Agent / Hybrid：
- 需要用户形成能力/判断/体验的部分归用户；
- 可机械化、可检索、可执行的部分交给 Agent；
- 高价值场景默认 Hybrid，AI 降低摩擦但不偷走目标本身。

### P4 — 我不用重复解释，它真的越来越懂我
“懂”不是记住更多聊天，而是过去纠正、偏好、成果与失败会在**恰当情境**改变后续决策；无关、过期、撤销的信息不会被使用。

### P5 — 我信任它
用户能知道：Sparkle 为什么这样建议、用了哪些个人信息、哪些只是推断，并能纠正/删除；写操作、Agent 执行、失败和恢复不撒谎。

## 4. Sparkle Moment

V3 最关键的体验不是“第一次看到星图”，而是：

> 用户带着真实目标卡住 → Sparkle 用极少交互识别关键 friction → 给出一个仍推进目标的行动 → 明确人机分工 → 用户确认 → 系统真实执行/进入行动 → 产生可见结果 → 后续一次相关情境中合理复用刚才学到的经验。

这个闭环比任何单独页面都重要。

## 5. Aurora 的角色

Aurora 不是聊天人格，也不是提醒模块。

Aurora = **Adaptive Control Layer + Relationship Layer**：
- 观察 State；
- 决定是否需要干预；
- 选择 intervention；
- 决定 Human/Agent/Hybrid；
- 选择所需 Context 与 Cognitive Tier；
- 产生可解释的 Proposal；
- 从 outcome 与 correction 更新受限策略；
- 决定什么时候保持安静。

模型拥有语义判断自由，但系统边界确定：权限、事务、删除、计费、用户隔离、安全、幂等、审计不可由模型自由改变。

## 6. V3 的技术护城河

不是“我们也有 Agent / RAG / Memory”，而是以下组合真正工作：

1. **User World Model**：State / Memory / Knowledge / Events 分离且来源可追溯；
2. **Context Compiler**：以决策为中心构造最小高信号上下文，而非历史全塞；
3. **Conflict Resolver**：明确处理用户事实、偏好、行为观察、推断之间的冲突；
4. **Experience Memory**：记录“什么情境下什么干预有效”，而非只保存人格标签；
5. **Aurora Policy**：规则约束 + LLM 判断 + Experience Memory，支持 bounded plasticity；
6. **Human–AI Allocation**：显式优化“谁做什么”，保护 cognitive ownership；
7. **Outcome Ledger**：真实成果与行动结果成为未来决策证据；
8. **Trust Layer**：来源、解释、纠偏、删除、审计、恢复全部贯穿 UI 与 runtime。

## 7. 产品表面原则

V3 不再把 42 个 feature 都当一级产品。

核心心智模型保持五 Tab 以降低迁移风险，但重新解释：
- **首页**：Today Cockpit — 现在最值得做什么；
- **任务**：Goals & Actions — 目标轨迹与行动；
- **对话**：Aurora Conversation — 理解、澄清、协作、执行；
- **星图**：Outcome & Knowledge Graph — 已形成的知识/成果关系；
- **我的**：Reflection & Control — 我取得了什么、Sparkle 如何理解我、隐私与控制。

Focus / Calendar / Error Book / Vocabulary / Translation / Knowledge / Documents 等成为 Goal Context 中按需出现的能力，而不是逼用户学习 App 架构。

## 8. 设计气质

**Calm / Warm / Precise / Alive / Trustworthy**。

视觉方向：纸感书院 + 现代 AI；星图可以保留独特暗色宇宙视觉，但核心工作流避免粒子、渐变、glow、confetti 抢夺信息层级。

“温度”来自：
- 对状态的理解；
- 恰当时机的语言；
- 不打扰；
- 允许失败；
- 可撤回；
而不是动效总量。

## 9. V3 不做什么

- 不为了代码沉没成本把所有旧模块放回主界面；
- 不把“理解度 75%”作为没有定义的神秘准确数字；
- 不把用户行为静默升级为人格事实；
- 不把所有 Memory 都召回给模型；
- 不公开 chain-of-thought；等待态只展示可验证阶段；
- 不让 AI 替用户完成本该形成能力的核心动作；
- 不用模型做权限、TTL、写库、幂等、计费等确定性工作；
- 不用假统计/seed 数据冒充真实用户结果；
- 不因模型更强就取消 guard / evaluator / simulator；
- 不上 RL 假装“自学习”，V3 先把可解释的 bounded adaptation 做对。
