# 架构师指令通道 · 最高优先级

> **说明**：本文件是人类架构师（Opus + 人）对三专家工作流的唯一干预入口。每个 loop 的第一步（紧跟 lock 检查后）必须读这里，凡出现 `status: active` 且 `priority: override` 的指令，立即暂停本角色当前 loop 的常规计划，转而执行指令内容。执行完毕写 `## ACK by <role>` 段并把 status 改为 `done`。
>
> 三专家**禁止**在本文件追加与"执行指令"无关的内容；长背景/方案放到 `architect/decisions/<id>.md`。

---

## 使用说明（架构师写指令时）

指令 id 规则：`DIRECTIVE-YYYYMMDD-NN`，NN 从当天 01 起。

`priority`：
- `override`：暂停正常队列，本 loop 必须先处理
- `elevated`：优先级拔高到当前队列头部，但不阻断常规流程
- `advisory`：只读提示，不强制执行

`target_roles`：`[auditor]` / `[fixer]` / `[verifier]` / `[auditor, fixer, verifier]` / `[all]`

`scope`：可选，限定作用切片或 ISSUE，例如 `slice:03-plan_review` 或 `issue:ISSUE-20260424-007`

`expires_at`：可选。过期后即使未 done 也视为失效，三专家写 `status: expired`。

---

## 活动指令

<!-- 架构师在下方追加新指令。三专家按顺序处理 active 指令，done 与 expired 会被定期归档到 architect/decisions/ARCHIVE_<yyyymm>.md -->

---

### DIRECTIVE-20260424-07
- status: active
- issued_at: 2026-04-25T00:00:00+08:00
- target_roles: [auditor]
- priority: override
- scope: all
- expires_at: never

#### 内容

**Auditor cursor 冻结：立即停止推进新切片，等待 P1 open < 10。**

原因：
1. P1 积压已达 18 个（红线是 20），fix 速率约 1-2/loop，audit 速率约 6/loop，积压比 1:3 无法收敛
2. DIRECTIVE-03（elevated，要求先补核 ISSUE-009 再推切片）被直接忽视 — cursor 推了 10→11→12 两步，ISSUE-009 未核查

**立即执行（本 loop 内，在所有其他任务之前）**：

1. **cursor 冻结**：不得再调用 `cursor += 1` 推进新切片，直到 `workflow/SUMMARY.md` 中 P1 open 数量降至 **< 10**
2. **ISSUE-009 补核**（DIRECTIVE-03 遗留任务）：
   - 打开 `backend/gateway/internal/service/quota.go` 和 `backend/gateway/internal/handler/chat_orchestrator_chatflow.go`
   - 独立确认 `segmentSize guard` 是否真的防住了 `STREAM_TOKEN_SEGMENT=0` 除零
   - 若 guard 有效 → 在 `workflow/SUMMARY.md` 为 ISSUE-009 标注 `[re-audit: guard confirmed, downgrade P1→P2]` 并降级
   - 若 guard 无效 → 维持 P1，将 ISSUE-009 插入 `workflow/queue/pending_fix.md` 头部
3. **冻结期间可做的工作**（不得推新切片，但以下工作合法）：
   - Re-audit 已有切片（round 0 的第二遍）
   - 协助 Verifier：帮助验证在 verifying 队列中的 fix（但不替代 Verifier 的最终判定）
   - 对现有 open 问题提供辅助分析（如 Fixer 需要背景信息时）
4. 解冻条件：`workflow/SUMMARY.md` 统计快照显示 `open P1 < 10` 时，由架构师在 CONTROL_LOG 写入解冻决定后生效（不得自行解冻）

#### ACK by auditor
（待 Auditor 执行后填写）

---

### DIRECTIVE-20260424-08
- status: active
- issued_at: 2026-04-25T00:00:00+08:00
- target_roles: [fixer]
- priority: elevated
- scope: all
- expires_at: never

#### 内容

**Fixer 下阶段优先队列（ISSUE-027/028 进入 verifying 后）**

安全 P1 修复完成后，下阶段按以下顺序认领：

```
第一波（数据完整性 P1）：
  ISSUE-20260424-016  pending_actions_store get-delete 非原子，SubmitPlanReview 可重复审批
                      → 加 Redis SET NX 或 DB 行级锁
  ISSUE-20260424-015  asyncio.create_task fire-and-forget，计划批准后任务生成静默失败
                      → 改为 await 或显式 try/except + 日志
  ISSUE-20260424-040  community_signal_bridge handle_resource_shared 双重 commit
                      → 删除重复 await db.commit()

第二波（核心逻辑 P1）：
  ISSUE-20260424-072  enqueue_from_chat_turn fire-and-forget，推断记忆写入失败静默丢弃
  ISSUE-20260424-064  NotificationPushService 绕过用户通知偏好
  ISSUE-20260424-021  routing_engine chat+direct 快捷路径绕过双核信号处理
```

**原则**：
- 每个 fix commit 引用规范 ISSUE ID
- Fix 完成后立即更新 `workflow/issues/open/ISSUE-NNN.md` 的 `## [Fix]` 段，移入 verifying/，更新 SUMMARY.md
- 不要超前认领超过 2 个 issue（避免并发冲突）

#### ACK by fixer
（待 Fixer 执行后填写）

---

### DIRECTIVE-20260424-05
- status: done
- issued_at: 2026-04-24T23:35:00+08:00
- target_roles: [fixer]
- priority: override
- scope: issue:ISSUE-20260424-027,ISSUE-20260424-028
- expires_at: 2026-04-25T12:00:00+08:00

#### 内容

**安全 P1 紧急插队：ISSUE-027 和 ISSUE-028 必须在所有其他 issue 之前修复。**

架构师检测到 `workflow/queue/pending_fix.md` 当前队列头部是 achievement/error_book 相关问题（ISSUE-058/059/060/046），而安全类 P1 未入队。这违反了安全优先原则。

**立即执行**：

1. 将 `workflow/queue/pending_fix.md` 中的当前条目保持不变，但在顶部**插入**以下两条（优先处理）：
   ```
   - ISSUE-20260424-027 P1 [SECURITY] /health 端点未认证可访问，泄露 OpenClaw 基础设施详情
   - ISSUE-20260424-028 P1 [SECURITY] handoff_task Exception 捕获泄露内部错误消息
   ```

2. ISSUE-027 修复方向：
   - 在 `/health` 路由加认证 middleware（与 `/api/v1/executions` 路由一致），或者
   - 将 `/health` 端点的响应内容截断为只返回 `{"status": "ok"}`，不含 OpenClaw URL、config 等基础设施信息

3. ISSUE-028 修复方向：
   - 将 `except Exception as e: raise HTTPException(status_code=500, detail=str(e))` 改为 `raise HTTPException(status_code=500, detail="Internal execution error")`
   - 确保内部错误只进入日志，不通过 HTTP 响应泄露

4. Fix commit 格式：`fix(openclaw): <描述>\n\nissue: ISSUE-20260424-027` 和 `fix(openclaw): <描述>\n\nissue: ISSUE-20260424-028`

**时限**：12h 内（2026-04-25T12:00 前）必须进入 verifying。超时架构师将升级为 P0 并直接指派。

#### ACK by fixer
Fixer Loop 6 @ 2026-04-24T23:50. ISSUE-027 fixed (unauthenticated /health response truncated to minimal). ISSUE-028 fixed (commit 9f84ab1d: generic error message, original logged). Both moved to verifying/.

---

### DIRECTIVE-20260424-06
- status: done
- issued_at: 2026-04-24T23:35:00+08:00
- target_roles: [fixer]
- priority: elevated
- scope: issue:ISSUE-20260424-007
- expires_at: never

#### 内容

**ISSUE-007 降级决定：P1 → P2，不强制修复，但需记录保护边界。**

架构师独立验证了 Fixer 的 dispute 证据：
- `chat_history.go:237-250` circuit breaker + retryBuf（最大 500 条）确实存在
- `retryWorker` 定期重试入队确实存在
- `GetMessages` DB fallback 确实存在

Dispute 核心观察**成立**：不是"立即不可恢复丢失"，有多层保护。P2 降级合理。

**但须记录以下已知剩余风险**（写入 ISSUE-007 的 `## [Fix]` 段）：
- retryBuf 上限 500 条，在持续 Redis 不可用时 old messages 会被 LRU 淘汰（line 178）
- 这是可接受的工程折中，但运维必须知道此边界

Fixer 需在 `workflow/issues/verifying/ISSUE-20260424-007.md` 的 `## [Fix]` 段补充：
```
## [Fix] 变更摘要
无代码修改。保护机制已存在。

## [Fix] 自检
已验证: circuit breaker retryBuf(max=500), retryWorker, GetMessages DB fallback
已知边界: retryBuf overflow 在持续 Redis 故障 >500 消息时 oldest 被丢弃（可接受折中）
建议: 运维 alert on retryBuf > 400 条（Prometheus gauge 建议后续添加）
```

然后将 ISSUE-007 移入 `workflow/issues/closed/`，在 `workflow/SUMMARY.md` 更新 status 为 `closed (P2-downgraded, dispute accepted)`。

#### ACK by fixer
Fixer Loop 6 @ 2026-04-24T23:55. ISSUE-007 moved to closed/ with protection boundary notes. SUMMARY.md updated to closed (P2-downgraded, dispute accepted).

---

### DIRECTIVE-20260424-01
- status: done
- issued_at: 2026-04-24T23:30:00+08:00
- target_roles: [fixer]
- priority: override
- scope: all
- expires_at: never

#### 内容

**Fixer 队列重置：立即放弃 `.claude/workflow/queue/pending_fix.md`，改用规范队列。**

经架构师独立审查，`.claude/workflow/` 是一个影子追踪系统，其 ISSUE ID 与规范系统 `workflow/SUMMARY.md` 存在严重冲突（同一 ID 指向不同问题）。继续在影子系统工作会导致修复错误问题、fix commit 引用错误 ID，污染 git 历史。

**立即执行（本 loop 内）**：

1. 丢弃 `.claude/workflow/queue/pending_fix.md` 中的所有条目（不要 fix 这些）
2. 改从 `workflow/SUMMARY.md` 中按以下优先级认领：
   ```
   P1 安全优先（立即修）：
     ISSUE-20260424-027  /health 泄露 OpenClaw 基础设施
     ISSUE-20260424-028  handoff_task Exception 泄露内部错误
   P1 数据完整性（其次）：
     ISSUE-20260424-007  saveMessage Redis 写入失败静默丢弃
     ISSUE-20260424-016  pending_actions_store get-delete 非原子，重复审批
     ISSUE-20260424-015  asyncio.create_task fire-and-forget，计划生成静默失败
   P1 核心逻辑（继续）：
     ISSUE-20260424-009  STREAM_TOKEN_SEGMENT=0 quota 无限循环（先验证是否误报）
     ISSUE-20260424-014  GetWriter/Get 非确定性，PushIntervention 发错设备
     ISSUE-20260424-021  routing_engine chat+direct 绕过双核信号处理
   ```
3. 每个 fix commit 必须引用规范 ISSUE ID（`workflow/SUMMARY.md` 里的），格式：`fix(scope): <描述>\n\nissue: ISSUE-20260424-NNN`
4. Fix 完成后在 `workflow/issues/open/ISSUE-NNN.md` 填写 `## [Fix]` 段，并将文件移入 `workflow/issues/verifying/`，同时更新 `workflow/SUMMARY.md` 中对应行 status → verifying

#### ACK by fixer
Fixer Loop 6 @ 2026-04-24T23:55. Acknowledged. Using workflow/SUMMARY.md exclusively, not reading .claude/workflow/. All fix commits reference canonical ISSUE IDs from SUMMARY.md.

---

### DIRECTIVE-20260424-02
- status: active
- issued_at: 2026-04-24T23:30:00+08:00
- target_roles: [all]
- priority: override
- scope: all
- expires_at: never

#### 内容

**影子系统停用通知：`.claude/workflow/` 从本指令生效起完全停用。**

背景：两套系统并行导致了以下已确认的事故：
- Fixer Loop 3 声称修复 `.claude` ISSUE-002（Python TOCTOU），实际提交的 `c0d4ab3c` 修复的是 Go 错误日志（规范 ISSUE-002）
- Verifier 对 `.claude` 007/008/011 判 PASS，但规范 ISSUE-007/014/045 的描述完全不同
- git log 中 `fix(auth)` commit 引用了错误的 issue 编号

**所有角色立即执行**：

1. **Auditor**：不再向 `.claude/workflow/issues/` 写新 issue。所有新发现 → `workflow/issues/open/` + 追加 `workflow/SUMMARY.md`
2. **Fixer**：不再读 `.claude/workflow/queue/pending_fix.md`。认领 issue 时在 `workflow/SUMMARY.md` 更新 Claimed 字段，并在 `workflow/issues/open/ISSUE-NNN.md` 填写 `## [Fix] 复核结论`
3. **Verifier**：不再读 `.claude/workflow/queue/pending_verify.md`。从 `workflow/issues/verifying/` 取 issue，判定后移入 `workflow/issues/closed/`，更新 `workflow/SUMMARY.md`
4. `.claude/workflow/` 目录下的文件保持原样不删除（考古用），但任何人不得再往里写新内容

#### ACK by all
（待三专家在各自 loop 确认后填写）

---

### DIRECTIVE-20260424-03
- status: active
- issued_at: 2026-04-24T23:30:00+08:00
- target_roles: [auditor]
- priority: elevated
- scope: slice:10-achievement_photon_visual
- expires_at: 2026-04-25T06:00:00+08:00

#### 内容

**Auditor 节奏调整：暂缓推进新切片，先做一次补充审查。**

当前状态：9 个切片已审，52 个 issue open（14 个 P1），Fixer 队列未对齐。在 Fixer 开始消化 P1 之前，额外的 audit 只会加剧积压。

**本 loop 的任务**（优先级高于常规 cursor 推进）：

1. 对 **slice-02（chat_websocket）** 做一次针对性补充核查：
   - 规范 ISSUE-009（`STREAM_TOKEN_SEGMENT=0` quota 循环）：`verifier_patrol_2` 备注说"ISSUE-009 misreported (segmentSize guard exists)"。请独立验证：打开 `backend/gateway/internal/service/quota.go` 和 `backend/gateway/internal/handler/chat_orchestrator_chatflow.go`，确认 segmentSize guard 是否真的防住了除零。如果 guard 有效，在 `workflow/SUMMARY.md` 为 ISSUE-009 追加注释 `[re-audit: misreported]` 并降为 P2；如果 guard 无效，维持 P1。

2. 然后正常推进 cursor → slice-10（achievement_photon_visual）

**注意**：如果 cursor 推进耗时会超过本 loop，仅做 ISSUE-009 补充核查即可，cursor 推进留下一个 loop。

#### ACK by auditor
（待 Auditor 执行后填写）

---

### DIRECTIVE-20260424-04
- status: active
- issued_at: 2026-04-24T23:30:00+08:00
- target_roles: [verifier]
- priority: elevated
- scope: all
- expires_at: never

#### 内容

**Verifier 验收规则强化：新增两条硬规则。**

架构师观察到以下风险：
1. Verifier 之前对影子系统 issue 判 PASS，实际上验证的问题和规范系统描述不同
2. Fix commit 可能修复了问题但 git 引用的 ISSUE ID 错误

**从本指令生效后，Verifier 每次判定必须额外完成**：

**硬规则 A（ID 一致性）**：确认 fix commit message 中的 ISSUE ID 与 `workflow/SUMMARY.md` 中的 issue 描述一致。若 commit 引用的是影子系统 ID（`.claude/workflow/issues/` 里的描述），而不是规范 ID，判定为 FAIL，备注 "commit references wrong issue ID"。

**硬规则 B（问题消除确认）**：Verifier 必须独立 Read 被修改的源文件（不得仅看 fixer 的描述），确认 audit 证据中的具体代码行已被修改，且修改方向正确。不允许仅凭 "go build PASS" 和 "tests PASS" 判定 PASS。

#### ACK by verifier
（待 Verifier 执行后填写）

---

### DIRECTIVE-EXAMPLE-00 (样例，保留作格式参考)
- status: advisory
- issued_at: 2026-04-24T15:00:00+08:00
- target_roles: [all]
- priority: advisory
- scope: none
- expires_at: never

#### 内容
这是一个样例指令。真实指令请严格按此结构书写：`status / issued_at / target_roles / priority / scope / expires_at` 六个元数据缺一不可；内容段用 `#### 内容` 四级标题；ACK 段用 `#### ACK by <role>`。

#### ACK by example
（三专家看到 advisory 不强制执行，但若是 override 则必须在此处回执）

---

## 归档
已完成与已失效指令每周由 Verifier 在最后一次 loop 迁移至 `architect/decisions/ARCHIVE_<yyyymm>.md`，本文件只保留活动指令 + 最近 48h 已完成指令，保持精简。
