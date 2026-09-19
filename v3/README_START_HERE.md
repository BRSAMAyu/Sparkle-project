# Sparkle V3 Agent Execution Pack — START HERE

> **定位**：V3 是 Sparkle 从「工程上可用」迈向「真正好用、长期越用越好、具有商业竞争力」的产品化版本。此包只服务 Agent 舰队执行；不包含人的赛事材料、用户招募或人工审批任务。

## 0. 唯一目标

V3 不以“完成更多功能”为目标，而以 **跨模块用户价值闭环** 为完成标准：

1. 用户能在 3 分钟内获得第一次明确价值，而不是先学习产品结构；
2. 用户卡住时，Sparkle 能识别真正的 friction（阻碍），给出仍能推进目标的 smallest useful step；
3. 每个 Action 明确由 **Human / Agent / Hybrid** 谁执行，AI 不替用户完成本应由用户掌握的核心认知工作；
4. 用户纠正 Sparkle 后，后续相关决策必须改变，而无关情境不能机械复用；
5. Memory、RAG、画像、行为证据、任务结果通过 Context Compiler 与 Conflict Resolver 进入同一决策闭环；
6. Aurora 是可感知、可解释、可纠偏的 Adaptive Control + Relationship Layer，而非一个“75%理解度”卡片；
7. 数据分析回答“目标有没有真正推进、什么干预对我有效”，不再展示来源不明的 vanity metrics；
8. UI/UX 从“功能齐全”升级到消费级产品：安静、清晰、有温度、可信、状态完整；
9. 所有 AI 写操作、Agent Run、Memory 使用都有来源、权限、幂等、回执、审计和恢复；
10. 远程部署、监控、恢复、隐私和成本能够支持真实试用，而非只能本机演示。

## 1. 先读顺序

Leader 和所有 Worker 开工前必须按顺序读取：

1. `NORTH_STAR.md`
2. `V3_DEFINITION_OF_DONE.md`
3. `00_context/DECISIONS_V3.md`
4. `06_agent_fleet/FLEET_OPERATING_MODEL.md`
5. 自己任务卡 `07_tasks/cards/<ID>.md`
6. 任务卡列出的 `must_read`

核心系统任务额外阅读 `02_core_systems/` 相应规格；UI 任务额外阅读 `04_ux/`。

## 2. 这不是 V2 重跑

V2 与 V2.5 已被项目方声明完成并经历大量模拟器/真机修复。**V3 卡片全部是新增产品化工作，不允许为了满足卡片而重做已经完成的旧卡。**

如果当前仓库已经实现某张 V3 卡的行为：
- 不要机械重写；
- 先用该卡的 V3 验收协议证明当前行为；
- 若全部通过，可提交“evidence-only completion”；
- 只修验收失败的最小缺口。

## 3. Agent 舰队运行模型

- 前台：1 个 Leader（调度、冲突管理、集成、状态真源）。
- 后台：最多 6 个并发 Agent。
- 同一台机器历史上重型 Agent >4 会造成 Docker/Flutter 资源争用，因此**6 并发不等于 6 个重型构建**：建议 3–4 个 heavy implementation + 1–2 个 review/simulator/research/light task。
- Worker 不自行宣布 DONE；输出 `READY_FOR_REVIEW` 证据单。
- 独立 Reviewer 根据风险要求 1–2 个；高风险（隐私/删除/写操作/支付/跨用户/Agent Runtime）至少 2 个独立审查。
- Leader 只合并小批量，并在当前集成 HEAD 上重跑相关 journey / guard。

## 4. 任务如何领取

```bash
python 10_tools/next_tasks.py --state .sparkle_v3_fleet_state.json --limit 6
python 10_tools/fleet_state.py init --state .sparkle_v3_fleet_state.json
python 10_tools/fleet_state.py claim --state .sparkle_v3_fleet_state.json --task B-01 --agent agent-1
```

若尚未初始化，第一轮应有且只有 B-01…B-06 六张 baseline 卡可并行领取。

## 5. 完成一张卡必须留下什么

每张卡至少包含：
- 当前 base / final commit SHA；
- 改动摘要与为什么；
- 自动测试/守卫输出；
- 对应模拟器/浏览器/真机 journey 证据；
- UI 任务的 before/after 截图；
- AI 行为任务的真实模型 trace / requested+actual model / latency / usage；
- Reviewer verdict；
- 若未达到目标，必须标 `BLOCKED` 或 `PARTIAL`，不能通过文案伪装完成。

## 6. 最高纪律

> **从用户结果倒推系统，而不是从已有代码向用户解释价值。**

已有 42 个 feature、数百服务、复杂 Aurora/RAG/画像/统计不是保留理由。只有真正帮助核心旅程、产生可测价值的能力才能进入 V3 主产品表面。
