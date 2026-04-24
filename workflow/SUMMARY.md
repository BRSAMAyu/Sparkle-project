# ISSUE 汇总索引

> 三专家共同维护的唯一事实表。每 ISSUE 一行。Auditor 创建时追加行；Fixer/Verifier 就地更新状态字段；任何人**不得删除**他人写的行（已关闭行 7 日后由 Verifier 归档到 `closed/ARCHIVE_<yyyymm>.md`）。

## 活动 ISSUE

| ID | Slice | P | Status | Title | Claimed | Updated |
|----|-------|---|--------|-------|---------|---------|
| ISSUE-20260424-001 | 01 | P1 | closed | Go validateJWT 不检查 session_revoked:{sid}，设备下线不立即生效 | fixer@2026-04-24T20:45 | 21:00 PASS |
| ISSUE-20260424-002 | 01 | P1 | closed | AppleLogin UpdateUserLastLogin 和 UpsertUserSession 错误静默丢弃 | fixer@2026-04-24T21:45 | 22:15 PASS |
| ISSUE-20260424-003 | 01 | P1 | closed | Guest login 限流 100/15min 过于宽松，可被滥用刷号 | fixer@2026-04-24T22:48 | 22:45 PASS |
| ISSUE-20260424-004 | 01 | P2 | open | Guest login SELECT-INSERT 竞态条件，并发同 guest_id 返回 500 | - | 19:05 |
| ISSUE-20260424-005 | 01 | P2 | open | AppleLogin 用户创建/链接竞态，无 IntegrityError 处理 | - | 19:05 |
| ISSUE-20260424-006 | 01 | P2 | open | Go/Python JWT issuer/audience claims 处理需验证一致性 | - | 19:05 |
| ISSUE-20260424-007 | 02 | P1 | open | saveMessage Redis 写入失败静默丢弃，用户消息不可恢复丢失 | - | 19:30 |
| ISSUE-20260424-008 | 02 | P2 | verifying | 两套独立 WS 连接注册系统互不感知，用户可绕过全局限制 | fixer@89c88217 | 22:20 部分修复 |
| ISSUE-20260424-009 | 02 | P1 | open | STREAM_TOKEN_SEGMENT=0 导致 quota 记录无限循环 | - | 19:30 |
| ISSUE-20260424-010 | 02 | P2 | open | 客户端 active_tools 未做白名单校验可注入任意工具名 | - | 19:30 |
| ISSUE-20260424-011 | 02 | P2 | open | WS auth 检查在 Upgrade 之后，防御层位置不当 | - | 19:30 |
| ISSUE-20260424-012 | 02 | P2 | open | Flutter WS fallback 将 JWT 暴露在 URL query parameter 中 | - | 19:30 |
| ISSUE-20260424-013 | 02 | P1 | verifying | Protobuf 路径绕过 maxMessageLength 4000 字符应用层限制 | fixer@8fd4b32d | 22:20 已修复待验收 |
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
| ISSUE-20260424-027 | 05 | P1 | open | /health 端点未认证可访问，泄露 OpenClaw 基础设施详情 | - | 21:20 |
| ISSUE-20260424-028 | 05 | P1 | open | handoff_task 通用 Exception 捕获泄露内部错误消息 | - | 21:20 |
| ISSUE-20260424-029 | 05 | P2 | open | OpenClawClient 每次 execute 新建 httpx.AsyncClient 无连接池 | - | 21:20 |
| ISSUE-20260424-030 | 05 | P2 | open | _clear_failure_state 为空操作 stub，成功后不清除降级状态 | - | 21:20 |
| ISSUE-20260424-031 | 05 | P2 | open | _condition_matches 朴素字符串切片解析条件表达式，不支持转义 | - | 21:20 |
| ISSUE-20260424-032 | 05 | P2 | open | _promote_next_queued_intent TOCTOU 竞态可超出并发限制 | - | 21:20 |
| ISSUE-20260424-033 | 06 | P1 | open | spark_node 绕过 update_node_mastery pipeline，缺 audit/outbox/cache | - | 21:40 |
| ISSUE-20260424-034 | 06 | P1 | open | update_node_mastery legacy path 无 revision 时 read-modify-write 竞态 | - | 21:40 |
| ISSUE-20260424-035 | 06 | P2 | open | _find_nodes_by_keywords LIKE 通配符未转义，可匹配不相关节点 | - | 21:40 |
| ISSUE-20260424-036 | 06 | P2 | open | GalaxyRepository.getGalaxyEventsStream() 永久空流，SSE 端点未实现 | - | 21:40 |
| ISSUE-20260424-037 | 06 | P2 | open | auto_classify_task 用零 UUID 作 user_id 占位符，语义不正确 | - | 21:40 |
| ISSUE-20260424-038 | 06 | P2 | open | TaskEventListener consumer_name 含时间戳，重启后 pending 消息成孤儿 | - | 21:40 |
| ISSUE-20260424-039 | 07 | P1 | open | send_message 未调用 check_keyword_filter 和 slow_mode_seconds 检查 | - | 22:20 |
| ISSUE-20260424-040 | 07 | P1 | open | community_signal_bridge handle_resource_shared 双重 commit | - | 22:20 |
| ISSUE-20260424-041 | 07 | P2 | open | search_messages/group/user LIKE 通配符未转义 | - | 22:20 |
| ISSUE-20260424-042 | 07 | P2 | open | _record_community_signal asyncio.create_task fire-and-forget | - | 22:20 |
| ISSUE-20260424-043 | 07 | P2 | open | like_checkin/encourage_checkin 直接 db.commit() 绕过 session 管理约定 | - | 22:20 |
| ISSUE-20260424-044 | 07 | P2 | open | broadcast_achievement_unlock 使用 __import__("json") 代替正常 import | - | 22:20 |
| ISSUE-20260424-045 | 02 | P2 | closed | Flutter WS 重连耗尽静默清空 pending messages，不通知用户 | fixer@6db0c87f | 22:50 PASS |
| ISSUE-20260424-046 | 08 | P1 | open | AnalyzeError gRPC asyncio.create_task fire-and-forget，分析失败无感知 | - | 22:30 |
| ISSUE-20260424-047 | 08 | P2 | open | ErrorReplanBridge _count_recent_triggering_errors 无 SQL 日期过滤，全量加载 | - | 22:30 |
| ISSUE-20260424-048 | 08 | P2 | open | list_errors chapter/keyword LIKE 通配符未转义 | - | 22:30 |
| ISSUE-20260424-049 | 08 | P2 | open | delete_error 缺 is_deleted 过滤，已删错题重复删除返回 204 | - | 22:30 |
| ISSUE-20260424-050 | 08 | P2 | open | submit_review read-modify-write 竞态，并发复习丢失进度 | - | 22:30 |
| ISSUE-20260424-051 | 08 | P2 | open | _get_cohort_profile bare except 静默返回 None，cohort 数据永远空 | - | 22:30 |
| ISSUE-20260424-052 | 09 | P1 | open | log_session 先 commit 后发 event/write memory，失败不可恢复 | - | 23:00 |
| ISSUE-20260424-053 | 09 | P2 | open | _calculate_current_streak N+1 查询最多 365 次 DB 查询 | - | 23:00 |
| ISSUE-20260424-054 | 09 | P2 | open | log_session 不验证 duration_minutes 与 start/end_time 一致性 | - | 23:00 |
| ISSUE-20260424-055 | 09 | P2 | open | heatmap days 参数无上限，可请求全量历史 | - | 23:00 |
| ISSUE-20260424-056 | 09 | P2 | open | focus_service.py 4处 import logging 绕过 loguru 管道 | - | 23:00 |
| ISSUE-20260424-057 | 09 | P2 | open | log_session AchievementEngine 共享 session 事务边界不清 | - | 23:00 |

## 最近 7 日已关闭（趋势观察）

| ID | Slice | P | Verdict | Closed |
|----|-------|---|---------|--------|
<!-- Verifier 判 PASS 后追加 -->
| ISSUE-20260424-001 | 01 | P1 | PASS | 2026-04-24T21:00 |
| ISSUE-20260424-002 | 01 | P1 | PASS | 2026-04-24T22:15 |
| ISSUE-20260424-003 | 01 | P1 | PASS | 2026-04-24T22:45 |
| ISSUE-20260424-045 | 02 | P2 | PASS | 2026-04-24T22:50 |

## 统计快照（Verifier 每轮 loop 更新一次）

- round 0 进行中
- open: 52
- verifying: 0
- closed (7d): 4
- escalated: 0
- last_update: 2026-04-24T23:00:00+08:00
- slice_01_audit: 3 P1 + 3 P2, anchors personally read (7 files, 6 grep queries)
- slice_02_audit: 4 P1 + 4 P2, combined 2-loop audit (14 total anchors read)
- slice_03_audit: 2 P1 + 4 P2, anchors personally read (plan_review_service.py 2241L, plan_review_card.dart 1376L, agent_service.proto + agent_grpc_service.py)
- slice_04_audit: 1 P1 + 5 P2, anchors personally read (dual_core_router.py 647L, ux_envelope.py 1827L, prompts.py key sections + routing_engine.py integration)
- slice_05_audit: 2 P1 + 4 P2, anchors personally read (client.py 315L, executions.py 1000L, config.py 48L, intent_translator.py 220L, result_parser.py 122L, url_guard.py 118L, execution_service.py 3296L, execution_schedule_service.py 385L)
- slice_06_audit: 2 P1 + 4 P2, anchors personally read (galaxy_service.py 1000L, galaxy_service.proto 57L, galaxy_provider.dart 150L, galaxy_repository.dart 150L, event_listener.py 375L, stats_service.py 100L, structure_service.py 100L, collaborative_service.py 67L, crdt_persistence.py 119L, galaxy_grpc_service.py 170L, galaxy.py 300L)
- slice_07_audit: 2 P1 + 4 P2, anchors personally read (community_service.py 2482L, community_advanced_service.py 975L, community_signal_bridge.py 231L, community_signal_collector.py 172L, accountability.py API 1528L, accountability.py model 156L, community.py API 200L, proto/community_service.proto 324L, group_chat.go 116L)
- verifier_patrol_2: env-check pass; ISSUE-009 misreported (segmentSize guard exists); ISSUE-007/014 suggest P2 downgrade
- cross_ref_2026-04-24: .claude/workflow 影子系统与规范系统 ID 冲突已对齐：shadow-007→ISSUE-008(部分), shadow-008→ISSUE-013, shadow-011→ISSUE-045(新建)
- slice_09_audit: 1 P1 + 5 P2, anchors personally read (focus_service.py 587L, focus.py API 169L, focus.py model 54L, mindfulness_provider.dart 569L, focus_signal_processor.py 162L, focus_repository.dart 348L)
