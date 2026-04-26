# Sparkle UX Audit Workflow

체验问题发现工作流 — 覆盖全系统 20 条用户体验链路，找到所有闭环断点。

---

## 工作流设计

```
人工启动                人工启动              人工启动（或 resume）
Reviewer A  ──────┐                              Architect
Reviewer B  ──────┴──→  Validator  ──→  git      (30分钟检查一次)
(每轮一条链路)           (验证+汇总)     commit
```

**四个角色，各自独立**：
- **Reviewer A / B**：每次启动只审查一条链路，写完 `reviewer_X_current.md` 就停止
- **Validator**：读 A/B 的最新输出，验证质量、汇总、更新状态、git commit
- **Architect（你/Claude）**：每 30 分钟检查一次，校正方向，必要时干预

**节奏**（参考）：
- A + B 可以同时启动（它们写不同的文件，不冲突）
- A+B 跑完后启动 Validator
- 每 30 分钟用 `architect_alignment.md` 做一次检查

---

## 如何启动每个 Agent

每个角色有一个对应的 prompt 文件。启动方式：

### Reviewer A

```bash
# 新开一个 terminal，在项目根目录
claude --print "$(cat docs/ux_audit/prompts/reviewer_a.md)"

# 或者交互式（推荐，可以看到实时输出）
claude
# 然后粘贴 docs/ux_audit/prompts/reviewer_a.md 的全文作为第一条消息
```

### Reviewer B

```bash
claude --print "$(cat docs/ux_audit/prompts/reviewer_b.md)"
# 或交互式，粘贴 reviewer_b.md
```

### Validator（A + B 都跑完后启动）

```bash
claude --print "$(cat docs/ux_audit/prompts/validator.md)"
```

### Architect 检查（Claude / 你本人）

在当前对话（Claude）里直接说：
> "请做一次 UX 审查工作流的 architect 检查，读 docs/ux_audit/ 下的所有文件，按 architect_alignment.md 的格式输出报告。"

或者新建一个 Claude 会话，让它读 `docs/ux_audit/prompts/architect_alignment.md` 作为角色对齐文档。

---

## 状态管理

所有状态都在 `docs/ux_audit/audit_state.json`：

```jsonc
{
  "status": "running",          // "running" | "paused" | "complete"
  "current_round": 0,           // 已完成轮数
  "reviewer_a_next": 0,         // A 下一条要审的队列索引（0-9）
  "reviewer_b_next": 0,         // B 下一条要审的队列索引（0-9）
  
  // Architect 干预：填写后，对应 reviewer 下次会优先审这条链路
  "architect_override_a": null, // 填链路 ID，例如 "C05"，用完后 validator 清空
  "architect_override_b": null,
  
  // 质量指令：非空时，reviewer 会在审查前读取并应用
  "steering_notes": ""
}
```

**人工干预示例**：

```bash
# 暂停工作流（下次 reviewer 启动时会跳过）
# 编辑 audit_state.json，把 "status" 改为 "paused"

# 强制 Reviewer A 下次审查特定链路
# 编辑 "architect_override_a": "C05"

# 留质量指令
# 编辑 "steering_notes": "每个发现必须引用 file:line，说明期望行为和实际行为"
```

---

## 20 条审查链路

| ID | 链路 | 负责人 | 状态 |
|----|------|--------|------|
| C01 | 冷启动建模→计划→首个任务 | A | pending |
| C02 | 任务完成→Galaxy mastery→星图颜色 | B | pending |
| C03 | 任务卡点→stuck帮助→Aurora诊断 | A | pending |
| C04 | 错题录入→修复任务→计划页 | B | pending |
| C05 | 冲刺完成→庆祝页→档案更新 | A | pending |
| C06 | Galaxy节点→详情→复习chat | B | pending |
| C07 | 成就里程碑→推送→庆祝页 | A | pending |
| C08 | 回访唤回(≥3天)→comeback消息 | B | pending |
| C09 | 每日启动消息个性化 | A | pending |
| C10 | 跨会话记忆注入 | B | pending |
| C11 | 间隔重复提醒→Celery→推送→chat | A | pending |
| C12 | 低完成率→自适应压缩→计划更新 | B | pending |
| C13 | 每周报告→推送→周报卡 | A | pending |
| C14 | 学习档案页完整性 | B | pending |
| C15 | 全局空状态质量 | A | pending |
| C16 | 导航死路检查 | B | pending |
| C17 | API失败恢复 | A | pending |
| C18 | 推送通知路由完整性 | B | pending |
| C19 | Aurora建模对话质量 | A | pending |
| C20 | Sprint Pack端到端集成 | B | pending |

---

## 发现分级标准

| 级别 | 含义 | 典型例子 |
|------|------|----------|
| 🔴 Critical | 阻塞用户或静默丢失数据 | 后端写 DB 成功但 UI 永不刷新；无法退出的屏幕 |
| 🟡 Major | 体验混乱或不完整 | mastery 永远是 0；AI 回复无个性化；空白屏无引导 |
| 🟢 Minor | 细节打磨缺失 | 缺 loading skeleton；back 按钮略不对 |
| ✅ Works | 正确实现 | 确认实现正确，记录存档 |

---

## 文件说明

| 文件 | 用途 |
|------|------|
| `audit_state.json` | 工作流唯一状态源 |
| `reviewer_a_current.md` | A 最新一轮原始发现（每轮覆盖）|
| `reviewer_b_current.md` | B 最新一轮原始发现（每轮覆盖）|
| `accumulated_findings.md` | 所有已验证问题的累积报告 |
| `workflow_log.md` | 时间线日志 |
| `prompts/reviewer_a.md` | Reviewer A 角色 prompt |
| `prompts/reviewer_b.md` | Reviewer B 角色 prompt |
| `prompts/validator.md` | Validator 角色 prompt |
| `prompts/architect_alignment.md` | 架构师视野对齐文档 |

---

## 停止条件

全部 20 条链路 status 为 `done` 时，Validator 将 `status` 设为 `complete`，后续 reviewer 启动时自动跳过。所有发现汇总在 `accumulated_findings.md`，届时由 Architect（Claude+你）共同决定修复优先级和修复方案，再派发给 Codex 执行。
