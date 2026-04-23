# ISSUE 汇总索引

> 三专家共同维护的唯一事实表。每 ISSUE 一行。Auditor 创建时追加行；Fixer/Verifier 就地更新状态字段；任何人**不得删除**他人写的行（已关闭行 7 日后由 Verifier 归档到 `closed/ARCHIVE_<yyyymm>.md`）。

## 活动 ISSUE

| ID | Slice | P | Status | Title | Claimed | Updated |
|----|-------|---|--------|-------|---------|---------|
| ISSUE-20260424-001 | 01 | P1 | open | Go validateJWT 不检查 session_revoked:{sid}，设备下线不立即生效 | fixer@2026-04-24T20:35 | 20:35 |
| ISSUE-20260424-002 | 01 | P1 | open | AppleLogin UpdateUserLastLogin 和 UpsertUserSession 错误静默丢弃 | - | 19:05 |
| ISSUE-20260424-003 | 01 | P1 | open | Guest login 限流 100/15min 过于宽松，可被滥用刷号 | - | 19:05 |
| ISSUE-20260424-004 | 01 | P2 | open | Guest login SELECT-INSERT 竞态条件，并发同 guest_id 返回 500 | - | 19:05 |
| ISSUE-20260424-005 | 01 | P2 | open | AppleLogin 用户创建/链接竞态，无 IntegrityError 处理 | - | 19:05 |
| ISSUE-20260424-006 | 01 | P2 | open | Go/Python JWT issuer/audience claims 处理需验证一致性 | - | 19:05 |
| ISSUE-20260424-007 | 02 | P1 | open | saveMessage Redis 写入失败静默丢弃，用户消息不可恢复丢失 | - | 19:30 |
| ISSUE-20260424-008 | 02 | P2 | open | 两套独立 WS 连接注册系统互不感知，用户可绕过全局限制 | - | 19:30 |
| ISSUE-20260424-009 | 02 | P1 | open | STREAM_TOKEN_SEGMENT=0 导致 quota 记录无限循环 | - | 19:30 |
| ISSUE-20260424-010 | 02 | P2 | open | 客户端 active_tools 未做白名单校验可注入任意工具名 | - | 19:30 |
| ISSUE-20260424-011 | 02 | P2 | open | WS auth 检查在 Upgrade 之后，防御层位置不当 | - | 19:30 |
| ISSUE-20260424-012 | 02 | P2 | open | Flutter WS fallback 将 JWT 暴露在 URL query parameter 中 | - | 19:30 |
| ISSUE-20260424-013 | 02 | P1 | open | Protobuf 路径绕过 maxMessageLength 4000 字符应用层限制 | - | 19:35 |
| ISSUE-20260424-014 | 02 | P1 | open | GetWriter/Get 非确定性返回，PushIntervention 可能发到错误设备 | - | 19:35 |
| ISSUE-20260424-015 | 03 | P1 | open | asyncio.create_task fire-and-forget，计划批准后任务生成静默失败 | - | 20:15 |
| ISSUE-20260424-016 | 03 | P1 | open | pending_actions_store get-delete 非原子，并发 SubmitPlanReview 可重复审批 | - | 20:15 |
| ISSUE-20260424-017 | 03 | P2 | open | gRPC handler plan_id 来源不一致，使用 request.plan_id 而非已验证存储值 | - | 20:15 |
| ISSUE-20260424-018 | 03 | P2 | open | track_rejection_count 在 redis=None 时静默降级，连续拒绝信息收集永不触发 | - | 20:15 |
| ISSUE-20260424-019 | 03 | P2 | open | _validate_feasibility 硬编码 liberal_arts 背景检查，不适用于多元用户画像 | - | 20:15 |
| ISSUE-20260424-020 | 03 | P2 | open | get_stored_plan 永远返回 None (stub)，计划恢复前无法验证计划存在 | - | 20:15 |
| ISSUE-20260424-021 | 04 | P1 | open | routing_engine chat+direct 快捷路径绕过全部双核信号处理 | - | 20:35 |
| ISSUE-20260424-022 | 04 | P2 | open | intent_confidence=0.0 被 Python truthiness 静默覆盖为 0.7 | - | 20:35 |
| ISSUE-20260424-023 | 04 | P2 | open | cognitive_adjustments/execution_constraints 硬编码截断，不同模式比例不一致 | - | 20:35 |
| ISSUE-20260424-024 | 04 | P2 | open | BlockedPresentationHistoryStore 本地 fallback 无限增长无淘汰 | - | 20:35 |
| ISSUE-20260424-025 | 04 | P2 | open | _contains_any 子串匹配导致模式检测误报风险 | - | 20:35 |
| ISSUE-20260424-026 | 04 | P2 | open | gentle blocked_temperature 缺少 4 种 failure_kind 温和消息变体 | - | 20:35 |

## 最近 7 日已关闭（趋势观察）

| ID | Slice | P | Verdict | Closed |
|----|-------|---|---------|--------|
<!-- Verifier 判 PASS 后追加 -->

## 统计快照（Verifier 每轮 loop 更新一次）

- round 0 进行中
- open: 26
- verifying: 0
- closed (7d): 0
- escalated: 0
- last_update: 2026-04-24T20:35:00+08:00
- slice_01_audit: 3 P1 + 3 P2, anchors personally read (7 files, 6 grep queries)
- slice_02_audit: 4 P1 + 4 P2, combined 2-loop audit (14 total anchors read)
- slice_03_audit: 2 P1 + 4 P2, anchors personally read (plan_review_service.py 2241L, plan_review_card.dart 1376L, agent_service.proto + agent_grpc_service.py)
- slice_04_audit: 1 P1 + 5 P2, anchors personally read (dual_core_router.py 647L, ux_envelope.py 1827L, prompts.py key sections + routing_engine.py integration)
- verifier_patrol_2: env-check pass; ISSUE-009 misreported (segmentSize guard exists); ISSUE-007/014 suggest P2 downgrade
