# ISSUE 汇总索引

> 三专家共同维护的唯一事实表。每 ISSUE 一行。Auditor 创建时追加行；Fixer/Verifier 就地更新状态字段；任何人**不得删除**他人写的行（已关闭行 7 日后由 Verifier 归档到 `closed/ARCHIVE_<yyyymm>.md`）。

## 活动 ISSUE

| ID | Slice | P | Status | Title | Claimed | Updated |
|----|-------|---|--------|-------|---------|---------|
| ISSUE-20260424-001 | 01 | P1 | closed | Go validateJWT 不检查 session_revoked:{sid}，设备下线不立即生效 | fixer@2026-04-24T20:45 | 21:00 PASS |
| ISSUE-20260424-002 | 01 | P1 | closed | AppleLogin UpdateUserLastLogin 和 UpsertUserSession 错误静默丢弃 | fixer@2026-04-24T21:45 | 22:15 PASS |
| ISSUE-20260424-003 | 01 | P1 | closed | Guest login 限流 100/15min 过于宽松，可被滥用刷号 | fixer@2026-04-24T22:48 | 22:45 PASS |
| ISSUE-20260424-004 | 01 | P2 | closed | Guest login SELECT-INSERT 竞态条件，并发同 guest_id 返回 500 | fixer@b40e2e37 | 02:15 PASS |
| ISSUE-20260424-005 | 01 | P2 | open | AppleLogin 用户创建/链接竞态，无 IntegrityError 处理 | - | 19:05 |
| ISSUE-20260424-006 | 01 | P2 | open | Go/Python JWT issuer/audience claims 处理需验证一致性 | - | 19:05 |
| ISSUE-20260424-007 | 02 | P1 | closed | saveMessage Redis 写入失败静默丢弃，用户消息不可恢复丢失 | fixer@2026-04-24T23:15 | 23:55 closed (P2-downgraded, dispute accepted) |
| ISSUE-20260424-008 | 02 | P2 | open | 两套独立 WS 连接注册系统互不感知，用户可绕过全局限制 | fixer@89c88217 | 23:15 per-user limit已加，双系统问题仍open |
| ISSUE-20260424-009 | 02 | P1 | closed | STREAM_TOKEN_SEGMENT=0 导致 quota 记录无限循环 | fixer@2026-04-25T01:00 | 02:00 DISPUTED_UPHELD (misreported, guard exists) |
| ISSUE-20260424-010 | 02 | P2 | open | 客户端 active_tools 未做白名单校验可注入任意工具名 | - | 19:30 |
| ISSUE-20260424-011 | 02 | P2 | open | WS auth 检查在 Upgrade 之后，防御层位置不当 | - | 19:30 |
| ISSUE-20260424-012 | 02 | P2 | open | Flutter WS fallback 将 JWT 暴露在 URL query parameter 中 | - | 19:30 |
| ISSUE-20260424-013 | 02 | P1 | closed | Protobuf 路径绕过 maxMessageLength 4000 字符应用层限制 | fixer@8fd4b32d | 23:15 PASS |
| ISSUE-20260424-014 | 02 | P1 | closed | GetWriter/Get 非确定性返回，PushIntervention 可能发到错误设备 | fixer@2026-04-25T01:40 | 02:00 PASS |
| ISSUE-20260424-015 | 03 | P1 | closed | asyncio.create_task fire-and-forget，计划批准后任务生成静默失败 | fixer@2026-04-25T00:40 | 02:00 DISPUTED_UPHELD (try/except exists, P2) |
| ISSUE-20260424-016 | 03 | P1 | closed | pending_actions_store get-delete 非原子，并发 SubmitPlanReview 可重复审批 | fixer@2026-04-25T00:10 | 02:00 PASS |
| ISSUE-20260424-017 | 03 | P2 | open | gRPC handler plan_id 来源不一致，使用 request.plan_id 而非已验证存储值 | - | 20:15 |
| ISSUE-20260424-018 | 03 | P2 | open | track_rejection_count 在 redis=None 时静默降级，连续拒绝信息收集永不触发 | - | 20:15 |
| ISSUE-20260424-019 | 03 | P2 | open | _validate_feasibility 硬编码 liberal_arts 背景检查，不适用于多元用户画像 | - | 20:15 |
| ISSUE-20260424-020 | 03 | P2 | open | get_stored_plan 永远返回 None (stub)，计划恢复前无法验证计划存在 | - | 20:15 |
| ISSUE-20260424-021 | 04 | P1 | verifying | routing_engine chat+direct 快捷路径绕过全部双核信号处理 | fixer@2026-04-25 | 04:35 fix@6f43c40a |
| ISSUE-20260424-022 | 04 | P2 | open | intent_confidence=0.0 被 Python truthiness 静默覆盖为 0.7 | - | 20:35 |
| ISSUE-20260424-023 | 04 | P2 | open | cognitive_adjustments/execution_constraints 硬编码截断，不同模式比例不一致 | - | 20:35 |
| ISSUE-20260424-024 | 04 | P2 | open | BlockedPresentationHistoryStore 本地 fallback 无限增长无淘汰 | - | 20:35 |
| ISSUE-20260424-025 | 04 | P2 | open | _contains_any 子串匹配导致模式检测误报风险 | - | 20:35 |
| ISSUE-20260424-026 | 04 | P2 | open | gentle blocked_temperature 缺少 4 种 failure_kind 温和消息变体 | - | 20:35 |
| ISSUE-20260424-027 | 05 | P1 | closed | /health 端点未认证可访问，泄露 OpenClaw 基础设施详情 | fixer@2026-04-24T23:45 | 02:00 PASS |
| ISSUE-20260424-028 | 05 | P1 | closed | handoff_task 通用 Exception 捕获泄露内部错误消息 | fixer@2026-04-24T23:50 | 02:00 PASS |
| ISSUE-20260424-029 | 05 | P2 | open | OpenClawClient 每次 execute 新建 httpx.AsyncClient 无连接池 | - | 21:20 |
| ISSUE-20260424-030 | 05 | P2 | open | _clear_failure_state 为空操作 stub，成功后不清除降级状态 | - | 21:20 |
| ISSUE-20260424-031 | 05 | P2 | open | _condition_matches 朴素字符串切片解析条件表达式，不支持转义 | - | 21:20 |
| ISSUE-20260424-032 | 05 | P2 | open | _promote_next_queued_intent TOCTOU 竞态可超出并发限制 | - | 21:20 |
| ISSUE-20260424-033 | 06 | P1 | verifying | spark_node 绕过 update_node_mastery pipeline，缺 audit/outbox/cache | fixer@2026-04-25 | 04:35 fix@b1c54cab |
| ISSUE-20260424-034 | 06 | P1 | verifying | update_node_mastery legacy path 无 revision 时 read-modify-write 竞态 | fixer@2026-04-25 | 04:35 fix@b1c54cab |
| ISSUE-20260424-035 | 06 | P2 | open | _find_nodes_by_keywords LIKE 通配符未转义，可匹配不相关节点 | - | 21:40 |
| ISSUE-20260424-036 | 06 | P2 | open | GalaxyRepository.getGalaxyEventsStream() 永久空流，SSE 端点未实现 | - | 21:40 |
| ISSUE-20260424-037 | 06 | P2 | open | auto_classify_task 用零 UUID 作 user_id 占位符，语义不正确 | - | 21:40 |
| ISSUE-20260424-038 | 06 | P2 | open | TaskEventListener consumer_name 含时间戳，重启后 pending 消息成孤儿 | - | 21:40 |
| ISSUE-20260424-039 | 07 | P1 | verifying | send_message 未调用 check_keyword_filter 和 slow_mode_seconds 检查 | fixer@2026-04-25 | 04:35 fix@eb739fcf |
| ISSUE-20260424-040 | 07 | P1 | closed | community_signal_bridge handle_resource_shared 双重 commit | fixer@2026-04-25T01:20 | 02:00 PASS |
| ISSUE-20260424-041 | 07 | P2 | open | search_messages/group/user LIKE 通配符未转义 | - | 22:20 |
| ISSUE-20260424-042 | 07 | P2 | open | _record_community_signal asyncio.create_task fire-and-forget | - | 22:20 |
| ISSUE-20260424-043 | 07 | P2 | open | like_checkin/encourage_checkin 直接 db.commit() 绕过 session 管理约定 | - | 22:20 |
| ISSUE-20260424-044 | 07 | P2 | open | broadcast_achievement_unlock 使用 __import__("json") 代替正常 import | - | 22:20 |
| ISSUE-20260424-045 | 02 | P2 | closed | Flutter WS 重连耗尽静默清空 pending messages，不通知用户 | fixer@6db0c87f | 22:50 PASS |
| ISSUE-20260424-046 | 08 | P1 | claimed | AnalyzeError gRPC asyncio.create_task fire-and-forget，分析失败无感知 | fixer@2026-04-25 | reviewing |
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
| ISSUE-20260424-058 | 10 | P1 | open | after_commit fire-and-forget，解锁后关键副作用（通知/缓存/事件广播）静默丢失 | - | 23:10 |
| ISSUE-20260424-059 | 10 | P1 | open | WEEKEND_WARRIOR 三条无界查询加载全量用户历史，OOM 风险 | - | 23:10 |
| ISSUE-20260424-060 | 10 | P1 | open | get_close_to_unlock 对每个未解锁成就执行 _evaluate_progress，60-120 查询/调用 | - | 23:10 |
| ISSUE-20260424-061 | 10 | P2 | open | AchievementEventConsumer consumer_name 含时间戳，重启后 pending 消息成孤儿 | - | 23:10 |
| ISSUE-20260424-062 | 10 | P2 | open | ContractService.update_daily_progress 无日期守卫，单日可获多天契约积分 | - | 23:10 |
| ISSUE-20260424-063 | 10 | P2 | open | check_daily_first get-then-set TOCTOU 竞态，可获双倍首胜奖励 | - | 23:10 |
| ISSUE-20260424-064 | 11 | P1 | open | NotificationPushService 绕过用户通知偏好（免打扰时段、系统通知开关） | - | 09:04 |
| ISSUE-20260424-065 | 11 | P1 | open | calendar reminder_minutes 存储但从未消费，提醒功能完全未实现 | - | 09:04 |
| ISSUE-20260424-066 | 11 | P2 | open | _get_trends 逐日 N+1 查询，period='all' 可触发数千次 DB 查询 | - | 09:04 |
| ISSUE-20260424-067 | 11 | P2 | open | _get_hourly_distribution 无时间过滤加载用户全量交互记录 | - | 09:04 |
| ISSUE-20260424-068 | 11 | P2 | open | _find_notification_for_record 全量加载用户干预通知 Python 侧遍历 | - | 09:04 |
| ISSUE-20260424-069 | 11 | P2 | open | batch_operations 不发布 EventBus 事件，静默绕过事件管道 | - | 09:04 |
| ISSUE-20260424-070 | 11 | P2 | open | calendar.py get_event_summary 用 __import__("datetime") 代替正常 import | - | 23:25 |
| ISSUE-20260424-071 | 11 | P2 | open | Flutter _cancelReminders 硬编码最多 5 个提醒，超出部分永不取消 | - | 23:25 |
| ISSUE-20260424-072 | 12 | P1 | claimed | enqueue_from_chat_turn fire-and-forget，推断记忆写入失败静默丢弃 | fixer@2026-04-25 | disputed: _run_background has try/except + logger.warning, not silent; P2 not P1 |
| ISSUE-20260424-073 | 12 | P1 | open | _rate_limit_state 进程级 dict，多 worker 限流失效 | - | 09:09 |
| ISSUE-20260424-074 | 12 | P2 | open | _resolve_occurred_at UTC 时间戳设 locale 小时，"今晚"偏移+8h | - | 09:09 |
| ISSUE-20260424-075 | 12 | P2 | open | _degraded_queue 无界内存列表永不消费，死代码 | - | 09:09 |
| ISSUE-20260424-076 | 12 | P2 | open | MemoryPolicyEvaluator 每次写入查 DB 无缓存 | - | 09:09 |
| ISSUE-20260424-077 | 12 | P2 | open | TD-008 per-session 记忆限流未实现，单次对话可无限写入 | - | 09:09 |
| ISSUE-20260424-078 | 13 | P1 | open | _upsert_pattern 无 UNIQUE 约束，并发分析可创建重复行为定式 | - | 00:15 |
| ISSUE-20260424-079 | 13 | P1 | open | BehaviorSignalCollector 实例级 _local_cooldowns 每次 new 重置，Redis 不可用时冷却失效 | - | 00:15 |
| ISSUE-20260424-080 | 13 | P2 | open | get_patterns API 无分页不过滤 is_archived，返回全量含已归档 | - | 00:15 |
| ISSUE-20260424-081 | 13 | P2 | open | PatternType 枚举不对称 Python 3值 vs Flutter 4值，未知类型静默映射 | - | 00:15 |
| ISSUE-20260424-082 | 13 | P2 | open | get_today_capsules N+1 查询，逐胶囊检查收藏状态 | - | 00:15 |
| ISSUE-20260424-083 | 13 | P2 | open | 胶囊反馈数据收集但未闭环，反馈不回流AI无法个性化 | - | 00:15 |
| ISSUE-20260424-084 | 14 | P2 | open | list_libraries search LIKE 通配符未转义 | - | 00:35 |
| ISSUE-20260424-085 | 14 | P2 | open | findMySubscriptionForLibrary 客户端分页扫描 O(N/P) API调用 | - | 00:35 |
| ISSUE-20260424-086 | 14 | P2 | open | Translation API 捕获异常不记录日志，失败无法排查 | - | 00:35 |
| ISSUE-20260424-087 | 14 | P2 | open | rate_library 并发提交 IntegrityError 未处理返回误导性400 | - | 00:35 |
| ISSUE-20260424-088 | 14 | P2 | open | _blend_quality_score 每次 GET 重新计算无缓存 | - | 00:35 |
| ISSUE-20260424-089 | 14 | P2 | open | _SEED_VECTOR_RUNTIME_ENABLED 进程级全局开关，一用户失败禁用全进程 | - | 00:35 |
| ISSUE-20260424-090 | 15 | P1 | verifying | Simulation SSE streaming 泄露内部异常详情到客户端 | fixer@2026-04-25 | 04:35 fix@2496216f |
| ISSUE-20260424-091 | 15 | P1 | verifying | SimulationEngine._local_checkpoints 类级 dict 无限增长，OOM 风险 | fixer@2026-04-25 | 04:35 fix@cca4dcd7 |
| ISSUE-20260424-092 | 15 | P2 | open | prediction_theater_service.py 使用 import logging 绕过 loguru 管道 | - | 13:30 |
| ISSUE-20260424-093 | 15 | P2 | open | adopt_prediction bare except:pass 静默吞掉认知碎片创建错误 | - | 13:30 |
| ISSUE-20260424-094 | 15 | P2 | open | _find_related_concept_anchors ilike 通配符未转义 | - | 13:30 |
| ISSUE-20260424-095 | 15 | P2 | open | PredictionAccuracyTracker 用户索引 SET 积累过期 prediction ID 无清理 | - | 13:30 |
| ISSUE-20260424-096 | 16 | P1 | verifying | link_social / unlink_social db.add 无 db.commit 社交绑定不持久化 | fixer@2026-04-25 | 04:35 fix@a0d6face |
| ISSUE-20260424-097 | 16 | P1 | verifying | Leaderboard 全量加载用户到 Python 排序，OOM 风险 | fixer@2026-04-25 | 04:35 fix@8e683799 |
| ISSUE-20260424-098 | 16 | P2 | open | Leaderboard refresh-cache 端点无管理员校验且为空操作 stub | - | 03:15 |
| ISSUE-20260424-099 | 16 | P2 | open | Leaderboard get_top_three 泄露 str(e) 内部异常详情 | - | 03:15 |
| ISSUE-20260424-100 | 16 | P2 | open | Shop get_available_items N+1 ownership check 逐项查 DB | - | 03:15 |
| ISSUE-20260424-101 | 16 | P2 | open | update_schedule_preferences 无类型校验接受任意 dict[str, Any] | - | 03:15 |

## 最近 7 日已关闭（趋势观察）

| ID | Slice | P | Verdict | Closed |
|----|-------|---|---------|--------|
<!-- Verifier 判 PASS 后追加 -->
| ISSUE-20260424-001 | 01 | P1 | PASS | 2026-04-24T21:00 |
| ISSUE-20260424-002 | 01 | P1 | PASS | 2026-04-24T22:15 |
| ISSUE-20260424-003 | 01 | P1 | PASS | 2026-04-24T22:45 |
| ISSUE-20260424-045 | 02 | P2 | PASS | 2026-04-24T22:50 |
| ISSUE-20260424-013 | 02 | P1 | PASS | 2026-04-24T23:15 |
| ISSUE-20260424-007 | 02 | P1 | DISPUTED→P2 | 2026-04-24T23:55 |
| ISSUE-20260424-027 | 05 | P1 | PASS | 2026-04-25T02:00 |
| ISSUE-20260424-028 | 05 | P1 | PASS | 2026-04-25T02:00 |
| ISSUE-20260424-016 | 03 | P1 | PASS | 2026-04-25T02:00 |
| ISSUE-20260424-040 | 07 | P1 | PASS | 2026-04-25T02:00 |
| ISSUE-20260424-014 | 02 | P1 | PASS | 2026-04-25T02:00 |
| ISSUE-20260424-009 | 02 | P1 | DISPUTED_UPHELD | 2026-04-25T02:00 |
| ISSUE-20260424-015 | 03 | P1 | DISPUTED_UPHELD | 2026-04-25T02:00 |
| ISSUE-20260424-004 | 01 | P2 | PASS | 2026-04-25T02:15 |

## 统计快照（Verifier 每轮 loop 更新一次）

- round 0 进行中
- open: 81
- verifying: 0
- closed (7d): 14
- escalated: 0
- last_update: 2026-04-25T03:15:00+08:00
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
- slice_10_audit: 3 P1 + 3 P2, anchors personally read (achievement_engine.py 2292L, achievement_event_consumer.py 318L, achievement_repository.dart 920L, achievement_provider.dart 724L, photon_provider.dart 172L, photon_repository.dart 139L, visual_element_repository.dart 553L, close_to_unlock_provider.dart 125L)
- slice_11_audit: 2 P1 + 6 P2 (6 by concurrent session validated + 2 new), anchors personally read (calendar.py 413L, notification_push_service.py 323L, notification_center_service.py 1160L, notification_analytics_service.py 500L, calendar_repository.dart 454L)
- slice_13_audit: 2 P1 + 4 P2, anchors personally read (cognitive_service.py 681L, behavior_signal_collector.py 535L, cognitive.py API 126L, capsules.py 553L, cognitive models 106L, capsule_repository.dart 240L, cognitive_repository.dart 103L, capsule_provider.dart 188L, cognitive_provider.dart 95L, behavior_pattern_model.dart 72L, capsule_archive_provider.dart 106L)
- slice_14_audit: 0 P1 + 6 P2, anchors personally read (seed_libraries.py 789L, seed_library_service.py 700+L, seed_content.py 363L, seed_bridge.py 180L, translation.py 231L, translation_service.dart 157L, seed_library_repository.dart 598L, tool_registry.dart 380L, proxy_routes.go seed+translation routes)
- slice_15_audit: 2 P1 + 4 P2, anchors personally read (prediction_theater_service.py 3797L, simulation_engine.py 1779L, theater.py API 202L, simulation.py API 263L, learning_reports.py API 33L, learning_report_agent.py 1315L, session_cleanup.py 47L, simulation_state.py 13L, simulation_run_store.py 70L, proxy_routes.go theater/simulation/report routes)
- slice_16_audit: 2 P1 + 4 P2, anchors personally read (users.py API 697L, shop.py API 182L, leaderboards.py API 311L, user_settings.py API 146L, shop_service.py 450L, leaderboard_service.py 350L, proxy_routes.go user/shop/leaderboard/settings/profile routes)
