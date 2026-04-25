# Sparkle UX Audit Workflow

体验问题发现工作流 — 覆盖全系统 20 条用户体验链路，找到所有闭环断点。

## 工作流架构

```
每 15 分钟                每 15 分钟（offset 10min）    每 30 分钟
Reviewer A  ──────┐                                  Architect
Reviewer B  ──────┴──→  Validator  ──→  git commit   (steering)
                         (验证+汇总)
```

### 四个 Cron Agent

| Agent | Cron | 作用 |
|-------|------|------|
| Reviewer A | `3,18,33,48 * * * *` | 审查奇数链路 (C01,C03,...,C19) |
| Reviewer B | `3,18,33,48 * * * *` | 审查偶数链路 (C02,C04,...,C20) |
| Validator  | `13,28,43,58 * * * *` | 验证+去重+commit |
| Architect  | `8,38 * * * *` | 检查质量+校正方向 |

Cron ID:
- Reviewer A: `3da47531`
- Reviewer B: `5cda25e0`
- Validator:  `4641a7f3`
- Architect:  `e93d3da5`

## 文件说明

| 文件 | 用途 |
|------|------|
| `audit_state.json` | 工作流状态、链路队列、Architect 指令 |
| `reviewer_a_current.md` | Reviewer A 最新一轮的原始发现（每轮覆盖） |
| `reviewer_b_current.md` | Reviewer B 最新一轮的原始发现（每轮覆盖） |
| `accumulated_findings.md` | 所有已验证问题的累积报告（只增不减） |
| `workflow_log.md` | 每次操作的时间线日志 |

## 如何人工介入（Architect 操作）

编辑 `audit_state.json` 中的字段：

```jsonc
{
  // 暂停工作流（审查者下次运行会跳过）
  "status": "paused",          // "running" | "paused" | "complete"

  // 给所有审查者的指令（下次运行时他们会读到）
  "steering_notes": "重点检查 Riverpod invalidation 模式，每个发现必须引用具体文件:行号",

  // 强制 Reviewer A/B 下次审查特定链路（用完后 validator 会清空）
  "architect_override_a": "C05",   // null = 按正常顺序
  "architect_override_b": "C08"
}
```

## 20 条审查链路

| ID | 链路 | 负责人 |
|----|------|--------|
| C01 | 冷启动建模→计划→首个任务 | A |
| C02 | 任务完成→Galaxy mastery→星图颜色 | B |
| C03 | 任务卡点→stuck帮助→Aurora诊断 | A |
| C04 | 错题录入→修复任务→计划页 | B |
| C05 | 冲刺完成→庆祝页→档案更新 | A |
| C06 | Galaxy节点→详情→复习chat | B |
| C07 | 成就里程碑→推送→庆祝页 | A |
| C08 | 回访唤回(≥3天)→comeback消息 | B |
| C09 | 每日启动消息个性化 | A |
| C10 | 跨会话记忆注入 | B |
| C11 | 间隔重复提醒→Celery→推送→chat | A |
| C12 | 低完成率→自适应压缩→计划更新 | B |
| C13 | 每周报告→推送→周报卡 | A |
| C14 | 学习档案页完整性 | B |
| C15 | 全局空状态质量 | A |
| C16 | 导航死路检查 | B |
| C17 | API失败恢复 | A |
| C18 | 推送通知路由完整性 | B |
| C19 | Aurora建模对话质量 | A |
| C20 | Sprint Pack端到端集成 | B |

## 停止条件

当全部 20 条链路状态为 `done` 时，Validator 将 status 设为 `complete`，工作流自动停止。预计耗时约 2.5 小时（10 轮 × 15 分钟）。

## 发现分级标准

| 级别 | 含义 | 示例 |
|------|------|------|
| 🔴 Critical | 阻塞用户或静默丢失数据 | 后端写 DB 成功但 UI 永不刷新 |
| 🟡 Major | 体验混乱或不完整 | 数字永远显示 0，AI 回复没有个性化 |
| 🟢 Minor | 细节打磨缺失 | 缺少 loading skeleton，文案不清晰 |
| ✅ Works | 正确实现 | 记录验证通过的内容 |

## 取消 Cron

```bash
# 在 Claude Code 中执行（需要会话在线）
# CronDelete 3da47531  # Reviewer A
# CronDelete 5cda25e0  # Reviewer B
# CronDelete 4641a7f3  # Validator
# CronDelete e93d3da5  # Architect
```

或直接编辑 `.claude/scheduled_tasks.json` 删除对应条目。
