# V3 Task Index

> 只包含 V3 新增任务。V2/V2.5 已完成卡不重复。

Total: **107 V3 tasks**. Initial parallel frontier: B-01..B-06.

## BASELINE (6)

|ID|Title|Deps|Resource|Risk|Gate|
|---|---|---|---|---|---|
|[B-01](cards/B-01.md)|42 模块产品生死簿与可达性真相|-|LIGHT|medium|V3-0|
|[B-02](cards/B-02.md)|数据真实性、Mock 污染与指标 Lineage 基线|-|LIGHT|high|V3-0|
|[B-03](cards/B-03.md)|跨端 Journey Simulator Harness 基线|-|HEAVY|medium|V3-0|
|[B-04](cards/B-04.md)|V3 视觉基线截图与 L2–L5 Review Harness|-|HEAVY|medium|V3-0|
|[B-05](cards/B-05.md)|当前模型、Embedding、语音/OCR 与成本能力 Probe|-|MEDIUM|high|V3-0|
|[B-06](cards/B-06.md)|V3 核心实体映射与重复真源审计|-|LIGHT|high|V3-0|

## UX (10)

|ID|Title|Deps|Resource|Risk|Gate|
|---|---|---|---|---|---|
|[U-01](cards/U-01.md)|核心设计表面 Inventory 与 Component 收敛计划|B-01,B-04|LIGHT|medium|V3-4|
|[U-02](cards/U-02.md)|Calm/Warm 设计语言与低刺激模式落地|U-01|HEAVY|medium|V3-4|
|[U-03](cards/U-03.md)|Aurora / Memory “Sparkle 对我的理解”核心交互|U-01,M-08|HEAVY|high|V3-4|
|[U-04](cards/U-04.md)|Proposal / Execution / Hybrid Handoff 交互组件|U-01,X-03|HEAVY|high|V3-4|
|[U-05](cards/U-05.md)|首页/Goal/Chat 三屏 L2 产品化重构|U-01,J-03,J-05|HEAVY|medium|V3-4|
|[U-06](cards/U-06.md)|L4 状态完备性注入与统一错误/等待语义|U-04,U-05|HEAVY|medium|V3-4|
|[U-07](cards/U-07.md)|长尾 Feature Contextualization 与导航减负|B-01,U-05|HEAVY|medium|V3-4|
|[U-08](cards/U-08.md)|Accessibility 全链升级|U-05|HEAVY|medium|V3-4|
|[U-09](cards/U-09.md)|L5 三端视觉/交互一致性 Diff|B-03,B-04,U-06,U-08|HEAVY|medium|V3-4|
|[U-10](cards/U-10.md)|全产品文案与术语终审|U-03,U-05,U-07|LIGHT|medium|V3-4|

## DATA (8)

|ID|Title|Deps|Resource|Risk|Gate|
|---|---|---|---|---|---|
|[D-01](cards/D-01.md)|统一 Event / Evidence Lineage Contract|B-02,B-06|MEDIUM|high|V3-3|
|[D-02](cards/D-02.md)|Outcome Ledger 与 Evidence Type 正规化|D-01|MEDIUM|high|V3-3|
|[D-03](cards/D-03.md)|Understanding 五维内部度量与校准|D-01,M-01|MEDIUM|medium|V3-3|
|[D-04](cards/D-04.md)|真实 Analytics 接线并清除生产 Mock 缓存污染|B-02,D-01|HEAVY|high|V3-0|
|[D-05](cards/D-05.md)|Intervention → Outcome 分析管线|D-02,A-02|MEDIUM|medium|V3-3|
|[D-06](cards/D-06.md)|WVPL 北极星查询与事实 JSON|D-02,D-04|MEDIUM|medium|V3-3|
|[D-07](cards/D-07.md)|Evidence-driven Insights 产品重构|D-03,D-04,D-05,U-05|HEAVY|medium|V3-3|
|[D-08](cards/D-08.md)|数据飞轮纵向证明与 Regression Dashboard|D-06,D-07,A-08|HEAVY|medium|V3-3|

## MEMORY (10)

|ID|Title|Deps|Resource|Risk|Gate|
|---|---|---|---|---|---|
|[M-01](cards/M-01.md)|Memory V3 实体映射与 Epistemic Types|B-06|MEDIUM|high|V3-2|
|[M-02](cards/M-02.md)|Personalized Storage Gate — 该不该记|M-01|MEDIUM|medium|V3-2|
|[M-03](cards/M-03.md)|Scope/TTL/Purpose 确定性预筛|M-01|MEDIUM|high|V3-2|
|[M-04](cards/M-04.md)|Memory Conflict Resolver 接线|M-03,D-01|MEDIUM|high|V3-2|
|[M-05](cards/M-05.md)|Over-personalization Self-ReCheck|M-03,C-03|MEDIUM|medium|V3-2|
|[M-06](cards/M-06.md)|Experience Memory Projector|M-02,D-05|MEDIUM|medium|V3-3|
|[M-07](cards/M-07.md)|Correction/Delete/Revocation + Memory Epoch 终局|M-01|MEDIUM|critical|V3-2|
|[M-08](cards/M-08.md)|Memory Provenance/Scope 用户 API|M-04,M-07|MEDIUM|high|V3-2|
|[M-09](cards/M-09.md)|Memory Longitudinal / Adversarial 评测套件|M-05,M-06,M-07|MEDIUM|medium|V3-2|
|[M-10](cards/M-10.md)|Memory/Aurora UI 全链集成|M-08,U-03,M-09|HEAVY|high|V3-4|

## CONTEXT (8)

|ID|Title|Deps|Resource|Risk|Gate|
|---|---|---|---|---|---|
|[C-01](cards/C-01.md)|DecisionContext / ContextPack 契约冻结|B-06|MEDIUM|high|V3-2|
|[C-02](cards/C-02.md)|State/Memory/Knowledge/Events 四分适配层|C-01,M-01,D-01|MEDIUM|medium|V3-2|
|[C-03](cards/C-03.md)|Context 硬过滤→语义检索 Pipeline|C-02,M-03|MEDIUM|high|V3-2|
|[C-04](cards/C-04.md)|RAG Placement/Citation/Version 正确性|C-02,E-05|MEDIUM|medium|V3-2|
|[C-05](cards/C-05.md)|Conflict Resolver 注入 Context 与 Clarification|C-02,M-04|MEDIUM|medium|V3-2|
|[C-06](cards/C-06.md)|Context Budget / JIT / Compaction|C-03,C-04|MEDIUM|medium|V3-2|
|[C-07](cards/C-07.md)|Context Cache 版本/Memory Epoch/Policy Version 正确性|C-03,M-07|MEDIUM|critical|V3-2|
|[C-08](cards/C-08.md)|Context Observability + Decision Utility Eval|C-05,C-06,C-07|MEDIUM|medium|V3-2|

## ACTION (10)

|ID|Title|Deps|Resource|Risk|Gate|
|---|---|---|---|---|---|
|[X-01](cards/X-01.md)|ActionPlan V3 契约：Outcome/Execution/Cognitive Ownership|B-06|MEDIUM|high|V3-2|
|[X-02](cards/X-02.md)|Human/Agent/Hybrid Allocation Policy|X-01|MEDIUM|high|V3-2|
|[X-03](cards/X-03.md)|Action Proposal Diff/Authorization 统一适配|X-01|MEDIUM|critical|V3-2|
|[X-04](cards/X-04.md)|Human Action Flow + Completion Evidence|X-03|HEAVY|medium|V3-2|
|[X-05](cards/X-05.md)|Unified Agent Run 持久化状态机|X-01,D-01|MEDIUM|critical|V3-2|
|[X-06](cards/X-06.md)|Tool Registry Permission/Idempotency/Budget|X-05|MEDIUM|critical|V3-2|
|[X-07](cards/X-07.md)|Hybrid Handoff / Awaiting User / Resume|X-02,X-05,U-04|HEAVY|high|V3-2|
|[X-08](cards/X-08.md)|Outcome Capture 与 Goal State 回写|X-04,X-05,D-02|MEDIUM|high|V3-3|
|[X-09](cards/X-09.md)|Agent Failure/Cancel/Unknown Outcome/Recovery|X-05,X-06|HEAVY|critical|V3-5|
|[X-10](cards/X-10.md)|Action Engine E2E Evaluation|X-07,X-08,X-09,A-04|HEAVY|medium|V3-5|

## AURORA (8)

|ID|Title|Deps|Resource|Risk|Gate|
|---|---|---|---|---|---|
|[A-01](cards/A-01.md)|AuroraDecision 契约与现有 Runtime 映射|B-06,C-01,X-01|MEDIUM|high|V3-2|
|[A-02](cards/A-02.md)|Intervention Catalog + Policy Engine V1|A-01|MEDIUM|medium|V3-2|
|[A-03](cards/A-03.md)|Friction Diagnosis + Sufficiency / One Best Question|A-02,C-03|MEDIUM|medium|V3-2|
|[A-04](cards/A-04.md)|Aurora Human/Agent/Hybrid 联合决策|A-02,X-02|MEDIUM|high|V3-2|
|[A-05](cards/A-05.md)|Bounded Policy Patches / Adaptive Preferences|A-02,M-06,D-05|MEDIUM|high|V3-3|
|[A-06](cards/A-06.md)|Aurora “Why this?” / Calibration Receipt|A-03,M-08,U-03|HEAVY|high|V3-4|
|[A-07](cards/A-07.md)|Comeback + Low-stimulation Relationship Policies|A-02,U-02|HEAVY|medium|V3-4|
|[A-08](cards/A-08.md)|Aurora Longitudinal / Ablation Evaluation|A-03,A-04,A-05,A-06,A-07,M-09,C-08|HEAVY|medium|V3-3|

## JOURNEY (8)

|ID|Title|Deps|Resource|Risk|Gate|
|---|---|---|---|---|---|
|[J-01](cards/J-01.md)|First 3 Minutes 当前体验实测与机会图|B-01,B-03,B-04|HEAVY|medium|V3-1|
|[J-02](cards/J-02.md)|Onboarding：Value Before Profile|J-01,U-01|HEAVY|medium|V3-1|
|[J-03](cards/J-03.md)|Today Cockpit 重新定义主入口|J-01,U-01|HEAVY|medium|V3-1|
|[J-04](cards/J-04.md)|First Meaningful Action 端到端|J-02,J-03,A-03,X-03|HEAVY|medium|V3-1|
|[J-05](cards/J-05.md)|“我卡住了”旗舰恢复旅程|J-03,A-03,U-01|HEAVY|medium|V3-2|
|[J-06](cards/J-06.md)|Hybrid Flagship Journey：AI 降摩擦但不偷走目标|J-05,X-07|HEAVY|medium|V3-2|
|[J-07](cards/J-07.md)|Return / Stale Plan / Comeback Recovery|J-06,A-07|HEAVY|medium|V3-3|
|[J-08](cards/J-08.md)|Goal Completion → Reflection → Trajectory|J-06,D-02,G-02|HEAVY|medium|V3-3|

## AI (8)

|ID|Title|Deps|Resource|Risk|Gate|
|---|---|---|---|---|---|
|[E-01](cards/E-01.md)|Cognition Ladder 当前路由映射|B-05,B-06|LIGHT|medium|V3-1|
|[E-02](cards/E-02.md)|Fast Semantic / Deliberate Decision 能力路由|E-01|MEDIUM|high|V3-1|
|[E-03](cards/E-03.md)|实时 Stage Events 与首反馈体验|E-02,U-04|HEAVY|medium|V3-4|
|[E-04](cards/E-04.md)|Aurora/Action/Memory 专项模型 Eval 与 Prompt 收敛|E-02,A-02,M-02|MEDIUM|high|V3-2|
|[E-05](cards/E-05.md)|Embedding / Hybrid Retrieval 生产接入|B-05|MEDIUM|high|V3-2|
|[E-06](cards/E-06.md)|Async Batch Cognitive Worklane|E-01,D-01|MEDIUM|medium|V3-3|
|[E-07](cards/E-07.md)|Quality/Latency/Cost Adaptive Routing + Health Fallback|E-02,E-04,B-05|MEDIUM|high|V3-6|
|[E-08](cards/E-08.md)|AI Stack 集成 Bench：Quality × TTFT × Cost × Context|E-03,E-04,E-07,C-08|HEAVY|medium|V3-7|

## PROACTIVE (6)

|ID|Title|Deps|Resource|Risk|Gate|
|---|---|---|---|---|---|
|[P-01](cards/P-01.md)|Event-trigger + Suppression Pipeline|A-02,D-01|MEDIUM|medium|V3-5|
|[P-02](cards/P-02.md)|NO_ACTION / Proactive Relevance Decision|P-01,A-03|MEDIUM|medium|V3-5|
|[P-03](cards/P-03.md)|Proactive Suggestion UX|P-01,U-05|HEAVY|medium|V3-5|
|[P-04](cards/P-04.md)|低风险 Auto-execute 授权模型|P-01,X-06|MEDIUM|critical|V3-5|
|[P-05](cards/P-05.md)|Proactive Longitudinal Evaluation|P-02,P-03,P-04,M-09|MEDIUM|medium|V3-5|
|[P-06](cards/P-06.md)|Notification Burden / Quiet / Low-stimulation 终局|P-03,A-07|HEAVY|medium|V3-5|

## GALAXY (5)

|ID|Title|Deps|Resource|Risk|Gate|
|---|---|---|---|---|---|
|[G-01](cards/G-01.md)|Galaxy Mastery 从“学习分钟”升级 Evidence-aware|B-01,D-02|MEDIUM|medium|V3-3|
|[G-02](cards/G-02.md)|Artifact/Outcome → Galaxy/Trajectory 接线|G-01,X-08|MEDIUM|medium|V3-3|
|[G-03](cards/G-03.md)|Galaxy Goal-focused UX 重设计|G-01,U-05|HEAVY|medium|V3-4|
|[G-04](cards/G-04.md)|Galaxy 对 Correction/Delete/Version 的一致性|G-02,M-07|MEDIUM|high|V3-3|
|[G-05](cards/G-05.md)|Galaxy 性能/手势/视觉终验|G-03,G-04,U-09|HEAVY|medium|V3-4|

## COMMUNITY (5)

|ID|Title|Deps|Resource|Risk|Gate|
|---|---|---|---|---|---|
|[S-01](cards/S-01.md)|Community Realtime/Read-model 真相复测|B-01,B-03|HEAVY|medium|V3-5|
|[S-02](cards/S-02.md)|Community Context Privacy Boundary|S-01,M-01|MEDIUM|critical|V3-5|
|[S-03](cards/S-03.md)|Squad/Sprint/Check-in 产品表面收敛|S-01,U-05|HEAVY|medium|V3-5|
|[S-04](cards/S-04.md)|Community Artifact Feedback → Outcome/Evidence|S-03,D-02|MEDIUM|medium|V3-5|
|[S-05](cards/S-05.md)|Community Reconnect/Retract/Two-account E2E|S-02,S-03,S-04|HEAVY|high|V3-5|

## OPS (7)

|ID|Title|Deps|Resource|Risk|Gate|
|---|---|---|---|---|---|
|[O-01](cards/O-01.md)|公网 Staging HTTPS/WSS 一键部署|B-06|HEAVY|high|V3-6|
|[O-02](cards/O-02.md)|End-to-End Trace / Metrics Spine|D-01,B-05|MEDIUM|medium|V3-6|
|[O-03](cards/O-03.md)|Secrets/Prompt Injection/Tool Permission 安全终审|X-06,C-04|MEDIUM|critical|V3-6|
|[O-04](cards/O-04.md)|Paid Entitlement 与 Flame/Gameification 解耦|B-01,E-07|MEDIUM|high|V3-6|
|[O-05](cards/O-05.md)|Backup/Restore + Agent Run/Memory Consistency 演练|O-01,X-09,M-07|HEAVY|critical|V3-6|
|[O-06](cards/O-06.md)|Kill Switch / Release / Rollback 统一操作面|O-01,A-01,X-05|MEDIUM|high|V3-6|
|[O-07](cards/O-07.md)|成本/配额/Queue 生产预算与 Graceful Degradation|E-07,X-06,O-02|MEDIUM|high|V3-6|

## QUALITY (8)

|ID|Title|Deps|Resource|Risk|Gate|
|---|---|---|---|---|---|
|[Q-01](cards/Q-01.md)|260 场景统一 Runner 与证据格式|B-03|MEDIUM|medium|V3-7|
|[Q-02](cards/Q-02.md)|20 Golden Journeys 三端终验|Q-01,U-09,J-08,X-10,M-10|HEAVY|medium|V3-7|
|[Q-03](cards/Q-03.md)|Autonomous Visual QA 最终波|U-09,U-10,Q-02|HEAVY|medium|V3-7|
|[Q-04](cards/Q-04.md)|Personalization / Overpersonalization 独立红队|M-09,A-08,D-08|MEDIUM|high|V3-7|
|[Q-05](cards/Q-05.md)|Security/Privacy/Permission 最终红队|O-03,S-05,O-04|MEDIUM|critical|V3-7|
|[Q-06](cards/Q-06.md)|Performance / Cost / Provider 波动终验|E-08,O-07,Q-01|HEAVY|medium|V3-7|
|[Q-07](cards/Q-07.md)|Chaos / Recovery / Offline / Restore Storm 终验|X-09,O-05,U-06|HEAVY|critical|V3-7|
|[Q-08](cards/Q-08.md)|V3 Final Gate Audit / Commercial RC|Q-02,Q-03,Q-04,Q-05,Q-06,Q-07,D-08,P-05,G-05|MEDIUM|critical|V3-7|

