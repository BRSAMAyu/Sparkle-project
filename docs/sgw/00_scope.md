# SGW v2 范围定义

> 版本: 1.1 | 日期: 2026-04-21 | 状态: FROZEN (审查修订版)

## 1. 定位

SGW v2 是 Sparkle 的**长期合成用户闭环测试平台**，不是一个一次性验收脚本。

它从当前 `scripts/sgw/sgw_orchestrator.py` 演化而来，保留其核心价值（全链路 WebSocket 测试、违规检测、断点续跑），同时解决三个根本缺陷：

1. **对话脚本化**：`turn_index % N` 机械触发行为，不像真人对话
2. **评估耦合**：36% soft violation 混合了"系统违规"和"对话质量差"，无法归因
3. **无归因闭环**：发现问题后只能盲调，不知道为什么

## 2. In-Scope（平台职责）

### 2.1 用户模拟
- 从三轴连续分布（行为/叙事/表达）采样，生成高度拟真的合成用户
- Session 级剧情弧保证对话有结构有方向，不是随机拼接
- 事件驱动 state machine 让模拟用户对 AI 回复做出合理反应
- 反应性硬约束强制模拟用户引用/回应 AI 的具体内容

### 2.2 系统验证
- 全链路 WebSocket → Go Gateway → Python Backend 完整测试
- 硬违规自动检测（Rule Y 合规）
- Compliance Audit（inferred write 质量）
- Authenticity Audit（对话真实性独立评分）

### 2.3 归因分析
- Diagnostic Agent 对失败模式做聚类和假设生成
- ExperimentPlan 支持控制变量对比实验
- 迭代日志持久化，所有假设/验证/参数变更可回溯
- 防局部最优机制（随机探索批次 + 多样性监控）

### 2.4 场景抽象
- ScenarioSpec 参数化描述一个测试场景
- 当前实现 Stage 16 (Rule Y)，设计上支持 Stage 17+ 复用
- 多场景可并行运行

### 2.5 长期运行
- 7×24 无人值守运行能力
- 实时观测仪表板
- 告警和自动恢复
- 知识沉淀（iteration 报告可检索）

## 3. Out-of-Scope（明确排除）

### 3.1 被测系统本身的修改
- SGW v2 不修改 Sparkle 主系统代码（Go/Python/Flutter）
- 如果归因分析指向 Sparkle 内核问题，产出的是"诊断报告"而非直接修复
- Sparkle 内核修复是独立的工程任务，不在本平台范围内

### 3.2 生产灰度替代
- SGW 是 Pre-launch context 的验证手段
- 不替代 Product Gray Window (PGW)
- PGW 在有真实用户后仍然需要执行

### 3.3 前端测试
- SGW v2 只测后端（WebSocket → Gateway → Backend）
- Flutter UI 测试由 Flutter 测试套件负责

### 3.4 负载/压力测试
- SGW 的目标是"质量验证"不是"性能压测"
- 并发 Worker 上限 5，不是制造高负载
- 性能压测由独立的 benchmark 工具负责

## 4. 边界条件

| 边界 | SGW v2 行为 |
|------|------------|
| 被测系统崩溃 | 记录错误、等待恢复、从断点继续 |
| 被测系统速率限制 | **假设**：SGW 在测试环境下使用放宽的速率限制（或绕过 IP 限制的内部 API）。如果使用生产配置，5 个 Worker 可能达到 WebSocket 连接限制（5/min）。当前代码每轮打开新 WS 连接，需确认环境是否放宽。 |
| LLM API 全面不可用 | 全局 cooldown + 等待，不修改被测系统 |
| 发现硬违规 | 立即停止、产出诊断报告、等待人工介入 |
| 软违规率 > 30% | 触发 Diagnostic Agent，自动进入归因模式 |
| Meta loop 连续 10 轮无改善 | 告警 + 暂停自动迭代，等待人工审查 |

## 5. 与现有代码的关系

```
scripts/sgw/                    ← SGW v1（当前）
├── sgw_orchestrator.py         ← 逐步重构，不推倒重来
├── sgw_runner.sh               ← 保留，增加 v2 参数
├── hard_violation_rules.py     ← 保留不变（Rule Y 治理要求）
├── metrics_collector.py        ← 扩展（增加归因维度）
├── persona_library.json        ← 扩展（增加三轴分布参数）
├── adversarial_playbook.json   ← 扩展（增加攻击反馈机制）
└── prompts/                    ← 重写（三层 prompt 架构）

scripts/sgw_v2/                 ← SGW v2 新增模块
├── models/                     ← 数据模型（ScenarioSpec, TurnDecision 等）
├── sim/                        ← 模拟层（state machine, arc generator）
├── audit/                      ← 评估层（compliance + authenticity）
├── diagnostic/                 ← 归因层（Diagnostic Agent, ExperimentPlan）
├── meta/                       ← 元编排层（Meta-Orchestrator）
└── storage/                    ← 运行存储层（SQLite）
```

**原则**：`sgw_orchestrator.py` 保持可运行状态，v2 模块逐步替代其内部逻辑，不是 branch 切换。

## 6. 不变量（贯穿所有 Phase）

1. **生成层 ≠ 判断层 ≠ 归因层**：三层独立演化
2. **多样性在分布，不在标签**：连续采样，不枚举
3. **可复现 + 可对比**：run_id + config_hash
4. **每个失败都必须可归因**：维度标签足够切片
5. **Claude Code 只做研究员**：表达层用便宜 API
