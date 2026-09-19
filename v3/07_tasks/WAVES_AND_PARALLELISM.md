# Waves & Parallelism

V3 task graph has **107 tasks**. “Wave” 只是阅读辅助；Leader 以依赖图+锁动态调度，不等整波全完才继续。

## Wave 0 — Truth (exactly 6 parallel)
B-01..B-06。

## Wave 1 — Foundations
U-01, D-01, M-01, C-01, X-01, E-01, J-01 等从不同 baseline 解锁。优先 contract/entity mapping，让后续实现大规模并行。

## Wave 2 — Core Intelligence & First Journey
Onboarding/Today/Stuck 与 Memory hard filters、Context source split、Intervention catalog、Human-Agent allocation 同时推进。

## Wave 3 — Closed Loop
Experience Memory、Action Runtime、Outcome Ledger、Aurora policy patches、Insights/Galaxy/Hybrid journey。

## Wave 4 — Trust & Relationship
Memory UI、Why-this、proactive、community privacy、recovery、state completeness。

## Wave 5 — Product Excellence
L2-L5 UI、cross-platform、latency/cost、remote deployment、entitlement、observability。

## Wave 6 — Red Team / RC
Q-01..Q-08 逐步解锁，最终 Q-08 是唯一 Commercial RC gate audit。

### 6-slot policy
- 不允许两任务同时持相同 semantic lock；
- HEAVY 同机≤4（建议3），剩余 slot 给 LIGHT/MEDIUM review/eval；
- contract/schema 高风险任务优先小合并，随后解锁更多并行；
- Leader 持续补满，而不是固定“每人负责一个模块”。
