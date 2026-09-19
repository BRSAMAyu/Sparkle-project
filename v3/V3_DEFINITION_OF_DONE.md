# Sparkle V3 — Definition of Done

> V3 DONE 不是“任务卡都关闭”，而是下面用户级、系统级与运行级证据同时成立。

## Gate V3-0 — Truth
- 42 个 feature 有唯一 portfolio 状态：CORE / CONTEXTUAL / LABS / HIDDEN / RETIRE；不存在用户可达的半成品入口。
- 所有核心统计数字都有数据 lineage；mock/seed/demo 明确隔离且不会进入真实缓存或真实用户分析。
- 当前模型、embedding、ASR/TTS、OCR 等能力由 runtime probe 得到，不凭配置文件宣称可用。

## Gate V3-1 — First Meaningful Value
- 清空状态的新用户可在 **≤3 分钟**内理解 Sparkle 的价值并完成首次 meaningful action proposal；
- 首屏不要求理解 Aurora、Memory、Galaxy 等内部名词；
- “体验示例”与“开始我的目标”严格区分，demo persona 不冒充用户历史；
- 核心 onboarding / home / chat 无 P0/P1 UX 阻断，A/B 级视觉问题清零。

## Gate V3-2 — Stuck → Useful Action
- 20 个代表性 friction scenario 中 ≥18 个产生与真实原因一致的 intervention；
- 输出必须包含 outcome、smallest useful step、为什么现在做、完成证据、人机执行模式；
- 不允许用无限缩小任务制造完成感；
- 高风险或信息不足时能 clarify / abstain。

## Gate V3-3 — Human–AI Collaboration
- Human / Agent / Hybrid 分配离线评测 ≥90% 符合 rubric；
- 应由人形成能力/判断的步骤不会被 Agent 自动替代；
- 高风险不可逆行为 autonomous execution = 0；
- Hybrid handoff 的 pending / awaiting_user / resumed / cancelled 状态真实可恢复。

## Gate V3-4 — Personalization That Helps
- Memory / user model 的有效使用 precision ≥95%；
- expired / revoked / wrong-user / wrong-scope memory 使用次数 = 0；
- over-personalization（irrelevance / repetition / sycophancy）≤5%；
- 纠正一条用户理解后，相关 future decision 必须改变；不相关 scenario 不改变；
- 用户删除后，retrieval / cache / context / in-flight continuation 均不能继续使用旧信息；
- paired evaluation 中 personalized decision 相比同信息非个性化基线目标 **+15pp**；达不到必须报告真实结果而非改口径。

## Gate V3-5 — Data Flywheel
- 每个 intervention 都能连接：context → decision → execution → outcome → evidence update；
- understanding_depth 不再是单一神秘分数，而有 coverage / correctness / scope precision / freshness / utility 五个内部维度；
- 用户侧不显示未经校准的精确百分比；
- 能回答“过去什么帮助对这个用户在这个情境有效”，并区分相关性与因果性。

## Gate V3-6 — Trustworthy Agent Runtime
- 100 个代表性 run ≥99 个正确进入 terminal/awaiting 状态；
- **false success = 0、cross-user access = 0、duplicate side effect = 0**；
- app 关闭/重开、WebSocket 重连、worker restart 后 run 可查询并恢复；
- cancel / timeout / retry / unknown outcome 都有明确用户语义；
- tool call 有 run_id、permission decision、idempotency key、result/receipt、latency/cost。

## Gate V3-7 — Experience Quality
- L2–L5 UI/UX 审查完成：核心旅程 A/B issue=0；长尾可达页面 A issue=0；
- loading / empty / error / offline / permission denied / model unavailable / conflict / awaiting user / partial result 等状态完整；
- Android/Web/macOS 核心 golden journey 均通过；
- 视觉回归有基线截图与 diff，不以“代码看起来对”代替实际渲染。

## Gate V3-8 — Performance & Cost
候选目标（必须以真实 provider 基线校准）：
- 本地确定性交互 p95 ≤300ms；
- L0 no-model 路径 p95 ≤500ms；
- L1 fast semantic path first meaningful feedback p50 ≤2.5s / p95 ≤5s；
- L2 deep decision 在 500ms 内给阶段反馈，最终 p95 ≤15s；
- L3 Agent Run 创建/ACK ≤1s，后续异步、可恢复；
- 没有任何 UI 因隐藏模型调用无反馈冻结 >2s；
- 每个 tier 有 token/cost/latency/quality 账本。

若 qwen3.8-flash 或当期 provider 无法满足，必须重新定真实 SLO，并通过 fast lane/缓存/预计算/异步改善；禁止通过隐藏等待伪造性能。

## Gate V3-9 — Commercial Launch Engineering
- HTTPS 远程环境可部署；移动/Web 可配置远端 endpoint；密钥只在服务端；
- flame/gameification 与 entitlement/paid plan 解耦；
- quota、成本、降级、kill switch、rollback 可观测；
- 数据导出/删除/Memory 控制有效；
- backup/restore 演练成功；
- release candidate 有一键 smoke + rollback runbook。

## Gate V3-10 — North Star Measurement
North Star：**Weekly Valuable Progress Loops (WVPL)**

定义：一个活跃用户在 7 天内至少完成 1 次 `goal-linked action → observable outcome/evidence → state update` 的闭环。

必须同时报告：
- active users 分母；
- WVPL users；
- loops/user；
- outcome 类型；
- Human/Agent/Hybrid；
- 是否由 proactive intervention 启动；
- 不得把 chat/send/task-click 当作成果闭环。
