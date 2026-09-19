# V3 Frontier Research Digest → Engineering Implications

> 本文不是论文综述，而是只保留会改变 Sparkle 设计的研究/产业信号。具体来源见 `SOURCE_REGISTER.md/json`。

## 1. Context engineering > prompt stuffing
Anthropic 2025 的 context engineering 指南强调 context 是有限资源，目标是选择高信号最小集合，并讨论 JIT context、compaction、结构化 note、多 Agent。对 Sparkle：Context Compiler 必须成为一等基础设施，而非把 profile+memory+RAG 全塞 prompt。

## 2. Memory 的难题从 recall 转向适用性
2026 OP-Bench 显示 Memory 会导致 irrelevance/repetition/sycophancy 型过度个性化；Personalize-then-Store 指出不同用户值得记的内容不同，storage gating 仍是难题。
对 Sparkle：加入 storage gate、scope、Self-ReCheck、overpersonalization eval；“更多 memory”不作为 KPI。

## 3. Long-term personalization 应以 experience/outcome 为中心
近期 agent-memory 研究趋势从 Storage → Reflection → Experience。对 Sparkle：Experience Memory 记录 situation/intervention/outcome，而不是只生成更长 persona summary。

## 4. Human–AI delegation 不是“能自动就自动”
2026 delegation 研究把 authority/responsibility/accountability/boundaries/trust 放在中心；HCI 研究也显示人给人类同事的是高层意图，对 AI 更倾向 rigid instructions，理想系统需要 checkpoints/test runs。
对 Sparkle：Human/Agent/Hybrid 作为 Action 一级属性，保护 cognitive ownership，高风险必须审批。

## 5. Event-triggered background agents 已成为产业基线
Notion Custom Agents 已支持 event-triggered background work；通用 AI 产品支持 schedule/monitor/background agent。Sparkle 的差异不能只是“会主动/会 Agent”，而要在长期 goal state 与 intervention quality。

## 6. Goal pursuit 的行为科学依据
Implementation intentions 元分析（94 个独立测试）表明把目标落实为 when/where/how 的 if-then 行动能改善目标达成。对 Sparkle：目标价值不止“计划”，还要处理 action initiation、shielding、失败路线 disengage、现实变化下重规划。

## 结论
V3 技术 moat 不是新名词，而是：
`state truth + selective context + appropriate memory + calibrated delegation + trustworthy execution + outcome learning` 在真实产品闭环中同时成立。
