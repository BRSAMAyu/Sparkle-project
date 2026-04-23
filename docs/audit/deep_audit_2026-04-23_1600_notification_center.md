# 深度审计：Notification Center Service 通知中心服务完整链路

> 日期：2026-04-23
> 审计者：Chris (Session 3)
> 范围：`notification_center_service.py` → `notification_center.py` API → `Notification` + `InterventionRequest` + `NotificationInteraction` + `NotificationPreferences` 模型 → 前端通知中心 → DB schema

## 审计发现

### P0 — 阻断性问题（1 项）

#### P0-1: mark_all_notifications_read 使用逐行处理，N+1 查询 + 无上限，可能导致超时
- **位置**: `backend/app/services/notification_center_service.py:191-257`
- **问题**: `mark_all_notifications_read()` 先 SELECT 所有未读通知，再逐条 UPDATE + INSERT interaction。无数量上限
  ```python
  # :211-226 — SELECT 所有未读，逐条处理
  unread_system = result.scalars().all()
  for notif in unread_system:
      notif.is_read = True
      notif.read_at = _utcnow()
      count += 1
      await self._record_interaction(...)  # 每条 INSERT
  ```
- **影响**: 如果用户有 1000+ 未读通知，会执行 1000+ 次 `_record_interaction` flush，加上 N 次 ORM 跟踪变更，可能造成 DB 超时和内存溢出
- **修复**: 使用批量 UPDATE (`UPDATE ... SET is_read=True WHERE user_id=? AND is_read=False`) + 单次批量 INSERT interactions，或添加 LIMIT 子句

---

### P1 — 重要问题（5 项）

#### P1-1: notification_type 参数无枚举约束，静默接受任意字符串
- **位置**: `backend/app/api/v1/notification_center.py:68,124`
- **问题**: `notification_type: str = Query(...)` 接受任意值，但服务层仅处理 `'system'` 和 `'intervention'`。无效值（如 `'admin'`、`'../../etc'`）不返回 400 错误，静默返回 `False` 或无操作
- **修复**: 使用 `Literal['system', 'intervention']` 或 `Enum` 类型约束

#### P1-2: get_unified_notifications 分页在内存中合并后裁剪，偏移量不正确
- **位置**: `backend/app/services/notification_center_service.py:37-111`
- **问题**: 分别获取 system + intervention 各 `limit` 条，合并排序后取前 `limit` 条。但 `skip` 参数分别应用于两个子查询，导致：
  - 请求 `skip=10, limit=5`：system 返回 [11-15]，intervention 返回 [11-15]
  - 合并排序后只有最多 5 条，但实际应该返回全部数据的第 11-15 条
  - `total` 也无法正确计算（未返回）
- **修复**: 使用 UNION ALL 子查询 + 外层排序分页，或使用 DB 层 UNION

#### P1-3: search 参数未转义 LIKE 通配符，用户可注入 `%` 和 `_`
- **位置**: `backend/app/services/notification_center_service.py:386-387,415`
- **问题**: `ilike(f"%{filters.search}%")` 直接插入用户输入。用户搜索 `%` 将匹配所有记录，`_` 匹配单个字符
- **影响**: 非安全漏洞，但可导致意外的大量结果返回和性能问题
- **修复**: 转义 `filters.search` 中的 `%` 和 `_` 字符

#### P1-4: delete_notification 对系统通知硬删除而非软删除，审计追踪丢失
- **位置**: `backend/app/services/notification_center_service.py:300`
- **问题**: `await self.db.delete(notification)` 永久删除通知记录。`_record_interaction` 仅记录 `dismissed` action，但通知内容（title/content/data）不可恢复
- **影响**: 用户删除通知后，无法在通知历史中查看，也无法做通知效果分析
- **修复**: 使用软删除（`is_deleted=True`）而非硬删除

#### P1-5: quiet_hours 偏好存在但发送链路未检查
- **位置**: `backend/app/services/notification_center_service.py:449-495` (偏好) vs 发送链路
- **问题**: `NotificationPreferences` 有 `quiet_hours_enabled`、`quiet_hours_start`、`quiet_hours_end` 字段，但通知发送路径（`notification_push_service`）未检查这些偏好
- **影响**: 用户设置免打扰时段后仍收到推送通知
- **修复**: 在推送发送前检查 quiet_hours 偏好

---

### P2 — 改进建议（3 项）

#### P2-1: _record_interaction 的 time_to_action 可能为负数
- **位置**: `backend/app/services/notification_center_service.py:508`
- **问题**: `time_to_action = int((_utcnow() - created_at).total_seconds())` — 如果服务器时钟不同步或 `created_at` 来自未来，结果为负
- **修复**: `max(0, int(...))`

#### P2-2: 通知无 TTL/自动清理机制
- **位置**: `Notification` 表无过期机制
- **问题**: 通知无限累积，长期用户可能有数万条通知记录
- **修复**: 添加 90 天自动清理 Cron 任务

#### P2-3: get_notification_history 重复了 get_unified_notifications 的大部分逻辑
- **位置**: `notification_center_service.py:37-111` vs `:350-447`
- **问题**: 两个方法逻辑几乎相同（获取 system + intervention → 合并排序），但分页和过滤逻辑不同
- **修复**: 抽取共享的 `_fetch_combined_notifications()` 方法

---

### 合规项（3 项）

1. **用户隔离** ✅ — 所有 API 端点使用 `Depends(get_current_user)` + `user_id=current_user.id`，无跨用户访问风险
2. **分页限制** ✅ — `limit` 和 `page_size` 均有上限 100 (`Query(50, ge=1, le=100)`)
3. **事务安全** ✅ — 写入操作有 try/except + `db.rollback()` 保护

---

## 数据流图

```
Flutter NotificationCenterScreen
  │
  ├── GET /notifications → get_unified_notifications()
  │   ├── SELECT Notification ⚠️ (分页不精确 P1-2)
  │   ├── SELECT InterventionRequest
  │   └── 内存合并+排序 ⚠️ (N+limit 条取 limit)
  │
  ├── PUT /notifications/:id/read → mark_notification_read()
  │   ├── UPDATE Notification (is_read=True)
  │   └── INSERT NotificationInteraction ⚠️ (time_to_action 可负 P2-1)
  │
  ├── PUT /notifications/read-all → mark_all_notifications_read()
  │   ├── SELECT 所有未读 ⚠️ (无上限 P0-1)
  │   ├── 逐条 UPDATE + INSERT ⚠️ (N+1 P0-1)
  │   └── ⚠️ (notification_type 无枚举约束 P1-1)
  │
  ├── DELETE /notifications/:id → delete_notification()
  │   └── DELETE Notification ⚠️ (硬删除 P1-4)
  │
  ├── GET /notifications/history → get_notification_history()
  │   └── ⚠️ (search LIKE 通配符注入 P1-3)
  │
  └── GET/PUT /notifications/preferences
      └── quiet_hours 存储但 ⚠️ 发送未检查 (P1-5)
```

---

## 建议修复方案

| 优先级 | 问题 | 修复方案 | 工作量 |
|--------|------|---------|--------|
| P0-1 | mark_all 逐行处理 | 批量 UPDATE + 批量 INSERT | 低（~20 行） |
| P1-1 | notification_type 无枚举 | 改用 Literal 类型 | 低（~5 行） |
| P1-2 | 分页不精确 | DB 层 UNION ALL | 中（~40 行） |
| P1-3 | LIKE 通配符注入 | 转义 % 和 _ | 低（~5 行） |
| P1-4 | 硬删除 | 改为软删除 | 低（~10 行） |
| P1-5 | quiet_hours 未检查 | 推送前检查偏好 | 低（~15 行） |

---

## Chris (Session 3+4) 修复记录

| 原始发现 | 修复提交 | 状态 |
|----------|---------|------|
| P0-1 mark_all N+1 | `41a5f609` (S4) | **FIXED** — bulk UPDATE + batch INSERT, O(3N)→O(6) |
| P1-3 LIKE 通配符注入 | `89850053` (S4) | **FIXED** — _escape_like() helper, 5× ilike escaped |
| P2-1 time_to_action 负数 | `f9d253e1` (S4) | **FIXED** — max(0, int(...)) |

**备注**: P1-1 notification_type 无枚举 → 部分误报，API层已有 `if notification_type not in ['system', 'intervention']` 校验。P1-2 分页不精确、P1-4 硬删除、P1-5 quiet_hours 仍为架构级改进项。
