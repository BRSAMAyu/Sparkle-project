# 深度审计：Community Signal Bridge 社群信号桥接链路

> 日期：2026-04-22 02:00
> 范围：`community_signal_bridge.py` 信号桥接 → `community_service.py` 事件发布 → `social_context_renderer.py` 上下文渲染 → `context_pack.py` AI 上下文 → `dual_core_router.py` 路由 → `community_handler.go` Go 网关 → `accountability.py` 责任伙伴 → Proto 定义 → Flutter Community 模块 → DB schema

## 审计发现

### P0 — 阻断性问题（2 项）

#### P0-1: 社群信号桥接输出完全未到达 AI 上下文，"Social → Router" 管道实质断裂
- **位置**: `backend/app/core/context_pack.py:405-805` (ContextPackBuilder) + `backend/app/orchestration/dual_core_router.py:37-58` (RoutingInput) + `backend/app/orchestration/social_context_renderer.py:6-25` (唯一渲染点)
- **问题**: Community Signal Bridge 处理的事件（小组任务完成、知识分享、成就广播）产生的输出仅写入 SystemUpdateService（用户通知）和 GalaxyService（掌握度），但**完全未流入 AI 对话上下文**
  ```python
  # social_context_renderer.py:6-25 — 唯一的社群→AI注入点
  def render_social_context_lines(payload: dict) -> list[str]:
      lines = ["【社交上下文】"]
      # 仅3个计数器，无实质内容：
      # - "你最近提到过 N 位学习相关人物"
      # - "你当前有 N 条关系型背景可供理解"
      # - "你有 N 条到期承诺待跟进"
      return lines if len(lines) > 1 else []
  ```
  ```python
  # context_pack.py — build() 包含的段:
  # ✅ preferences, goals, episodic, plan_context
  # ❌ 无 community/social 段

  # dual_core_router.py:37-58 — DualCoreRoutingInput 22 个字段:
  # ❌ 无 community/social/community_pressure/accountability_status 等字段
  ```
- **验证**: `orchestrator.py:66` 无 community import；`state_estimator_service.py:26-140` 的 `_compute_state()` 不包含任何社群信号；`routing_engine.py:263-322` 仅在 sufficiency 检查中使用 `recent_person_mentions`
- **影响**: 用户在社群中的活动（小组学习、责任伙伴打卡、知识分享）对 AI 对话行为零影响。Aurora Stage 17 规划的 "Social → Router" 管道完全不存在。社群是孤立的后花园，AI 是无社群感知的"金鱼"
- **修复**: (1) ContextPackBuilder 添加 community 段：提取活跃小组 + 责任伙伴状态 + 待办承诺 (2) DualCoreRoutingInput 添加 `has_active_accountability`, `pending_commitments`, `group_pressure_score` (3) 社群承诺到期时触发 cognitive_first 模式

#### P0-2: 群组访问控制绕过 — `get_group()` 接受可选 user_id，未鉴权可查看私密群组
- **位置**: `backend/app/services/community_service.py:~650` (get_group 定义) + `backend/gateway/internal/handler/proxy_routes.go:296-410` (路由注册)
- **问题**: `GroupService.get_group()` 的 `user_id` 参数为 `UUID | None`，当为 None 时不检查成员身份，直接返回群组详情
  ```python
  # community_service.py:~650
  async def get_group(db, group_id: UUID, user_id: UUID | None = None):
      group = await Group.get_by_id(db, group_id)
      # user_id 为 None 时跳过成员检查
      if user_id:
          member = await GroupService._get_active_member(db, group_id, user_id)
      return group_dict  # 返回完整群组信息
  ```
  ```go
  // proxy_routes.go:296-410 — 所有社群路由用 proxyWithHeaders，无额外鉴权
  community.GET("/groups/:id", h.proxyWithHeaders)
  ```
- **影响**: 如有 API 端点未传递 user_id 调用此方法，非成员可查看私密群组详情（名称、描述、成员数、设置）
- **修复**: (1) 将 `user_id` 改为必填参数 (2) Go Gateway 添加群组访问中间件（至少验证 public/private 属性）

---

### P1 — 重要问题（5 项）

#### P1-1: community_service.py 零事件发布，社群活动对事件驱动架构完全不可见
- **位置**: `backend/app/services/community_service.py` (2477 行)
- **问题**: community_service 有 `create_group()`, `send_message()`, `join_group()`, `check_in()` 等数十个写操作，但**零 `event_bus.publish()` 调用**
  ```python
  # community_service.py:45-59 — 唯一的"信号"记录方式
  def _record_community_signal(*, user_id, action, context, ...):
      asyncio.create_task(
          CommunitySignalCollector(cache_service.redis).record_interaction(...)
      )
  # → 仅写 Redis，不发布 Event Bus 事件
  ```
- **对比**: task_service.py 发布 `task.completed`；achievement_engine.py 发布 `achievement.unlocked`；galaxy_service.py 发布 `galaxy.node.updated`
- **影响**: 群组创建、消息发送、成员加入/退出、责任伙伴打卡等事件对 AchievementEngine、GalaxyEventConsumer、PlanHealthConsumer 等消费者完全不可见
- **修复**: 在关键写操作后添加 `await event_bus.publish()` 调用

#### P1-2: group_task_claims.personal_task_id 缺失索引，每次任务完成全表扫描
- **位置**: `backend/gateway/internal/db/schema.sql` — `group_task_claims` 表
- **问题**: task_service 完成任务时查询 `SELECT ... FROM group_task_claims WHERE personal_task_id = :id`，该列无索引
- **修复**: `CREATE INDEX idx_claim_personal_task ON group_task_claims(personal_task_id)`

#### P1-3: 资源分享仅处理 knowledge_node 类型，计划/任务/种子分享无反馈
- **位置**: `backend/app/services/community_signal_bridge.py:99`
  ```python
  if resource_type != "knowledge_node" or target_group_id is None:
      return  # 计划、任务、种子库分享 → 静默忽略
  ```
- **影响**: 用户分享计划/任务到小组后，无任何反馈信号回到个人系统
- **修复**: 扩展处理逻辑或至少发布事件供后续处理

#### P1-4: 责任伙伴系统缺失 Proto 定义，完全绕过 gRPC 合约
- **位置**: `proto/community_service.proto:230-268` (无 accountability RPC) vs `backend/app/api/v1/accountability.py` (完整 REST API)
- **问题**: 社群 Proto 定义了 Friends、Groups、Messages 系统 RPC，但 accountability（责任伙伴）系统**完全没有 Proto 定义**
- **影响**: Flutter 通过 REST 直接调用 accountability API，无法享受 gRPC 的类型安全和流式传输优势
- **修复**: 在 community_service.proto 添加 accountability RPC 定义

#### P1-5: AccountabilityPartnership 缺失唯一约束，可创建重复伙伴关系
- **位置**: `backend/app/models/accountability.py:42-112`
- **问题**: `AccountabilityPartnership` 模型有 `initiator_id` 和 `partner_id` 列但无 `UniqueConstraint('initiator_id', 'partner_id')`
- **影响**: 并发请求可创建多条相同伙伴关系（虽有应用层检查，但非原子）
- **修复**: 添加 `__table_args__ = (UniqueConstraint('initiator_id', 'partner_id', name='uq_accountability_pair'),)`

---

### P2 — 改进建议（3 项）

#### P2-1: Message reactions 数据结构 Proto 与后端不一致
- **位置**: `proto/community_service.proto:158-172` vs `backend/app/api/v1/community.py:419-435`
- **问题**: Proto 定义 `map<string, string>` (emoji → count)，后端实现 `dict[str, list[UUID]]` (emoji → user_id list)
- **修复**: 统一为 `map<string, list<UUID>>` 或添加中间转换层

#### P2-2: WS9 Feature Flag 静默禁用，无日志输出
- **位置**: `backend/app/social/accountability.py:130-136`
- **问题**: 所有 accountability 方法在 feature flag 关闭时返回默认值，无日志
- **修复**: 添加 `logger.warning("Accountability feature disabled")`

#### P2-3: 社群端点 Go Gateway 无速率限制
- **位置**: `proxy_routes.go:296-410`
- **问题**: 社群所有路由使用 `proxyWithHeaders` 无速率限制，仅依赖 Python 后端速率限制
- **修复**: 对群组创建、消息发送等高频操作添加 Gateway 级速率限制

---

### 合规项（4 项）

1. **责任伙伴授权** ✅ — `_ensure_partnership_access()` 严格验证用户归属 + 阻止关系 + 状态检查，所有 accountability 端点调用
2. **好友列表隔离** ✅ — `get_friends()` 的 `user_id` 为必填参数，查询显式过滤当前用户
3. **群组成员可见性** ✅ — `get_group_members()` 调用 `_require_active_member()` 验证成员身份
4. **WebSocket Origin 校验** ✅ — `HandleCommunityWS` 使用 `cfg.IsOriginAllowed(origin)` 验证来源

---

## 数据流图

```
社群用户操作 (群组学习/责任伙伴打卡/知识分享)
  │
  ├── [写入路径 A: Community Service] ⚠️ 零事件发布 (P1-1)
  │   ├── create_group() → DB write → 无 Event Bus 事件
  │   ├── send_message() → DB write → 无 Event Bus 事件
  │   ├── check_in() → DB write → 无 Event Bus 事件
  │   └── 仅 _record_community_signal() → Redis (非 Event Bus)
  │
  ├── [写入路径 B: Task → Bridge] ✅ 部分工作
  │   ├── task_service.complete_task() → event_bus.publish("task.completed", source="group")
  │   ├── TaskEventConsumer → 直接调用 bridge.handle_group_task_completed()
  │   │   ├── 查询 GroupTaskClaim ⚠️ 无 personal_task_id 索引 (P1-2)
  │   │   ├── 发布 community.group_task_completed 事件 ✅
  │   │   └── SystemUpdateService 通知 ✅
  │   └── 无独立 Event Consumer — bridge 仅被直接调用
  │
  ├── [写入路径 C: 资源分享 → Bridge]
  │   ├── API endpoint → 直接调用 bridge.handle_resource_shared()
  │   ├── knowledge_node → galaxy.node.updated + mastery +5.0 ✅
  │   └── plan/task/seed → return (静默忽略) ⚠️ (P1-3)
  │
  ├── [写入路径 D: 成就 → Bridge]
  │   ├── AchievementEventConsumer → bridge.broadcast_achievement_unlock()
  │   ├── 检查 share_achievements_to_community 偏好
  │   └── 发布到 Redis channel + Event Bus ✅
  │
  ↓ 桥接输出已产生
  │
  ├── [输出 1: SystemUpdateService] → 用户通知 ✅
  ├── [输出 2: GalaxyService] → 掌握度更新 ✅
  ├── [输出 3: Event Bus] → community.* 事件 ✅
  │
  ↓ 但所有输出均未到达 AI 上下文 ⚠️
  │
  ├── [AI 对话路径]
  │   ├── ContextPackBuilder.build()
  │   │   ├── ✅ preferences, goals, episodic, plan
  │   │   └── ❌ 无 community/social 段 (P0-1)
  │   │
  │   ├── social_context_renderer.py → 仅 3 行计数器文本
  │   │   └── ⚠️ 不影响路由决策
  │   │
  │   ├── DualCoreRoutingInput (22 字段)
  │   │   └── ❌ 无 community 字段 (P0-1)
  │   │
  │   ├── StateEstimator._compute_state()
  │   │   └── ❌ 无 community 信号 (P0-1)
  │   │
  │   └── 结果: AI 对社群活动完全"盲视"
  │
  ↓
  AI 行为: 无论用户是否有活跃社群活动，响应完全相同
```

---

## 建议修复方案

| 优先级 | 问题 | 修复方案 | 工作量 |
|--------|------|---------|--------|
| P0-1 | 社群信号未达 AI 上下文 | ContextPack + DualCoreRoutingInput 添加 community 段 | 中（~80 行 Python） |
| P0-2 | 群组访问控制绕过 | `get_group()` user_id 改必填 + Go 中间件 | 低（~20 行 Python + Go） |
| P1-1 | community_service 零事件发布 | 关键写操作添加 event_bus.publish() | 中（~60 行 Python） |
| P1-2 | group_task_claims 缺索引 | 添加 personal_task_id 索引 | 低（1 条 DDL） |
| P1-3 | 资源分享仅处理 knowledge_node | 扩展 bridge 处理逻辑 | 低（~20 行 Python） |
| P1-4 | Accountability 缺 Proto 定义 | 添加 RPC 到 community_service.proto | 中（~40 行 proto） |
| P1-5 | Partnership 缺唯一约束 | 添加 UniqueConstraint | 低（1 行 Python） |
