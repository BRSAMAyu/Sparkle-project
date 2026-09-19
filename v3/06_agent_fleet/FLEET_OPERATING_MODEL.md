# Sparkle V3 — 6-Agent Fleet Operating Model

## 1. 拓扑
- **Leader**：唯一调度与集成真源，不承担长实现任务；
- **6 concurrent slots**：动态 Worker/Reviewer/Simulator，不固定身份；
- 任一成员电脑都可启动同样的舰队，协同需要共享仓库状态与任务租约，不需要等待其他人审批。

## 2. 资源分类
- HEAVY：Flutter build/emulator、Docker full stack、全库测试、大规模迁移；
- MEDIUM：单服务实现/测试、后端集成；
- LIGHT：review、docs、静态分析、scenario、截图评审、单元测试。

同一机器默认：HEAVY≤4，建议 3；总活跃 slot≤6。Leader 发现磁盘<8GB、Docker memory pressure、queue storm 时立即减 heavy 并发。

## 3. 领取规则
任务只有在：
- depends_on 全 DONE；
- required_locks 与 running tasks 不冲突；
- 当前资源允许；
- 没有 stop_condition；
才可领取。

锁是语义组件锁，不只是文件锁。例如 `memory-semantics` 与 `context-retrieval` 即使文件不同也可能产生冲突。

## 4. Worker 循环
1. 读 North Star / card / must_read；
2. inspect 当前实现，不假设卡片术语对应已有类；
3. 先跑 baseline / reproduce；
4. 最小 coherent design；
5. implement；
6. targeted tests；
7. 真 simulator/stack 测试；
8. evidence bundle；
9. 标 READY_FOR_REVIEW；
10. 不等待，Leader 安排下一可用工作。

## 5. Review
普通任务 1 个独立 Reviewer；high-risk 2 个。Reviewer 必须：
- 从用户目标和 acceptance 反推；
- 看 diff + 运行关键测试；
- 对 UI 看实际截图/模拟器，不只读代码；
- 对 AI 行为看真实 trace/多次运行，不只读 prompt；
- 输出 ACCEPT / CHANGES / BLOCKED。

## 6. Merge
Leader 小批 merge/rebase，不攒大爆炸；merge 后在 integration HEAD 重跑 card 的 `integration_checks`。文本冲突消除不代表语义冲突消除。

## 7. Dynamic defects
执行中发现的新问题写入 `06_agent_fleet/DYNAMIC_ISSUES.md` 或状态 JSON；P0/P1 可以由 Leader 生成 `V3-FIX-*` 动态卡，必须有复现/acceptance，不在原卡里暗修大量旁支。

## 8. Continuous propulsion
完成一张卡不是停机点。只要还有可领取任务，Leader 自动补满 slot。只有：
- 全部 V3 gates PASS；
- 全部剩余任务外部 BLOCKED；
- 安全事故/数据风险；
- 资源阈值触发；
才全舰暂停。
