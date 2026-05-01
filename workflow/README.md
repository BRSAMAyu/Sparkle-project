# Sparkle 三专家持续审查工作流 · 协议 v1.0

> 目的：让 Auditor（审查）/ Fixer（修复）/ Verifier（验收）三个独立 Claude Code 会话，以 20 分钟循环 + 错峰启动的方式，稳定、持续、高质量、无漂移地覆盖 Sparkle 全系统，同时保留架构师（你）的最高优先级干预通道。

---

## 0. 角色与节拍

| 角色 | 会话 | 启动偏移 | 循环 | 职责 |
|---|---|---|---|---|
| A · Auditor 审查专家 | Session-A | T + 0 min | `/loop 20m` | 按切片轮转，亲自核对关键文件，产出/更新 ISSUE |
| B · Fixer 修复专家 | Session-B | T + 7 min | `/loop 20m` | 从队列领取 ISSUE，独立复核代码，修复或反证 |
| C · Verifier 验收专家 | Session-C | T + 14 min | `/loop 20m` | 批判性复核初审 + 修复结果，回灌 FAIL/REWORK |

错峰 7 分钟确保「审查→修复→验收」天然流水线，且不会在同一秒写同一个文件。

---

## 1. 目录结构

```
workflow/
├── README.md                       本文件
├── ARCHITECT_DIRECTIVES.md         ★ 架构师最高优先级通道（每个 loop 首先读取）
├── COVERAGE_MATRIX.md              21 切片轮转状态表
├── SUMMARY.md                      所有 ISSUE 的汇总索引（人读）
├── state.json                      机器可读状态（游标、round、计数）
├── PROMPT_AUDITOR.md               审查专家 Prompt
├── PROMPT_FIXER.md                 修复专家 Prompt
├── PROMPT_VERIFIER.md              验收专家 Prompt
├── locks/                          并发文件锁（auditor/fixer/verifier.lock）
├── issues/
│   ├── open/          ISSUE-YYYYMMDD-NNN.md  等待修复
│   ├── verifying/                             等待验收
│   ├── closed/                                已关闭
│   └── escalated/                             需人工介入
├── coverage/
│   └── <NN-slice>/    审查详情层级文档（每个切片一个子目录）
├── sessions/
│   ├── auditor_log.md
│   ├── fixer_log.md
│   └── verifier_log.md
└── architect/
    ├── decisions/     架构师批示落地（每条一个 md）
    └── notes/         架构师观察、临时笔记
```

---

## 2. 红线（违反即终止本次 loop，写入 sessions log）

1. **禁止 push / force push / 修改远端分支 / 创建 PR**（架构师亲自操作）
2. **禁止** `git reset --hard` / `rm -rf` / `drop table` / destructive alembic downgrade
3. **禁止**修改 `.env*`、secrets、`.github/workflows/**`、`Makefile` 中部署相关 target、`docker-compose.*.yml` 的镜像版本
4. **禁止**跨越当前 worktree 目录写文件
5. **禁止**直接编辑生成文件：`backend/gateway/gen/**`、`backend/app/gen/**`、`mobile/lib/gen/**`、sqlc `models.go`、build_runner 产物
6. **禁止**跳过 pre-commit / `--no-verify` / `--no-gpg-sign`
7. **禁止**为了绕过失败的测试而删除测试或放宽断言
8. **禁止**完全依赖 Agent 子会话做判断：关键文件必须本会话亲自 Read/Grep 核对
9. 单次 loop 代码改动 ≤ **10 文件 / 400 净行**；超限必须拆 ISSUE
10. 一个 loop 只做一个角色的事，不得越权（Auditor 不改业务代码，Fixer 不自己 PASS 自己的 ISSUE）

---

## 3. 优先级与 ISSUE 生命周期

### 优先级
- **P0 阻塞**：破坏既有用户链路 / 安全漏洞 / 数据损坏
- **P1 功能缺陷**：链路能走但与设计/共识不符
- **P2 质量债**：重复、遗留 TODO、注释过时、小性能
- **P3 建议**：风格 / 可选优化

### 状态机
```
         审查发现
             │
             ▼
      issues/open/*.md  ←──────────────────────────┐
             │                                     │
          Fixer 领取（写 claimed_by）              │
             │                                     │
             ├── 代码确有问题 → 修复 → verifying/ ─┤
             │                           │         │
             │                           ▼         │
             │                     Verifier 复核   │
             │                           │         │
             │                     PASS → closed/  │
             │                     FAIL / REWORK ──┘
             │
             ├── 代码无问题/报告不准 → 写反证批注 → verifying/ (status=disputed)
             │                                              │
             │                                  Verifier 裁决 closed/ 或 open/（需补证）
             │
             └── 过大/跨切片 → 拆 ≤3 子 ISSUE → 回 open/

同一 ISSUE 累计 3 次 FAIL/REWORK 或 2 次 disputed → escalated/（人工）
```

### ISSUE 文件模板
```markdown
---
id: ISSUE-20260424-001
slice: 03-plan_review
severity: P1
status: open            # open | verifying | closed | escalated | disputed
created_by: auditor
created_at: 2026-04-24T14:22:00+08:00
claimed_by: null
fixed_at: null
verified_at: null
paths:
  - backend/app/orchestration/plan_review_service.py:120
  - mobile/lib/features/chat/presentation/widgets/plan_review_card.dart:88
related:
  - ISSUE-20260423-005   # 同一链路的相邻问题
---

## [Audit] 证据
<grep/read 原文摘录、复现步骤、期望 vs 实际>

## [Audit] 建议修复方向
<只给方向与约束，不给具体实现>

## [Audit] 潜在副作用
<动这里可能影响的其它链路>

## [Fix] 复核结论
<Fixer 独立验证后的判断：确有问题 / 不准确 / 需拆分>

## [Fix] 变更摘要（若修复）
<commit sha、动了哪些文件、为什么这样改>

## [Fix] 自检
<跑了哪些测试、结果、UI 是否手验>

## [Verify] 判定
PASS | FAIL | REWORK | DISPUTED_UPHELD | DISPUTED_OVERRULED
理由 + 独立复现证据
```

---

## 4. 汇总索引 `SUMMARY.md`

三方共同维护的**唯一事实表**，每条一行，便于人读 + 快速查 ISSUE 是否已存在：
```
| ID | Slice | P | Status | Title | Claimed | Updated |
|----|-------|---|--------|-------|---------|---------|
| ISSUE-20260424-001 | 03 | P1 | open | plan_review 丢失 metadata | - | 14:22 |
```

**写入规则**：
- Auditor 创建 ISSUE → 同步追加一行
- Fixer 领取/修复 → 原行就地更新 Status/Claimed/Updated
- Verifier 判定 → 就地更新 Status（closed 保留一周再剔除，便于趋势观察）
- 任何人都**不得删除**他人写的行，只能更新

---

## 5. 覆盖保证：21 切片轮转

见 `COVERAGE_MATRIX.md`。Auditor 每次 loop 推进一个切片；切片冷却期 **4 小时**，确保约 24h 完成一轮全项目扫描。

每个切片必须端到端走读「Flutter 入口 → Go Gateway → Python Service → DB/Redis → 事件总线」，并对照 7 维清单（见 `PROMPT_AUDITOR.md`）。

---

## 6. 架构师干预通道（最高优先级）

`ARCHITECT_DIRECTIVES.md` 是你（架构师）写批示的唯一入口。三专家**每个 loop 的第一步**都是读这个文件。

### 指令格式
```markdown
## DIRECTIVE-YYYYMMDD-NN
- status: active | done | revoked
- issued_at: 2026-04-24T16:00:00+08:00
- target_roles: [auditor, fixer, verifier]   # 谁必须执行
- priority: override                          # override 会暂停正常队列
- expires_at: 2026-04-25T00:00:00+08:00       # 可选

### 内容
<具体要求：例如"暂停所有 P2 以下修复，本轮所有资源集中到 slice-03 plan_review">
```

### 三方响应规则
1. 发现 `status: active` 且 `priority: override` 的指令时：
   - 放弃本 loop 原计划，按指令执行
   - 执行完把 `status: done` 并在指令下方追加 `## ACK by <role>` 段
2. `target_roles` 不含自己时：仅感知，不执行，但写入本角色 log 留痕
3. 架构师可在 `architect/decisions/<id>.md` 留下更长版决策背景，指令文件只留可执行摘要
4. 三专家**禁止**修改 `ARCHITECT_DIRECTIVES.md` 以外的 `architect/` 目录（只读）

---

## 7. 并发控制

- 每个角色启动时在 `locks/<role>.lock` 写：
  ```
  pid=<n>
  started_at=<iso>
  claim=ISSUE-xxx | slice-xx | none
  ```
- 正常结束或异常退出都必须删除自己的 lock
- 若发现他人 lock 存在 > 18 min，视为僵死，可强制清理并在 log 写 `CLEANUP <role> lock age=<n>min`
- Fixer 领取 ISSUE 前必须在 ISSUE 文件头写 `claimed_by: fixer / claimed_at: <ts>`；领取后其它角色不得改其 `[Fix]` 段
- 三方均可**追加**自己段落，不得删除/改写他人段落

---

## 8. Git 持续维护

**分离提交**：工作流文档提交与业务代码提交**必须分开**。

| 角色 | 提交形态 |
|---|---|
| Auditor | 仅工作流文档：`audit(slice-NN): add K issues` |
| Fixer | **先**代码提交：`fix(<scope>): <what>` （含 ISSUE id trailer） → **再**文档提交：`triage: update ISSUE-... status` |
| Verifier | 仅工作流文档：`verify: ISSUE-... PASS/FAIL/REWORK` |
| Architect | 任意 + `architect: ...` 前缀 |

**提交规范**：
- 每个 loop 结束前必须 `git status` 确认无遗漏
- **禁止** `git commit --amend`（除非修正当前 loop 自己刚提交且未 push 的）
- **禁止**跨角色 squash
- commit message 末尾必须带 `Co-Authored-By: Claude <noreply@anthropic.com>` 与 `issue: ISSUE-xxx`（如适用）
- 每次 Fixer 代码提交前运行对应 pre-commit 钩子，不得 bypass

**工作区整洁**：
- 每个角色 loop 开始时若发现 `git status` 有未提交残留，先诊断归属：
  - 若是本角色上轮异常中断 → 按残留内容判定继续 or 丢弃（`git stash` 先保留，写 log）
  - 若是其它角色残留 → 写 log `DETECT leftover from <role>, skip loop`，立即退出

---

## 9. 停机条件（任一触发）

1. 连续 3 个 loop `open/` 与 `verifying/` 都为空，且 COVERAGE_MATRIX 全部切片 round ≥ 2
2. 连续触发同一红线 2 次
3. `ARCHITECT_DIRECTIVES.md` 有 `status: halt` 指令

触发时在 `sessions/<role>_log.md` 写 `HALT_REQUESTED reason=...` 并退出当前 loop，`/loop` 会在下一轮重启；但若架构师 halt 则不再启动。

---

## 10. 独立批判性铁律（必读）

这是整个工作流不漂移的根基。三专家都必须遵守：

1. **本会话亲自核对**：核心文件（Orchestrator / DualCoreRouter / WebSocket Proxy / Plan Review / Memory Write Lane / Event Bus / Auth / Proto / Schema）必须自己 Read/Grep，**禁止**仅凭 Agent 摘要定论
2. **证据优先**：所有判断必须给出 `file_path:line_number` + 原文引用 + 复现步骤；不得用"可能"、"也许"、"应该"
3. **反向假设**：Fixer 在修之前必须先假设"Auditor 报错了"，独立跑一遍；Verifier 在判 PASS 前必须先假设"Fixer 改错了"
4. **全局副作用**：任何改动前回答三个问题
   - 这条链路的上下游还有谁依赖？
   - 现有哪些测试/acceptance 覆盖了它？
   - 改完会不会让某个当前正常工作的系统降级？
5. **拒绝虚假成功**：没跑的测试不得说"通过"；UI 未手验必须明说"代码层修改未手验"；找不到根因不要"假装修好"
6. **增量最小化**：不顺带重构，不加无关抽象，不加装饰性注释
7. **遵守 CLAUDE.md 源真层级**：proto → gen / schema → alembic / design_system.dart → 组件，反方向永远错

违反此铁律一次 → 验收 FAIL；连续违反两次 → `architect/notes/` 留痕并在下一轮 loop 开始前必须读完才能继续。

---

## 11. 启动方式

在三个独立终端分别：
```bash
# 终端 A（立即）
claude
# 进入会话后：
/loop 20m @workflow/PROMPT_AUDITOR.md

# 终端 B（等 7 分钟）
sleep 420 && claude
/loop 20m @workflow/PROMPT_FIXER.md

# 终端 C（等 14 分钟）
sleep 840 && claude
/loop 20m @workflow/PROMPT_VERIFIER.md
```

架构师介入时：
```bash
# 直接编辑 workflow/ARCHITECT_DIRECTIVES.md 追加新指令
# 或者在 architect/decisions/ 落地较长的决策文档
```

---

## 12. 版本历史
- v1.0 · 2026-04-24 · 初版（Opus 起草，经人类架构师确认）
