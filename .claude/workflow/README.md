# Sparkle 三专家循环工作流协议 v1.0

## 目录结构

```
.claude/workflow/
├── README.md               # 本文件（协议 & 红线）
├── coverage_matrix.md      # 模块/用户链路覆盖矩阵（轮转表）
├── state.json              # 当前轮转游标、统计
├── locks/                  # 文件锁（防并发冲突）
│   └── <role>.lock         # 内含 pid + 起始时间 + 声明的 issue_id
├── queue/
│   ├── pending_fix.md      # 审查产出 → 等待修复
│   ├── pending_verify.md   # 修复完成 → 等待验收
│   └── closed.md           # 已关闭
├── issues/
│   └── ISSUE-YYYYMMDD-NNN.md   # 每个问题一份，含 audit / fix / verify 三段
└── sessions/
    ├── auditor_log.md
    ├── fixer_log.md
    └── verifier_log.md
```

## 覆盖矩阵

19 个切片，轮转扫描，约 6.3 小时一轮。切片粒度 = 一个"用户链路 × 一层"的交集；`state.json.cursor` 指向下次审查的切片。

详见 `coverage_matrix.md`。

### 切片列表

1.  Auth 链路（mobile → gateway middleware → api）
2.  Chat WebSocket 链路（ws_proxy → orchestrator → llm_service）
3.  Plan Review 链路（plan_review_service → Flutter plan_review_card）
4.  Dual-Core Router（dual_core_router → ux_envelope → prompt 注入）
5.  Execution / OpenClaw（execution_service → adapters/openclaw → Flutter openclaw）
6.  Galaxy 知识图谱（galaxy_service → AGE schema → Flutter galaxy）
7.  Community 链路（community_service → community_signal_bridge → Flutter community）
8.  Error Book（error_book.proto → Flutter error_book → knowledge penalty）
9.  Focus / Breathing / 计时（Phase1 修复后的完整链路）
10. Achievement / Photon（achievement_engine → event_consumer → Flutter achievement）
11. Calendar（calendar_weather → notification scheduling → Flutter calendar）
12. Memory Service（memory_service 读写路径 + Stage16 Memory Write Lane）
13. Cognitive Service（cognitive_service → cognitive_patterns → capsule）
14. Seed Library / Tools / Translation
15. Event Bus（event_bus → Redis Streams → 3 bridges + DLQ）
16. Proto 契约（6 个 proto 与 Go/Python/Dart 生成代码一致性）
17. DB 迁移与 schema.sql 一致性（Alembic × sqlc）
18. 监控 & SLO（11 条告警规则 × runbook × Grafana）
19. 安全基线（JWT / rate-limit / CORS / 密钥扫描 / 时序攻击）

## 优先级定义

| 级别 | 含义 |
|------|------|
| **P0 阻塞** | 破坏既有用户链路 / 安全漏洞 / 数据损坏风险 |
| **P1 功能缺陷** | 链路可走通但与设计不符 / UX 明显偏差 |
| **P2 质量债** | 重复代码、遗留 TODO、注释过时、小幅性能 |
| **P3 建议** | 风格 / 可选优化 |

## 红线（任何角色违反立即终止本次 loop 并写入 sessions/<role>_log.md）

1. **禁止** push、force push、touch 远端分支
2. **禁止** git reset --hard、rm -rf、drop table、destructive alembic downgrade
3. **禁止**修改 .env*、secrets、CI/CD workflow、Makefile 中与部署相关的 target
4. **禁止**跨越当前 worktree 目录写文件
5. **禁止**直接编辑生成文件（proto gen / sqlc models / build_runner 产物）
6. **禁止**跳过 pre-commit / --no-verify
7. 单次 loop 改动 ≤ 10 个文件、≤ 400 行净增减；超限则拆分成多个 issue

## 并发控制

- 每个角色启动时写 `locks/<role>.lock`，结束或异常退出时删除
- Fixer 领取 issue 前必须在 ISSUE 文件头写 `claimed_by: fixer / claimed_at: <ts>`
- 若发现 lock 存在且 > 15min，视为僵死，可强制清理并在 log 留痕
- 三方均**禁止**修改他人当前 claim 的 ISSUE 文件正文（只能追加自己段落）

## Issue 模板

```markdown
---
id: ISSUE-YYYYMMDD-NNN
slice: <切片编号-名称>
severity: P0 | P1 | P2 | P3
status: pending_fix | pending_verify | closed | rejected
created_by: auditor
created_at: <ISO 8601>
claimed_by: null
paths: [<相关文件路径:行号>]
---

## [Audit] 证据
<grep/read 输出摘要、复现步骤、期望 vs 实际>

## [Audit] 建议修复方向
<不给具体代码，给方向与约束>

## [Fix] 变更摘要
<commit sha、动了哪些文件、为什么>

## [Fix] 自检
<本地测试、相关 make 命令输出要点>

## [Verify] 判定
PASS / FAIL / NEEDS_REWORK，理由 + 证据
```

## 停机条件

任一角色连续 3 次 loop 出现以下任一情况，在自己的 log 写 `halt_requested` 并退出循环：

- pending_fix / pending_verify 队列为空 **且** coverage_matrix 已完成 ≥ 2 轮
- 连续触发同一红线
- 同一 issue 在 verifier 处 FAIL ≥ 3 次（标记为需要人工介入）

## 角色时序

```
T+0min   Auditor  触发  → 扫描切片，产出 issue → 写入 pending_fix
T+7min   Fixer    触发  → 领取 issue，修复 → 写入 pending_verify
T+14min  Verifier 触发  → 验收 → PASS 写入 closed / FAIL 退回 pending_fix
```

三角色通过文件系统交接，无需网络或进程间通信。
