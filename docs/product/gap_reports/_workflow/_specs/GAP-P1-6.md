# GAP-P1-6: CRDT 冲突解决 — Implementation Spec

> **Mode**: spec→you | **Level**: L3 | **Effort**: M (3-5 days)
> **Source**: 11 号报告 — APP-005: CRDT for Graph Mastery
> **Status**: 📋 Spec ready for user implementation

---

## 1. 目标 (Objectives)

为 Sparkle 的 CRDT 系统补全冲突解决能力：集成现有 ConflictResolver 到同步管线、添加用户仲裁 UI、补充测试。

### 核心目标
1. 将 `ConflictResolver` 的三级策略（revision → LWW → mastery）接入 `CRDTSyncManager` 同步循环
2. 为并发编辑同一字段的场景增加 field-level merge（当前只有 union-of-operations）
3. Flutter 端展示冲突并允许用户裁决
4. 补充全面的 CRDT 单元/集成测试

---

## 2. 现状评估 (Current State Assessment)

### 已实现（比 11 号报告认知的更完整）

| 能力 | 文件 | 状态 |
|------|------|------|
| Lamport 时钟 | `offline_crdt_document.dart` L15, L106 | ✅ 完整 |
| Vector 时钟 | `offline_crdt_document.dart` L60, L92-93, L104 | ✅ 完整 |
| Operation-based CRDT | `offline_crdt_document.dart` L8-53 | ✅ 完整 |
| apply/applyAll/merged | `offline_crdt_document.dart` L108-134 | ✅ 完整 |
| 知识掌握度 CRDT | `offline_crdt_document.dart` L136-149 | ✅ 完整 |
| 任务状态 CRDT | `offline_crdt_document.dart` L151-185 | ✅ 完整 |
| 聊天消息 CRDT | `offline_crdt_document.dart` L187-222 | ✅ 完整 |
| 三级冲突策略 | `conflict_resolver.dart` L36-65 | ✅ 完整 |
| Isar 持久化 | `crdt_sync_manager.dart` L221-256 | ✅ 完整 |
| 同步引擎集成 | `crdt_sync_manager.dart` L238-256 | ✅ 完整 |
| ACK 匹配 | `sync_engine.dart` + `local_database.dart` | ✅ 完整 |

### 实际缺口

| # | 缺口 | 严重程度 | 描述 |
|---|------|---------|------|
| G1 | **ConflictResolver 未集成** | 🔴 High | `CRDTSyncManager.resolveConflict()` (L171-176) 直接调用 `applyUpdate(remoteUpdate)`，未检查冲突 |
| G2 | **无 field-level merge** | 🟡 Medium | `OfflineCrdtDocument.merged()` 是纯 union。两个设备并发改同一 mastery delta 会产生 double-apply |
| G3 | **无冲突裁决 UI** | 🟡 Medium | `SyncStatus.conflict` 枚举值存在但无 UI 消费 |
| G4 | **CRDT 测试极少** | 🔴 High | 11 号报告确认 "currently minimal" |

---

## 3. 文件清单 (File Inventory)

### 新建文件

| 文件 | 用途 |
|------|------|
| `mobile/lib/core/offline/field_level_merge.dart` | Field-level merge 策略（mastery/delta, task/status, chat/content） |
| `mobile/lib/features/sync/presentation/screens/conflict_resolution_screen.dart` | 冲突裁决 UI |
| `mobile/lib/features/sync/presentation/widgets/conflict_diff_card.dart` | 冲突差异展示卡片 |
| `mobile/lib/features/sync/presentation/providers/conflict_resolution_provider.dart` | 冲突状态 Riverpod provider |
| `mobile/test/core/offline/crdt_document_test.dart` | OfflineCrdtDocument 单元测试 |
| `mobile/test/core/offline/crdt_sync_manager_test.dart` | CRDTSyncManager 单元测试 |
| `mobile/test/core/offline/conflict_resolver_test.dart` | ConflictResolver 单元测试 |
| `mobile/test/core/offline/field_level_merge_test.dart` | Field-level merge 单元测试 |

### 修改文件

| 文件 | 变更 |
|------|------|
| `mobile/lib/core/offline/crdt_sync_manager.dart` | `resolveConflict()` 集成 ConflictResolver；导出冲突供 UI 消费 |
| `mobile/lib/core/offline/conflict_resolver.dart` | 新增 `ConflictRecord` 模型和 `detectConflicts()` 方法 |
| `mobile/lib/core/offline/offline_crdt_document.dart` | `merged()` 增加 field-level merge 调用 |
| `mobile/lib/core/offline/local_database.dart` | 确认 `SyncStatus.conflict` 枚举完整 |

---

## 4. 实现步骤 (Implementation Steps)

### Phase 1: Field-Level Merge Engine (1 day)

**Step 1.1**: 创建 `mobile/lib/core/offline/field_level_merge.dart`

```dart
/// Field-level merge strategies for concurrent edits of the same object.
///
/// Current CRDT merge is union-of-operations — correct for append-only data
/// (chat), but insufficient for state-based data (mastery, task status) where
/// two devices can concurrently issue operations targeting the same field.
class FieldLevelMerge {
  /// Merge two mastery deltas for the same node.
  /// Returns the single delta to apply (= sum clamped to [-100, 100] range).
  static int mergeMasteryDelta(int localDelta, int remoteDelta) {
    return (localDelta + remoteDelta).clamp(-100, 100);
  }

  /// Merge two task status transitions. Highest rank wins.
  /// Rank order: pending(0) < in_progress(1) < paused(2) < blocked(3) < failed(4) < completed(5)
  static String mergeTaskStatus(String local, String remote) {
    const rank = {
      'pending': 0, 'todo': 0,
      'in_progress': 1, 'active': 1,
      'paused': 2,
      'blocked': 3,
      'failed': 4,
      'completed': 5, 'done': 5,
    };
    return (rank[local] ?? 0) >= (rank[remote] ?? 0) ? local : remote;
  }

  /// Merge two chat message content edits. LWW by lamport timestamp.
  static Map<String, dynamic> mergeChatContent(
    OfflineCrdtOperation local,
    OfflineCrdtOperation remote,
  ) {
    return local.lamport >= remote.lamport ? local.value : remote.value;
  }

  /// Detect and resolve field-level conflicts for same objectId + field.
  /// Returns resolved operations (duplicates collapsed into single ops).
  static List<OfflineCrdtOperation> resolveConflicts(
    List<OfflineCrdtOperation> localOps,
    List<OfflineCrdtOperation> remoteOps,
  ) {
    // Group by (objectType, objectId, opType) key
    // For mastery_delta: sum deltas
    // For task_status: highest rank wins
    // For chat_add: keep both (append-only)
    // For chat_delete: tombstone wins over chat_add
    final merged = <String, OfflineCrdtOperation>{};
    final allOps = [...localOps, ...remoteOps];

    for (final op in allOps) {
      final key = '${op.objectType}:${op.objectId}:${op.opType}';
      if (op.opType == 'mastery_delta') {
        final existing = merged[key];
        if (existing != null) {
          final sumDelta = _asInt(existing.value['delta']) + _asInt(op.value['delta']);
          merged[key] = OfflineCrdtOperation(
            opId: op.opId, // keep latest
            actorId: op.actorId,
            objectType: op.objectType,
            objectId: op.objectId,
            opType: op.opType,
            lamport: op.lamport,
            createdAt: op.createdAt,
            value: {'delta': sumDelta.clamp(-100, 100)},
          );
        } else {
          merged[key] = op;
        }
      } else if (op.opType == 'task_status') {
        final existing = merged[key];
        if (existing != null) {
          merged[key] = op.lamport >= existing.lamport ? op : existing;
        } else {
          merged[key] = op;
        }
      } else {
        // chat_add, chat_delete: keep all (union)
        merged['${key}:${op.opId}'] = op;
      }
    }
    return merged.values.toList();
  }
}
```

**Step 1.2**: 修改 `OfflineCrdtDocument.merged()` 调用 `FieldLevelMerge.resolveConflicts()`:

```dart
// In offline_crdt_document.dart, replace merged():
OfflineCrdtDocument merged(OfflineCrdtDocument other) {
  final resolved = FieldLevelMerge.resolveConflicts(
    operations,
    other.operations,
  );
  final merged = OfflineCrdtDocument.empty()..applyAll(resolved);
  return merged;
}
```

### Phase 2: ConflictResolver Integration (0.5 day)

**Step 2.1**: 扩展 `conflict_resolver.dart`：

```dart
// Add to conflict_resolver.dart:

class ConflictRecord {
  ConflictRecord({
    required this.objectId,
    required this.objectType,
    required this.localValue,
    required this.remoteValue,
    required this.resolution,
  });
  final String objectId;
  final String objectType;
  final dynamic localValue;
  final dynamic remoteValue;
  final ConflictResolution resolution;
}

class ConflictResolver {
  // Existing resolveConflict() unchanged

  /// Detect all conflicts between local document and remote operations.
  /// Returns list of ConflictRecord for UI consumption.
  List<ConflictRecord> detectConflicts(
    OfflineCrdtDocument local,
    List<OfflineCrdtOperation> remoteOps,
  ) {
    final conflicts = <ConflictRecord>[];
    final localOps = local.operations;

    for (final remote in remoteOps) {
      // Check if any local op targets same (objectId, objectType, opType)
      for (final localOp in localOps) {
        if (localOp.objectId == remote.objectId &&
            localOp.objectType == remote.objectType &&
            localOp.opType == remote.opType &&
            localOp.lamport != remote.lamport) {
          // Same field, different lamport → conflict
          conflicts.add(ConflictRecord(
            objectId: remote.objectId,
            objectType: remote.objectType,
            localValue: localOp.value,
            remoteValue: remote.value,
            resolution: ConflictResolution._(
              ConflictResolutionType.merge,
              FieldLevelMerge.resolveConflicts([localOp], [remote]).first,
            ),
          ));
        }
      }
    }
    return conflicts;
  }
}
```

**Step 2.2**: 修改 `CRDTSyncManager.resolveConflict()` 集成 ConflictResolver：

```dart
final ConflictResolver _resolver = ConflictResolver();

Future<List<ConflictRecord>> resolveConflict(
  List<int> remoteUpdate, {
  String galaxyId = 'default',
}) async {
  final remoteOps = _tryDecodeOperations(remoteUpdate);
  if (remoteOps.isEmpty) {
    await applyUpdate(remoteUpdate, origin: 'remote', galaxyId: galaxyId);
    return [];
  }

  final document = await _loadDocument(galaxyId);

  // Detect field-level conflicts
  final conflicts = _resolver.detectConflicts(document, remoteOps);

  if (conflicts.isEmpty) {
    // No conflict: auto-merge
    document.applyAll(remoteOps);
    await _persistDocument(galaxyId: galaxyId, document: document, synced: true);
    return [];
  }

  // Auto-resolve mastery/task conflicts (deterministic merge)
  // Return chat conflicts for UI mediation
  final chatConflicts = conflicts
      .where((c) => c.objectType == 'chat_message')
      .toList();

  final nonChatOps = remoteOps
      .where((op) => op.objectType != 'chat_message')
      .toList();
  document.applyAll(FieldLevelMerge.resolveConflicts(
    document.operations,
    nonChatOps,
  ));
  await _persistDocument(galaxyId: galaxyId, document: document, synced: false);

  return chatConflicts;
}
```

### Phase 3: Conflict Resolution UI (1 day)

**Step 3.1**: 创建 `conflict_resolution_provider.dart`：

```dart
/// Riverpod provider exposing pending CRDT conflicts for UI consumption.
///
/// Consumed by conflict_resolution_screen.dart and a badge on settings/home.
final pendingConflictsProvider = StateNotifierProvider<PendingConflictsNotifier, List<ConflictRecord>>((ref) {
  return PendingConflictsNotifier();
});

class PendingConflictsNotifier extends StateNotifier<List<ConflictRecord>> {
  PendingConflictsNotifier() : super([]);

  void addConflicts(List<ConflictRecord> conflicts) {
    state = [...state, ...conflicts];
  }

  void resolveConflict(ConflictRecord record, {required bool useLocal}) {
    state = state.where((c) => c.objectId != record.objectId).toList();
    // useLocal: discard remote, keep local. Otherwise: apply merged.
  }

  void clearAll() => state = [];
}
```

**Step 3.2**: 创建 `conflict_diff_card.dart` — 展示单个冲突的差异卡片：
- 对象类型图标（知识节点/任务/消息）
- 本地值 vs 远程值 对比
- "保留本地" / "接受远程" / "合并" 三个按钮（mastery/task 自动合并，仅 chat 显示按钮）

**Step 3.3**: 创建 `conflict_resolution_screen.dart` — 冲突列表页：
- AppBar: "Conflicts" / "冲突"
- ListView of `ConflictDiffCard` widgets
- 空状态: "No pending conflicts" / "暂无冲突"
- 全部接受远程 / 全部保留本地 批量操作

### Phase 4: Tests (1-1.5 days)

**Step 4.1**: `crdt_document_test.dart` (15+ tests)：
| Test | 描述 |
|------|------|
| `test_empty_document` | 空文档初始化 |
| `test_apply_single_operation` | 单个 op 应用后 vector clock 更新 |
| `test_apply_duplicate_op_id` | 重复 opId 被拒绝 |
| `test_applyAll_multiple_operations` | 批量应用 + lamport 排序 |
| `test_merge_two_documents` | 两个文档 merge 后 operation 完整 |
| `test_knowledge_mastery_aggregation` | mastery delta 累加正确 |
| `test_knowledge_mastery_clamped` | mastery 值限制在 [0, 100] |
| `test_task_state_highest_rank_wins` | 并发 task status 取最高 rank |
| `test_chat_messages_ordered` | 聊天消息按时间排序 |
| `test_tombstone_removes_message` | chat_delete 移除对应 chat_add |
| `test_vector_clock_monotonic` | vector clock 单调递增 |
| `test_serialization_roundtrip` | JSON 序列化往返不丢失数据 |
| `test_hash_deterministic` | 相同内容产生相同 hash |
| `test_field_level_mastery_delta_merge` | 并发 delta 正确合并 |
| `test_field_level_task_status_merge` | 并发 status 正确合并 |
| `test_field_level_chat_keep_both` | chat_add 保持双方消息 |

**Step 4.2**: `conflict_resolver_test.dart` (8+ tests)：
| Test | 描述 |
|------|------|
| `test_revision_priority` | 高 revision 胜出 |
| `test_lww_fallback` | 相同 revision 时 LWW 胜出 |
| `test_mastery_fallback` | revision + timestamp 相同时高 mastery 胜出 |
| `test_detect_conflicts_same_object` | 同一对象并发编辑被检测为冲突 |
| `test_detect_conflicts_different_objects` | 不同对象不产生冲突 |
| `test_detect_conflicts_no_conflict` | 无并发编辑时返回空列表 |

**Step 4.3**: `crdt_sync_manager_test.dart` (6+ tests)：
| Test | 描述 |
|------|------|
| `test_apply_knowledge_mastery_delta` | mastery delta 正确写入 document |
| `test_set_task_state` | task status 正确写入 |
| `test_append_chat_message` | chat message 正确 append |
| `test_resolve_conflict_auto_merge` | 非 chat 冲突自动合并 |
| `test_resolve_conflict_returns_chat_conflicts` | chat 冲突返回给 UI |
| `test_snapshot_persistence` | snapshot 正确读写 |

### Phase 5: 连接 SyncEngine 触发冲突检测 (0.5 day)

**Step 5.1**: 修改 `CRDTSyncManager` 添加 WebSocket 推送监听：
- 当 `SyncEngine` 收到远程更新时，调用 `resolveConflict()`
- 如有未解决的 chat 冲突，emit 到 `pendingConflictsProvider`
- 在主页面/设置页显示冲突徽章

---

## 5. 测试计划 (Test Plan)

### Unit Tests (30+ tests)
- `offline_crdt_document_test.dart` — 16 tests
- `field_level_merge_test.dart` — 6 tests
- `conflict_resolver_test.dart` — 8 tests
- `crdt_sync_manager_test.dart` — 6 tests

### Widget Tests (5 tests)
- `conflict_diff_card_test.dart` — 3 tests
- `conflict_resolution_screen_test.dart` — 2 tests

### Integration Test (2 tests)
- Full CRDT sync cycle: local edit → remote edit → conflict → resolve → sync
- Concurrent mastery delta from two devices

---

## 6. 验收标准 (Acceptance Criteria)

### Functional
- [ ] `FieldLevelMerge` 正确处理 mastery delta 并发累加
- [ ] `FieldLevelMerge` 正确处理 task status 并发（最高 rank 胜出）
- [ ] `ConflictResolver.detectConflicts()` 正确检测并发编辑
- [ ] `CRDTSyncManager.resolveConflict()` 自动合并非 chat 冲突
- [ ] `CRDTSyncManager.resolveConflict()` 返回 chat 冲突供 UI 裁决
- [ ] `ConflictDiffCard` 正确展示本地 vs 远程差异
- [ ] `ConflictResolutionScreen` 支持用户选择保留本地/接受远程
- [ ] 冲突解决后 `pendingConflictsProvider` 状态更新
- [ ] 无冲突时同步流程不受影响（零回归）

### Non-Functional
- [ ] Conflict detection < 50ms (典型 100-op document)
- [ ] Field-level merge < 10ms
- [ ] 无内存泄漏（provider dispose 正确）
- [ ] 所有现有 CRDT 行为不变（向后兼容）

### Quality Gates
- [ ] 所有 35+ tests 通过
- [ ] `flutter analyze` 无新增 warning
- [ ] 无硬编码 secrets/tokens
- [ ] i18n 双语覆盖新增 UI 文本 (`isChinese ? '中文' : 'English'`)

---

## 7. 设计决策 (Design Decisions)

| 决策 | 选择 | 理由 |
|------|------|------|
| Mastery delta merge | Sum both deltas | 两个设备各加 5 → 总共 +10；delta 累加语义正确 |
| Task status merge | Highest rank wins | completed > in_progress > pending，进度只进不退 |
| Chat message merge | Keep both (union) | 聊天是 append-only，双方消息都应保留 |
| Auto-merge vs user mediation | mastery/task 自动合并，chat 可选 UI 裁决 | 数据类冲突确定性强；对话类冲突需要用户判断 |
| 测试框架 | `flutter test` + `mockito` | 与现有 Flutter test 基础设施一致 |

---

## 8. 依赖与阻塞 (Dependencies)

- Phase 2 依赖 Phase 1（field-level merge engine）
- Phase 3（UI）可并行于 Phase 2
- Phase 4（tests）依赖 Phase 1-2
- Phase 5（SyncEngine 连接）依赖 Phase 2-3
- 无外部依赖阻塞

---

## 9. 开放问题 (Open Questions)

1. Conflict resolution UI 的触发时机：收到远程更新时立即弹窗 vs 在设置页显示徽章让用户主动查看？建议：徽章 + 设置页入口（非阻塞弹窗）。
2. 是否需要在 `LocalCRDTSnapshot` 中持久化未解决的冲突列表？建议：仅内存（`pendingConflictsProvider`），冲突在下次 sync 时重新检测。
3. 后端是否需要感知 CRDT conflict？当前设计是客户端独立解决，后端仅转发 operations。

---

*Spec generated 2026-05-06 by claude-B (GAP Closer Agent)*
