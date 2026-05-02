# FV-17 · 资料生命周期管理报告 · 2026-05-02

Branch: `codex/FV-17-source-lifecycle`

## 1. 5/5 标准达成情况

| # | 标准 | 状态 | 证据 |
|---|------|------|------|
| 1 | 新建 source lifecycle 服务 | Done | `backend/app/services/source_lifecycle.py:52` defines archive, restore, revoke, goal-close orphan cleanup, delete/erasure, archive reminders, and retrieval eligibility. |
| 2 | SourceAsset lifecycle 状态 active / archived / revoked / orphaned | Done | `backend/app/models/file_storage.py:13` adds `SourceLifecycleStatus`; `backend/alembic/versions/fv17_20260502_source_lifecycle.py` persists status/timestamps and review metadata. |
| 3 | Goal close cleanup marks orphaned | Done | `backend/app/services/source_lifecycle.py:126` finds sources attached through closed goal plan tasks and marks them `orphaned`. |
| 4 | Permission revoke invalidates cache and sharing | Done | `backend/app/services/source_lifecycle.py:104` sets `revoked`, makes source private, soft-deletes active group links, and invalidates Redis/cache retrieval surfaces. |
| 5 | Archived sources excluded from RAG but restorable | Done | `rag_indexing_service.py`, `graph_rag.py`, `galaxy_service.py`, `retrieval_service.py`, `task_document_service.py`, and `source_tray_integration.py` all gate retrieval/context on active lifecycle. Restore re-indexes active chunks at `source_lifecycle.py:87`. |
| 6 | 90-day archive reminder | Done | `ARCHIVE_REVIEW_DAYS = 90` at `source_lifecycle.py:35`; `/api/v1/sources/archive-review-due` returns due archived sources. |
| 7 | Delete uses erasure/GDPR-safe path | Done | `source_lifecycle.py:166` invalidates retrieval, soft-deletes chunks/graph/group links, deletes encrypted object storage, stamps `erased_at`, and stores an erasure receipt. |
| 8 | API archive / restore / delete | Done | `backend/app/api/v1/sources.py:35` exposes archive, restore, revoke, delete, goal cleanup, and archive review endpoints. Gateway proxies `/api/v1/sources/*path`. |
| 9 | Frontend lifecycle UI | Done | Document library models/repository/provider/screen now parse lifecycle status, call source lifecycle endpoints, and show archive/restore/revoke controls with lifecycle badges. |
| 10 | Tests | Done / workspace blockers noted | Backend focused suite passes; gateway handler and Flutter analyzer are blocked by unrelated shared-worktree issues listed below. |

## 2. 文件变更清单

```
backend/alembic/versions/fv17_20260502_source_lifecycle.py
backend/app/api/v1/sources.py
backend/app/api/v1/router.py
backend/app/models/file_storage.py
backend/app/orchestration/graph_rag.py
backend/app/services/document_upload_storage.py
backend/app/services/galaxy/retrieval_service.py
backend/app/services/galaxy_service.py
backend/app/services/group_file_service.py
backend/app/services/rag_indexing_service.py
backend/app/services/source_lifecycle.py
backend/app/services/task_document_service.py
backend/app/signals/source_tray_integration.py
backend/app/signals/types.py
backend/gateway/internal/handler/file_handler.go
backend/gateway/internal/handler/proxy_routes.go
backend/gateway/internal/service/file_metadata.go
backend/tests/services/test_source_lifecycle.py
mobile/lib/core/network/api_endpoints.dart
mobile/lib/features/documents/data/models/document_library_models.dart
mobile/lib/features/documents/data/repositories/document_library_repository.dart
mobile/lib/features/documents/presentation/providers/document_library_provider.dart
mobile/lib/features/documents/presentation/screens/document_library_screen.dart
```

## 3. 测试证据

### Backend

```
cd backend
.venv/bin/python -m py_compile app/models/file_storage.py app/services/document_upload_storage.py app/services/source_lifecycle.py app/api/v1/sources.py app/api/v1/router.py app/services/rag_indexing_service.py app/orchestration/graph_rag.py app/services/galaxy/retrieval_service.py app/services/galaxy_service.py app/services/task_document_service.py app/services/group_file_service.py app/signals/types.py app/signals/source_tray_integration.py tests/services/test_source_lifecycle.py
# PASS

.venv/bin/ruff check app/models/file_storage.py app/services/document_upload_storage.py app/services/source_lifecycle.py app/api/v1/sources.py app/services/rag_indexing_service.py app/orchestration/graph_rag.py app/services/galaxy/retrieval_service.py app/services/galaxy_service.py app/services/task_document_service.py app/services/group_file_service.py app/signals/types.py app/signals/source_tray_integration.py tests/services/test_source_lifecycle.py
# All checks passed!

.venv/bin/python -m pytest tests/services/test_source_lifecycle.py tests/services/test_rag_indexing_service.py tests/services/test_galaxy_node_sources.py tests/test_api/test_task_document_api.py
# 12 passed in 3.75s
```

### Gateway

```
cd backend/gateway
go test ./internal/service
# ok github.com/sparkle/gateway/internal/service (cached)

go test ./internal/service ./internal/handler
# BLOCKED: unrelated internal/middleware/network_resilience.go imports missing module logur.dev/logur.
```

Earlier in the shared worktree, before switching back onto the FV17 branch, `go test ./internal/service ./internal/handler` passed. The current branch state has unrelated middleware changes that block handler package setup.

### Mobile

```
cd mobile
dart format lib/core/network/api_endpoints.dart lib/features/documents/data/models/document_library_models.dart lib/features/documents/data/repositories/document_library_repository.dart lib/features/documents/presentation/providers/document_library_provider.dart lib/features/documents/presentation/screens/document_library_screen.dart
# PASS

flutter analyze lib/core/network/api_endpoints.dart lib/features/documents/data/models/document_library_models.dart lib/features/documents/data/repositories/document_library_repository.dart lib/features/documents/presentation/providers/document_library_provider.dart lib/features/documents/presentation/screens/document_library_screen.dart
# 37 info-level existing style/lint issues; no errors or warnings.
```

### Workspace Guard

```
git diff --check
# PASS
```

## 4. 用户视角变化

用户现在可以在资料库里归档资料、恢复资料、撤回资料权限或删除资料。归档资料不会再进入 RAG/知识星图/任务上下文，但保留恢复路径；撤回会移除共享与检索缓存；删除会走软删除、检索清理和对象存储擦除收据。

具体场景：
- 之前：资料上传后缺少统一生命周期，旧资料或撤权资料仍可能被检索链路看到。
- 之后：资料状态成为检索入口的统一门禁，RAG、source tray、Galaxy、任务资料和群组资料列表默认只使用 active sources。

## 5. 与其他卡片的协调

- 与 CXP-21 / documents source tray：`SourceAsset` 增加 `lifecycle_status`，source tray 规划会记录 lifecycle skip reason。
- 与 Gateway：`stored_files` responses include `lifecycle_status` and `archive_review_due_at`; Python source APIs are proxied under `/api/v1/sources`.
- 与 Architect：迁移 revision 当前接在 `wp18_20260502` 后；最终整合时需要确认所有 FV migrations 的线性顺序或 merge revision。
- 与 Mobile：当前文案直接使用中文字符串；后续 i18n pass 可把 archive/restore/revoke snackbars and dialogs 移入 ARB。

## 6. 已知限制 / 后续

- `go test ./internal/handler` 当前被 unrelated `logur.dev/logur` missing module 阻塞。
- `flutter analyze` 在这些已存在的大文件中有 info-level style issues，未做大范围自动清理以避免扩大共享 worktree churn。
- Archive review endpoint returns due archived sources for the current user; actual notification/reminder scheduling can be wired into the notification center in a later integration task.

## 7. 验收命令一键回放

```bash
cd backend
.venv/bin/python -m py_compile app/models/file_storage.py app/services/document_upload_storage.py app/services/source_lifecycle.py app/api/v1/sources.py app/api/v1/router.py app/services/rag_indexing_service.py app/orchestration/graph_rag.py app/services/galaxy/retrieval_service.py app/services/galaxy_service.py app/services/task_document_service.py app/services/group_file_service.py app/signals/types.py app/signals/source_tray_integration.py tests/services/test_source_lifecycle.py
.venv/bin/ruff check app/models/file_storage.py app/services/document_upload_storage.py app/services/source_lifecycle.py app/api/v1/sources.py app/services/rag_indexing_service.py app/orchestration/graph_rag.py app/services/galaxy/retrieval_service.py app/services/galaxy_service.py app/services/task_document_service.py app/services/group_file_service.py app/signals/types.py app/signals/source_tray_integration.py tests/services/test_source_lifecycle.py
.venv/bin/python -m pytest tests/services/test_source_lifecycle.py tests/services/test_rag_indexing_service.py tests/services/test_galaxy_node_sources.py tests/test_api/test_task_document_api.py

cd ../backend/gateway
go test ./internal/service
go test ./internal/service ./internal/handler

cd ../../mobile
dart format lib/core/network/api_endpoints.dart lib/features/documents/data/models/document_library_models.dart lib/features/documents/data/repositories/document_library_repository.dart lib/features/documents/presentation/providers/document_library_provider.dart lib/features/documents/presentation/screens/document_library_screen.dart
flutter analyze lib/core/network/api_endpoints.dart lib/features/documents/data/models/document_library_models.dart lib/features/documents/data/repositories/document_library_repository.dart lib/features/documents/presentation/providers/document_library_provider.dart lib/features/documents/presentation/screens/document_library_screen.dart

cd ..
git diff --check
```
