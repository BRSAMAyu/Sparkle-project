# FV-11 · Mobile CRDT 真实合并 + ACK · 完成报告

**Agent**: codex-agent-11
**Branch**: codex/FV-11-mobile-crdt-ack
**Date**: 2026-05-02
**Status**: PARTIAL - mobile CRDT/ACK implementation complete; full Flutter integration test is blocked by unrelated compile errors already present in other FV worktree files.

## 1. 5/5 标准达成情况

| # | 标准 | 状态 | 证据 |
|---|------|------|------|
| 1 | 引入 Dart Yjs 兼容库或 minimal CRDT | ✅ | `mobile/lib/core/offline/offline_crdt_document.dart:6` defines `sparkle-crdt-v1` minimal CmRDT protocol, no generated schema churn. |
| 2 | KnowledgeMastery / TaskState / ChatMessage 三类对象真实 CRDT 操作 | ✅ | `offline_crdt_document.dart:136`, `offline_crdt_document.dart:151`, `offline_crdt_document.dart:187` derive mastery PN-style deltas, task-state lattice, and chat OR-set. |
| 3 | 双向 ACK，ACK 后从 outbox 删除 | ✅ | `mobile/lib/core/offline/sync_engine.dart:220` deletes ACKed CRDT outbox rows; `sync_engine.dart:289` sends request id and waits for CRDT ACK. |
| 4 | 冲突解决不再 last-write-wins | ✅ | `offline_crdt_document.dart:108` idempotently unions operations; `offline_crdt_document.dart:129` merges documents by operation set, not timestamps. |
| 5 | 离线到在线自动重放未 ACK 操作 | ✅ | Existing outbox/retry loop remains; CRDT items stay pending/waitingAck until ACK and are requeued by TTL path in `sync_engine.dart:422`. |
| 6 | 多端并发编辑可预期 | ✅ | `mobile/test/core/offline/offline_crdt_document_test.dart:8`, `:42`, `:68` cover concurrent mastery, task, and chat merges. |
| 7 | 网络抖动、ACK 丢失、并发编辑、长时间离线集成测 | ⚠️ | Added ACK deletion test in `mobile/test/core/offline/sync_engine_crdt_ack_test.dart:48`, but Flutter compile is currently blocked by unrelated non-FV11 errors. Existing waitingAck TTL test still covers ACK timeout requeue in `mobile/test/unit/sync_engine_test.dart`. |
| 8 | 1000 操作 < 200ms 合并 | ✅ | `mobile/test/core/offline/offline_crdt_document_test.dart:132` asserts 1000 accumulated operations merge under 200ms. |

## 2. 文件变更清单

```
mobile/lib/core/offline/crdt_sync_manager.dart        | 216 ++++++++++++++++++++++---
mobile/lib/core/offline/offline_crdt_document.dart    | new minimal CRDT document/protocol
mobile/lib/core/offline/offline_providers.dart        |  10 ++
mobile/lib/core/offline/sync_engine.dart              |  88 +++++++---
mobile/lib/core/offline/sync_queue.dart               | 127 ++++++++++-----
mobile/test/core/offline/offline_crdt_document_test.dart | new CRDT merge/perf tests
mobile/test/core/offline/sync_engine_crdt_ack_test.dart  | new CRDT ACK outbox test
```

## 3. 测试证据

### 单测
```
cd mobile && flutter test test/core/offline/offline_crdt_document_test.dart
00:00 +5: All tests passed!
```

### 集成测
```
cd mobile && flutter test test/core/offline/sync_engine_crdt_ack_test.dart
Failed to load ... unrelated compile errors:
- calendar_provider.dart: TaskStatus.paused not handled
- plan_context_summary.dart: TaskStatus.paused not handled
- plan_detail_screen.dart: TaskStatus.paused not handled
- openclaw_automation_panel.dart / openclaw_node_management_panel.dart: const DS.textOnPrimary errors
```

### Lint / 类型 / Guard
```
cd mobile && dart analyze \
  lib/core/offline/offline_crdt_document.dart \
  lib/core/offline/crdt_sync_manager.dart \
  lib/core/offline/sync_engine.dart \
  lib/core/offline/sync_queue.dart \
  lib/core/offline/offline_providers.dart \
  test/core/offline/offline_crdt_document_test.dart \
  test/core/offline/sync_engine_crdt_ack_test.dart

Exit code: 0
Only pre-existing sync_engine.dart info-level style lints remained.
```

## 4. 用户视角变化

> 在离线学习、任务执行或聊天期间，用户现在可以积累本地操作；恢复网络后，只有服务器 ACK 的 CRDT delta 才会从 outbox 删除，未 ACK 的操作会继续重放。

具体场景：
- 之前：两个设备同时改同一学习掌握度或任务状态时，移动端依赖 last-write/max-wins 类策略，CRDT 发送也不等 ACK。
- 之后：移动端保存可合并的操作 delta，KnowledgeMastery / TaskState / ChatMessage 都有确定性合并语义，CRDT outbox 使用 requestId 等待后端 ACK。

## 5. 与其他卡片的协调

- 仅修改 `mobile/lib/core/offline/` 和 `mobile/test/core/offline/`，符合 FV-11 文件域。
- 当前工作树存在大量其他 FV 卡片的未提交改动和进度文件，未触碰或回滚。
- 后端协议期望：WebSocket `crdt_update` 需返回 `ack_crdt_update` / `crdt_ack` / `ack_crdt`，payload 或顶层包含 `requestId`/`request_id`；错误返回 `error_crdt_update` / `crdt_error`。

## 6. 已知限制 / 后续

- `sync_engine_crdt_ack_test.dart` 无法在当前 worktree 编译，原因是非 FV-11 文件的 Flutter 编译错误；这些应由对应 FV 卡片或 Architect 收尾修复后重跑。
- 后端 Yjs bridge 未在本卡直接修改；需要 Architect 确认后端将 `sparkle-crdt-v1.operations` 转换/合并入 YDoc 并按上述 ACK contract 回包。
- Legacy scalar server update path仍存在于 `sync_queue.handleServerUpdate`，用于兼容旧服务端推送；长期应由后端 CRDT snapshot/delta 替换。

## 7. 验收命令一键回放

```bash
cd mobile
flutter test test/core/offline/offline_crdt_document_test.dart
dart analyze lib/core/offline/offline_crdt_document.dart lib/core/offline/crdt_sync_manager.dart lib/core/offline/sync_engine.dart lib/core/offline/sync_queue.dart lib/core/offline/offline_providers.dart test/core/offline/offline_crdt_document_test.dart test/core/offline/sync_engine_crdt_ack_test.dart
flutter test test/core/offline/sync_engine_crdt_ack_test.dart
```
