# Reviewer A — E07: 认知胶囊→行为分析→双核路由数据流
Timestamp: 2026-04-26T11:40:00+08:00
Chain Index: 18

## Chain Flow Summary
用户收藏认知胶囊后，`CapsuleFavoriteService` 写入 DB 并发布 `CAPSULE_FAVORITE_UPDATED` 事件。`ProfileEventConsumer` 收到事件后仅刷新 profile context 缓存，不创建任何 cognitive fragment。`BehaviorSignalCollector` 不订阅胶囊事件，因此胶囊收藏行为**从未**触发行为分析。`CapsuleFavoriteService.get_preferences()` 计算了有价值的用户偏好（深度偏好、科目亲和度），但该方法**零消费者**。胶囊收藏数据从未流入 `dual_core_router` 或 prompt assembly。

## Critical Issues 🔴

**1. 胶囊收藏→行为分析链路完全断裂**
- `backend/app/services/behavior_signal_collector.py` 只处理 5 种事件：`task_feedback`, `task_abandoned`, `task_completed`, `plan_replanned`, `behavior_pattern` — 没有 `capsule_favorite` 或 `capsule_feedback`
- Expected: 收藏胶囊 → `BehaviorSignalCollector` 创建 cognitive fragment（如"用户收藏了关于XX的胶囊"）→ `cognitive_service.analyze_behavior()` 提取行为模式
- Actual: 收藏胶囊 → DB 写入 + EventBus 事件 → ProfileEventConsumer 仅刷缓存 → **链路终止**
- Evidence: `behavior_signal_collector.py` 全文无 `capsule` 关键字

**2. 胶囊偏好数据零消费者——`get_preferences()` 死代码**
- `backend/app/services/capsule_favorite_service.py:200-260` 计算了 `content_depth_preference`, `subject_affinity`, `recent_notes`
- Expected: 这些偏好被 context_manager 或 prompt assembly 注入 AI prompt
- Actual: `context_manager.py` 全文无 `capsule` 引用；`prompts.py` 全文无 `capsule_favorite` 引用
- Evidence: `grep -r "get_preferences" backend/app/core/ backend/app/orchestration/` 返回零匹配（除 capsule_favorite_service 自身）
- 影响：用户花时间收藏的每个胶囊，系统都知道偏好，但 AI 教练完全忽略

## Major Issues 🟡

**3. `CAPSULE_FAVORITE_UPDATED` 事件处理过于轻量**
- `backend/app/services/profile_event_consumer.py:191-198` — `_handle_insight_signal_family_updated()` 只调用 `_invalidate_profile_context_cache()`
- Expected: 至少调用 `capsule_favorite_service.get_preferences()` 写入用户画像的 inferred 偏好
- Actual: 仅删除 Redis 缓存键，不做任何数据写入或转换
- 影响：缓存失效后重新加载 profile context 时，胶囊偏好数据依然不会出现在新的 context 中

**4. `DualCoreRoutingInput` 无胶囊相关字段**
- `backend/app/orchestration/dual_core_router.py:41-66` — `DualCoreRoutingInput` 有 `behavior_pattern_names`, `social_signals`, `srl_phase_hint`, `metacognition_hint` 但无任何胶囊/内容偏好字段
- `routing_engine.py:1482-1579` — `_get_cognitive_routing_signals()` 只读 `BehaviorPattern` 表
- Expected: 用户偏好深度内容 vs 浅层内容、偏好哪些科目 → 影响路由决策（如偏好深度内容则减少碎片化推送）
- Actual: 路由完全不考虑用户的认知胶囊偏好

**5. 胶囊反馈（feedback）同样不流入 AI**
- `CAPSULE_FEEDBACK_SUBMITTED` 也在 `INSIGHT_SIGNAL_EVENTS` 中 → 同样只刷缓存
- 用户给胶囊评分（rating）、标记 helpful、写评论 → 这些行为信号全部丢失
- Evidence: `grep -r "capsule_feedback" backend/app/orchestration/ backend/app/core/context_manager.py` 返回零匹配

## Minor Issues 🟢
None found beyond the above.

## Working Well ✅

1. **胶囊收藏 DB 层完整** — `capsule_favorite_service.py` 正确处理 add/remove/toggle，有 idempotency，发布 EventBus 事件
2. **Flutter UI 层正确** — `capsule_provider.dart:44-64` 使用 optimistic update，error 时 refresh 恢复状态
3. **空状态和加载状态** — `curiosity_capsule_screen.dart` 有 `EmptyState`、`LoadingIndicator`、`CustomErrorWidget`
4. **行为模式→路由链路本身通畅** — 当 `BehaviorSignalCollector` 创建的 cognitive fragment 触发 `analyze_behavior()` 且 confidence > 0.6 时，`_upsert_pattern()` → `behavior.pattern.updated` event → `routing_engine._get_cognitive_routing_signals()` 正确读取并传入 `DualCoreRoutingInput`
5. **行为模式 prompt 注入** — `prompts.py:3700-3748` 正确将 behavior patterns 渲染到 AI prompt 中

## Files Examined
- `backend/app/services/cognitive_service.py` (681 lines)
- `backend/app/services/behavior_signal_collector.py` (535 lines)
- `backend/app/orchestration/dual_core_router.py` (648 lines)
- `backend/app/services/capsule_favorite_service.py` (307 lines)
- `backend/app/services/profile_event_consumer.py` (257 lines)
- `backend/app/orchestration/routing_engine.py` (lines 630-706, 1482-1579)
- `backend/app/orchestration/prompts.py` (capsule/behavior sections)
- `backend/app/tools/prism_tools.py` (109 lines)
- `mobile/lib/features/cognitive/presentation/providers/capsule_provider.dart` (188 lines)
- `mobile/lib/features/cognitive/presentation/providers/cognitive_provider.dart` (95 lines)
- `mobile/lib/features/cognitive/data/repositories/capsule_repository.dart` (240 lines)
- `mobile/lib/features/cognitive/presentation/screens/curiosity_capsule_screen.dart` (183 lines)
- `backend/app/core/event_types.py` (capsule event definitions)
- `backend/app/core/context_manager.py` (no capsule references found)

## Confidence: High — 完整追踪了从 Flutter toggleFavorite → API → DB → EventBus → Consumer → Context → Router → Prompt 的全链路，每一层都有代码证据确认胶囊数据是否到达。
