# V2 / V2.5 基线 — V3 不重复施工

此文只定义 V3 的起点，不把历史完成项重新派卡。

## 已知完成/成熟基础（来自项目方 2026-09-19 快照）
- V2 全部 60 工程卡 + 55 继承卡完成；
- 两轮大规模系统审查与 P0/P1 修复；
- 71 条 rule guard 全绿；
- restore storm P50 从约 45s 降到 68ms；
- 三端已有真实 journey 与大量修复；
- qwen3.8-flash 成为当前全 tier 主力；
- MiniMax M3 用于 glm_batch；
- ASR/TTS 切到阿里；
- Memory/RAG revival 14 轮后 8/9 验收稳定；
- CI/迁移/proto/安全/配额/取消语义等已大量加固。

## V3 不应重新安排
- 基础命令协议、幂等、receipt、attempt ledger 若当前实现已满足，不重建；
- V2 的技术债已清偿项不重开；
- 已完成的三端 auth/session 修复不重做；
- 已有 Context/Aurora/Memory 代码先映射与复用，禁止为了新术语创造平行服务；
- 旧卡状态不迁移成 V3 TODO。

## V3 必须重新验证但不是“重做”
- 当前仓库实际模块 reachability 与 feature portfolio；
- 真数据/假数据 lineage；
- 当前模型真实 latency/cost/quality；
- Memory/RAG/画像在整合后是否改善决策；
- UI L2-L5；
- core journeys；
- 社群 realtime、insights、task completion 等历史覆盖缺口；
- 远程部署与商业 entitlement。

## 证据纪律
项目方提供的历史数字是 V3 planning input，不代表本任务包独立重跑验证。V3 Agent 在当前 HEAD 上必须留下新的 evidence。
