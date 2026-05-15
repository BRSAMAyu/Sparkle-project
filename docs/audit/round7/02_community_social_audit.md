# Sparkle 社群与通知系统深度安全审计

> 审计范围: 社群功能、通知中心、排行榜、高级社群功能
> 审计日期: 2026-05-15
> 审计文件:
> - `backend/app/services/community_service.py` (3,303 行)
> - `backend/app/services/notification_center_service.py` (1,495 行)
> - `backend/app/services/leaderboard_service.py` (991 行)
> - `backend/app/services/community_advanced_service.py` (982 行)
> - `backend/app/api/v1/community.py` (API 路由层)
> - `backend/app/api/v1/notification_center.py` (API 路由层)
> - `backend/app/api/v1/leaderboards.py` (API 路由层)

---

## 一、架构总览

### 1.1 服务分层

```
API Router (FastAPI, JWT Auth, Rate Limiting)
    |
    v
Service Layer (业务逻辑, 权限校验)
    |
    v
ORM Layer (SQLAlchemy AsyncSession, soft-delete pattern)
    |
    v
PostgreSQL (关系 + pgvector + AGE)
```

### 1.2 模块划分

| 服务 | 职责 | 行数 |
|------|------|------|
| `FriendshipService` | 好友请求、接受、删除 | ~260 行 |
| `GroupService` | 群组 CRUD、成员管理、搜索 | ~550 行 |
| `GroupMessageService` | 群消息发送、编辑、撤回、反应 | ~530 行 |
| `PrivateMessageService` | 私聊消息发送、编辑、撤回 | ~310 行 |
| `CheckinService` | 群打卡、火苗奖励 | ~90 行 |
| `GroupTaskService` | 群任务创建、认领、完成 | ~260 行 |
| `UserBlockService` | 拉黑/解除、隐私 | ~170 行 |
| `UserSearchService` | 用户搜索(隐私控制) | ~100 行 |
| `NotificationCenterService` | 统一通知、干预、推送 | ~1,495 行 |
| `LeaderboardService` | 7种排行榜查询 | ~991 行 |
| `EncryptionService` | E2E 密钥管理 | ~100 行 |
| `ModerationService` | 群管理、敏感词、禁言 | ~180 行 |
| `ReportService` | 消息举报、审核 | ~100 行 |
| `FavoriteService` | 消息收藏 | ~100 行 |
| `ForwardService` | 消息转发 | ~60 行 |
| `BroadcastService` | 跨群广播 | ~55 行 |
| `MessageSearchService` | 全文搜索 | ~95 行 |
| `OfflineQueueService` | 离线消息队列 | ~145 行 |

### 1.3 安全亮点 (做得好的地方)

1. **群消息统一鉴权**: 所有群消息操作 (`send_message`, `get_messages`, `edit_message`, `revoke_message`, `update_reaction`, `get_thread_messages`, `search_messages`) 均通过 `GroupMember` 验证成员身份, 非成员无法操作。
2. **好友请求竞态保护**: `send_friend_request` 使用 `with_for_update()` 行锁 + `IntegrityError` 双重保护, 防止并发好友请求产生重复记录。
3. **软删除一致性**: `dissolve_group` 级联软删除所有子资源 (成员、消息、任务、文件、共享资源), 避免僵尸数据。
4. **消息可见性控制**: `_is_visible_to()` 实现了消息级别的 `self` 可见性控制, 支持私密消息场景。
5. **慢速模式**: 群消息发送前检查 `slow_mode_seconds`, 防止刷屏。
6. **关键词过滤**: 群消息发送前通过 `check_keyword_filter` 检测敏感词。
7. **火堆行锁**: `complete_task` 使用 `begin_nested()` + `with_for_update()` 保护计数器一致性。
8. **通知疲劳检测**: 连续 3 次拒绝触发 `notification.fatigue_detected` 事件, 关注用户体验。
9. **排行榜查询优化**: 全局榜使用 SQL ORDER BY + LIMIT, 避免加载所有用户到内存。
10. **举报权限分离**: 私信举报只能由超级管理员审核, 群消息举报由群管理员审核。

---

## 二、问题报告

### P0 - 严重 (生产安全风险)

#### P0-01: 跨群广播端点缺少速率限制

- **位置**: `backend/app/api/v1/community.py:4641` (`POST /broadcast`)
- **描述**: 跨群广播 (`/broadcast`) 端点没有配置 `@limiter.limit()` 速率限制。攻击者可以在短时间内向多个群组发送大量广播消息, 形成消息轰炸。
- **影响**: 管理员账号被盗后, 可被用于向所有管理的群组发送垃圾广播, 严重影响所有群成员体验。
- **修复建议**: 添加速率限制, 如 `@limiter.limit("3/minute")`。

---

#### P0-02: 群组排行榜未验证成员身份, 泄露群内数据

- **位置**: `backend/app/services/leaderboard_service.py:428-502` (`_get_group_leaderboard`)
- **描述**: `_get_group_leaderboard` 在 `group_id` 存在时, 直接查询 `GroupMember` 获取所有成员的火焰贡献值, 但不验证 `current_user_id` 是否是该群组成员。任何已认证用户可通过指定 `group_id` 查看任意群组的成员排名和贡献值, 即使该群组是私有的。
- **影响**: 非成员可以获取私有群组的成员列表、成员火焰贡献值等内部数据, 构成跨用户数据泄露。
- **修复建议**: 在查询成员前验证 `current_user_id` 是否为该群组的活跃成员:
  ```python
  # 在查询 members_query 前添加
  caller = await db.execute(
      select(GroupMember).where(
          GroupMember.group_id == request.group_id,
          GroupMember.user_id == current_user_id,
          GroupMember.not_deleted_filter(),
      )
  )
  if not caller.scalar_one_or_none():
      raise ValueError("不是群组成员")
  ```

---

#### P0-03: 私信发送不验证接收方是否拉黑发送方

- **位置**: `backend/app/services/community_service.py:2466-2536` (`PrivateMessageService.send_message`)
- **描述**: 私信发送仅检查是否存在 `BLOCKED` 状态的 `Friendship`, 但 `BLOCKED` 是 `Friendship` 表中的状态枚举值, 而实际拉黑功能使用的是独立的 `UserBlock` 表。`PrivateMessageService.send_message` 只查询 `Friendship.status == BLOCKED`, 不查询 `UserBlock` 表。如果用户 A 通过 `UserBlockService` 拉黑了用户 B (创建 `UserBlock` 记录并软删除 `Friendship`), 则用户 B 仍然可以给用户 A 发送私信, 因为 `Friendship` 记录已被软删除, 查询返回 `None`, 不触发拦截。
- **影响**: 被拉黑的用户仍可发送私信给拉黑者, 严重违反隐私意图, 可能被用于骚扰。
- **修复建议**: 在私信发送逻辑中额外调用 `UserBlockService.has_block_relationship()`:
  ```python
  if await UserBlockService.has_block_relationship(db, sender_id, data.target_user_id):
      raise ValueError("消息发送失败")
  ```

---

#### P0-04: `mark_as_sent` 和 `mark_as_failed` 不验证消息归属

- **位置**: `backend/app/services/community_advanced_service.py:894-929` (`OfflineQueueService.mark_as_sent`, `mark_as_failed`)
- **描述**: `mark_as_sent` 和 `mark_as_failed` 仅通过 `message_id` 查询消息, 不验证该消息是否属于当前操作的用户。任何已认证用户可以通过猜测或枚举 `message_id` 来修改其他用户的离线消息状态。
- **影响**: 攻击者可以标记其他用户的离线消息为已发送或失败, 破坏消息投递的可靠性。
- **修复建议**: 在查询中添加 `user_id` 过滤:
  ```python
  select(OfflineMessageQueue).where(
      OfflineMessageQueue.id == message_id,
      OfflineMessageQueue.user_id == user_id  # 添加归属校验
  )
  ```

---

### P1 - 高优先级

#### P1-01: 排行榜 `get_my_rank` 使用 `limit=100` 截断导致排名不准

- **位置**: `backend/app/services/leaderboard_service.py:100-159` (`get_my_rank`)
- **描述**: `get_my_rank` 使用 `limit=100` 获取排行榜数据, 然后在 Python 中线性搜索用户排名。如果用户排名在 100 名之后, 将返回 `rank=0`。注释中承认 "For accurate ranking in large systems, consider using COUNT queries instead",但当前实现并未修正。
- **影响**: 大量用户在全局榜中无法获取真实排名, 返回 `rank=0` 和 `percentile=None`, 影响用户体验和激励效果。
- **修复建议**: 使用 `COUNT` 子查询计算精确排名, 而非加载前 100 条后在 Python 中查找。

---

#### P1-02: 好友搜索 SQL LIKE 注入风险

- **位置**: `backend/app/services/community_service.py:2979-2987` (`UserSearchService.search_users`)
- **描述**: 搜索查询使用 `f"%{query}%"` 构建 LIKE 模式, 用户输入未转义 `%` 和 `_` 通配符。攻击者可输入 `%` 或 `_` 来匹配意外的用户数据。虽然 SQLAlchemy 参数化查询防止了 SQL 注入, 但 LIKE 通配符未转义可能导致信息泄露 (如 `%` 匹配所有用户)。
- **影响**: 攻击者可使用 `%` 搜索获取完整用户列表, 绕过隐私设置的 `SearchVisibility` 精确匹配意图。
- **修复建议**: 对 `query` 参数中的 `%` 和 `_` 进行转义 (与 `notification_center_service.py` 中的 `_escape_like` 类似)。

---

#### P1-03: 群消息搜索同样存在 LIKE 通配符问题

- **位置**: `backend/app/services/community_service.py:1941-1944` (`GroupMessageService.search_messages`) 和 `community_service.py:2693-2698` (`PrivateMessageService.search_messages`)
- **描述**: 两个搜索方法均使用 `f"%{keyword}%"` 且未转义 LIKE 通配符。
- **影响**: 用户可通过 `%` 或 `_` 通配符获取超出预期的搜索结果。
- **修复建议**: 统一使用 `_escape_like()` 函数转义搜索关键词。

---

#### P1-04: 公钥查询无访问控制

- **位置**: `backend/app/api/v1/community.py:4206` (`GET /encryption/keys/{user_id}`)
- **描述**: 任何已认证用户可查询任意用户的公钥列表, 返回完整的公钥内容、设备 ID、密钥类型等。虽然公钥本身设计上是公开的, 但暴露设备 ID 等元数据可能泄露用户设备指纹信息。
- **影响**: 攻击者可枚举所有用户 ID 获取设备指纹信息, 用于追踪用户多设备使用情况。
- **修复建议**: 限制返回字段, 仅返回 `public_key` 和 `key_type`, 不返回 `device_id`; 或限制只有好友/群成员可查询。

---

#### P1-05: `flag_misleading` 不验证举报者身份

- **位置**: `backend/app/services/community_service.py:3120-3142` (`CommunityResourceScorer.flag_misleading`)
- **描述**: `flag_misleading` 接收 `reporter_id` 参数但不验证举报者是否有权限访问该资源, 也不检查同一用户是否重复举报。攻击者可反复调用此接口使资源质量分数快速下降至阈值以下被隐藏。
- **影响**: 恶意用户可通过重复举报使合法资源被自动隐藏, 构成拒绝服务攻击。
- **修复建议**: 添加举报者去重 (同一用户只能举报一次); 检查举报者是否有权访问该资源; 添加速率限制。

---

#### P1-06: `get_group` 未检查私有群组可见性

- **位置**: `backend/app/services/community_service.py:650-715` (`GroupService.get_group`)
- **描述**: `get_group` 通过 `group_id` 直接获取群组详情, 不检查 `is_public` 属性。非成员可以查看私有群组 (`is_public=False`) 的完整信息, 包括名称、描述、公告、成员数量等。
- **影响**: 私有群组的元数据 (名称、描述、标签、成员数、公告) 对非成员完全可见, 违反群组隐私意图。
- **修复建议**: 当 `is_public=False` 时, 验证 `user_id` 是群组成员; 非成员仅返回最少信息 (名称和"这是私有群组") 或直接拒绝。

---

#### P1-07: 火焰贡献值可被操纵 (打卡奖励无上限防护)

- **位置**: `backend/app/services/community_service.py:2090-2180` (`CheckinService.checkin`)
- **描述**: 打卡奖励计算中, `base_flame=10`, `streak_bonus` 最高 +20, `duration_bonus` 最高 +30。但 `today_duration_minutes` 来自客户端提交的 `CheckinRequest`, 没有服务端验证。客户端可提交 `today_duration_minutes=999` 获取最大 `duration_bonus`。同时, 火焰值直接影响 `LeaderboardService._get_group_leaderboard` 的排名。
- **影响**: 用户可通过伪造学习时长刷火焰贡献值, 操纵群组排行榜排名, 影响排行榜公平性。
- **修复建议**: 服务端应基于实际学习记录 (如 `UserNodeStatus.last_study_at`) 验证学习时长, 而非信任客户端提交值。

---

### P2 - 中等优先级

#### P2-01: 通知中心 `get_unified_notifications` 可能返回超过 `limit` 条记录

- **位置**: `backend/app/services/notification_center_service.py:196-311`
- **描述**: 该方法分别查询 system (limit)、intervention notification (limit)、intervention request (limit)、push (limit) 四个来源, 合并后再排序截断。在最坏情况下, 返回 4*limit 条记录后才截断, 浪费查询资源。类似问题也存在于 `get_notification_history`。
- **影响**: 性能浪费, 在高通知量用户场景下可能导致响应延迟。
- **修复建议**: 先计算各来源的总数, 再按比例分配 limit; 或使用 UNION ALL 查询合并后再分页。

---

#### P2-02: `_find_notification_for_record` 全表扫描

- **位置**: `backend/app/services/notification_center_service.py:1454-1471`
- **描述**: `_find_notification_for_record` 查询用户所有干预类通知, 然后在 Python 中遍历 `data.record_id` 进行匹配。当用户有大量干预通知时, 这会导致大量无效数据加载。
- **影响**: 活跃用户可能有数百条通知, 每次调用此方法都会加载所有通知到内存。
- **修复建议**: 使用 JSON 查询 (PostgreSQL `@>` 操作符) 在数据库层面过滤:
  ```python
  .where(Notification.data.op('@>')({"record_id": str(record_id)}))
  ```

---

#### P2-03: `find_users_with_similar_goals` 对每个候选者调用 `_accepted_friend_ids`

- **位置**: `backend/app/services/community_service.py:3279-3282`
- **描述**: 对 200 个候选目标中的每一个, 都调用 `_accepted_friend_ids(db, cand_user.id)` 查询该用户的所有好友。这产生了 N+1 查询问题, 200 个候选 = 200 次额外 DB 查询。
- **影响**: 严重的性能问题, 每次调用产生约 200 次额外数据库查询。
- **修复建议**: 批量查询所有候选用户的好友关系, 在 Python 中计算交集。

---

#### P2-04: `get_group_members` 返回完整用户对象

- **位置**: `backend/app/services/community_service.py:717-756` (`GroupService.get_group_members`)
- **描述**: 成员列表使用 `selectinload(GroupMember.user)` 预加载完整用户对象。根据 ORM 模型, `User` 对象可能包含 `email`、`phone`、`settings` 等敏感字段。返回给前端时需要确保序列化层过滤了敏感字段。
- **影响**: 如果 API 响应未做字段过滤, 群成员可看到其他成员的 PII 信息。
- **修复建议**: 确认 API 响应的序列化模型 (`GroupMemberInfo`) 仅包含公开字段 (username, nickname, avatar_url), 不包含 email/phone。

---

#### P2-05: 全局排行榜缺少分页机制

- **位置**: `backend/app/services/leaderboard_service.py:205-317` (`_get_global_leaderboard`)
- **描述**: 全局排行榜仅支持 `LIMIT` 截断, 没有 `OFFSET` 分页。`LeaderboardRequest` 有 `offset` 字段但未在 `_get_global_leaderboard` 中使用。`total_participants` 固定返回 -1。
- **影响**: 无法翻页查看完整排行榜; 前端无法知道总参与人数。
- **修复建议**: 在查询中应用 `OFFSET`; 添加 `COUNT` 查询计算总参与人数。

---

#### P2-06: 群组搜索的 `keyword` 注入 LIKE 通配符

- **位置**: `backend/app/services/community_service.py:500-507` (`GroupService.search_groups`)
- **描述**: 与 P1-02/P1-03 相同的问题, `keyword` 未转义 LIKE 通配符。
- **修复建议**: 统一使用 `_escape_like()` 函数。

---

#### P2-07: 离线队列清理不验证调用方身份

- **位置**: `backend/app/services/community_advanced_service.py:954-967` (`OfflineQueueService.cleanup_expired`)
- **描述**: `cleanup_expired` 不接受 `user_id` 参数, 任何调用者都可以触发过期消息清理。如果暴露为 API 端点, 可能被滥用。同时, 它使用 `from sqlalchemy import update` 在方法内部重复导入。
- **影响**: 低风险, 主要影响是代码质量和潜在的资源浪费。
- **修复建议**: 确认此方法仅由 Celery 定时任务调用, 不暴露为 API 端点; 移除内部重复导入。

---

#### P2-08: 好友推荐和群组推荐缺少速率限制

- **位置**: `backend/app/api/v1/community.py:1588-1623` (`GET/POST /friends/recommendations/*`), `1906-1937` (`GET/POST /groups/recommendations/*`)
- **描述**: 好友推荐接口有 `@limiter.limit("10/minute")`, 但群组推荐的 GET 和 POST 端点均没有速率限制。群组推荐反馈 (`POST /groups/recommendations/feedback`) 可被重复调用。
- **影响**: 群组推荐 API 可能被滥用进行数据采集。
- **修复建议**: 为群组推荐端点添加速率限制。

---

#### P2-09: `get_topics` 不验证群组成员身份

- **位置**: `backend/app/services/community_advanced_service.py:816-833` (`MessageSearchService.get_topics`)
- **描述**: `get_topics` 直接查询指定群组的话题列表, 不验证调用者是否是群组成员。非成员可以获取群组的所有话题及其消息数量。
- **影响**: 私有群组的话题和活跃度信息对外泄露。
- **修复建议**: 添加群组成员身份验证。

---

#### P2-10: 消息转发不检查目标用户拉黑关系

- **位置**: `backend/app/services/community_advanced_service.py:620-681` (`ForwardService.forward_message`)
- **描述**: 当转发目标是私信 (`target_user_id`) 时, 不检查目标用户是否拉黑了发送方。与 P0-03 类似, 被拉黑用户仍可通过转发功能发送消息。
- **影响**: 拉黑可被转发功能绕过。
- **修复建议**: 在转发到私信目标前调用 `UserBlockService.has_block_relationship()`。

---

## 三、汇总

| 等级 | 数量 | 问题列表 |
|------|------|----------|
| P0 | 4 | P0-01 广播无速率限制, P0-02 群排行榜越权, P0-03 私信绕过拉黑, P0-04 离线队列越权 |
| P1 | 7 | P1-01 排名不准, P1-02~03 LIKE注入, P1-04 公钥暴露, P1-05 举报滥用, P1-06 私有群信息泄露, P1-07 火焰操纵 |
| P2 | 10 | P2-01~10 通知性能、N+1查询、PII暴露、分页缺失、话题越权、转发绕过等 |

### 优先修复建议

**立即修复 (P0)**:
1. P0-02: 在 `_get_group_leaderboard` 添加成员身份验证 — 一行代码修复, 影响面大
2. P0-03: 在 `PrivateMessageService.send_message` 添加 `UserBlock` 检查 — 关键隐私保护
3. P0-01: 在 `/broadcast` 端点添加 `@limiter.limit("3/minute")` — 一个装饰器修复
4. P0-04: 在 `mark_as_sent` / `mark_as_failed` 添加 `user_id` 过滤

**短期修复 (P1)**:
- P1-06 私有群可见性和 P1-07 火焰操纵应在下一迭代修复
- P1-02/P1-03 统一引入 `_escape_like()` 工具函数
