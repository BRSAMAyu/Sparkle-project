# Galaxy Audit Fixes WORKLOG — 2026-05-10

## 任务概述
根据 5 份 agent 报告 + 1 份汇总报告（共 98 个问题：6 P0 + 23 P1 + 40 P2 + 29 P3），按优先级依次修复。

---

## P0 问题修复记录 (6/6 DONE ✅)

### P0-1: SQL 注入 — keyword_search 用户输入直接拼入 ILIKE
- **文件**: `backend/app/services/galaxy/retrieval_service.py:589-594`
- **验证**: ✅ 确认存在
- **修复**: commit `41f2480c3` — escape LIKE wildcards + regex metacharacters in keyword_search
- **状态**: ✅ DONE

### P0-2: 掌握度重复更新 — spark_node + feedback_service 双写
- **文件**: `backend/app/services/galaxy/feedback_service.py`
- **验证**: ✅ 确认存在
- **修复**: commit `09fc7fae5` — skip _update_mastery_from_feedback for task_completed/study_session
- **状态**: ✅ DONE

### P0-3: Go RecordStudy 写入不存在的列
- **文件**: `backend/gateway/internal/service/galaxy_command.go:343-355`
- **验证**: ✅ 确认存在
- **修复**: commit `41f2480c3` — fix INSERT columns to match schema.sql (study_minutes, mastery_delta, initial_mastery)
- **状态**: ✅ DONE

### P0-4: Galaxy gRPC Client 无重连/重试
- **文件**: `backend/gateway/internal/galaxy/client.go:22-56`
- **验证**: ✅ 确认存在
- **修复**: commit `09fc7fae5` — add retry policy, remove WithBlock(), add reconnect(), add keepalive params
- **状态**: ✅ DONE

### P0-5: 协作星图并发安全 — module-level dict 无锁保护
- **文件**: `backend/app/services/galaxy_grpc_service.py:36-73`
- **验证**: ✅ 确认存在
- **修复**: commit `09fc7fae5` — add asyncio.Lock, replace datetime.utcnow() with datetime.now(timezone.utc)
- **状态**: ✅ DONE

### P0-6: gRPC GetNodeDetail 掌握度 × 100 溢出
- **文件**: `backend/app/services/galaxy_grpc_service.py:318`
- **验证**: ✅ 确认存在
- **修复**: commit `41f2480c3` — remove *100 multiplication, mastery_score already 0-100
- **状态**: ✅ DONE

---

## P1 问题修复记录 (已修复: P1-1, P1-2, P1-3, P1-5, P1-6, P1-7, P1-22, P1-23, P1-6)

### P1-1: galaxy_sync.go clamp (0,1) → (0,100)
- **文件**: `backend/gateway/internal/worker/galaxy_sync.go:375`
- **修复**: commit `35394246e` — clamp to (0,100), threshold 80.0
- **状态**: ✅ DONE

### P1-2: Perfectionist 成就永远无法触发
- **文件**: `backend/app/services/galaxy/stats_service.py:187-193`
- **修复**: commit `a4d3b2580` — change NODE_MASTERED to HIDDEN_TRIGGER with hidden_trigger_code="PERFECTIONIST"
- **状态**: ✅ DONE

### P1-3: LikePost 幽灵事件
- **文件**: `backend/gateway/internal/service/community_command.go:119-158`
- **验证**: 代码已有 RowsAffected() 检查，在原来代码中已正确实现
- **状态**: ✅ 无需修复（已确认正确）

### P1-5/6: `tags` → `keywords` 属性名修正
- **文件**: `galaxy_grpc_service.py:236, 320, 350`
- **修复**: commit `35394246e` — node.keywords instead of node.tags in GetUserGalaxy, GetNodeDetail, SearchNodes
- **状态**: ✅ DONE

### P1-6: Community GetFeed 无认证
- **文件**: `backend/gateway/internal/api/v1/community.go:31`
- **修复**: commit `d978969fb` — move GET /feed to protected group
- **状态**: ✅ DONE

### P1-7: SearchNodes mastery 硬编码 0
- **文件**: `galaxy_grpc_service.py:349`
- **修复**: commit `35394246e` — batch-query UserNodeStatus for all results
- **状态**: ✅ DONE

### P1-22: GetUserGalaxy mastery 取错属性
- **文件**: `galaxy_grpc_service.py:235`
- **修复**: commit `35394246e` — node.user_status.mastery_score instead of node.mastery
- **状态**: ✅ DONE

### P1-23: 文档导入节点无 embedding
- **文件**: `backend/app/services/galaxy_service.py:461-593`
- **修复**: commit `bb3e6b75a` — schedule background embedding via task_manager.spawn()
- **状态**: ✅ DONE

---

## 待修复 P1 问题 (剩余)

### P1-8: GetGalaxyStats avg_mastery 错误计算
- **文件**: `galaxy_grpc_service.py:478`
- **状态**: 待修复

### P1-9: _get_or_create_status 竞态条件
- **文件**: `stats_service.py:454-469`
- **状态**: 待修复

### P1-10: feedback_service 掌握度 int() 截断
- **文件**: `feedback_service.py:256`
- **状态**: 待修复

### P1-11: Community GetFeed 无认证 → 已修复 ✅

### P1-12: GalaxyRoutes force-unwrap 崩溃
- **文件**: `mobile/lib/features/galaxy/galaxy_routes.dart:50`
- **状态**: 待修复

### P1-13: GalaxyNodeModel.fromJson null ID 崩溃
- **文件**: `mobile/lib/shared/entities/galaxy_model.dart:193`
- **状态**: 待修复

### P1-14: Community CQRS handler 死代码
- **文件**: `community.go` + `setup.go`
- **状态**: 待决定（保留/删除）

### P1-15: NewGalaxyHandler 返回 nil → 空指针崩溃
- **文件**: `galaxy_handler.go:41-45` + `setup.go:284`
- **状态**: 待修复

### P1-16: SharedResourceCard 硬编码中英文字符串
- **文件**: `shared_resource_card.dart:29-223`
- **状态**: 待修复

### P1-17: CommunityInsight 每次重建重新请求 API
- **文件**: `node_detail_sheet.dart:1619`
- **状态**: 待修复

### P1-18: GroupKnowledgeBase _openFile 无错误处理
- **文件**: `group_knowledge_base_view.dart:121-132`
- **状态**: 待修复

### P1-19: Galaxy user_id 无 UUID 格式验证
- **文件**: `backend/app/api/v1/galaxy.py:182-200`
- **状态**: 待修复

### P1-20: spark_node 审计日志/事件静默吞错
- **文件**: `stats_service.py:81-128`
- **状态**: 待修复

### P1-21: Unbounded BFS DoS
- **文件**: `galaxy_grpc_service.py:364-427`
- **状态**: 待修复

---

## P2 问题修复记录
（待开始）

---

## 已完成 Commits

| Commit | 描述 |
|--------|------|
| `41f2480c3` | fix(P0): galaxy SQL injection, RecordStudy column names, GetNodeDetail mastery |
| `09fc7fae5` | fix(P0): galaxy client reconnect, collaborative sessions lock, mastery double-update |
| `35394246e` | fix(P1): galaxy_sync clamp 0-100, GetUserGalaxy mastery, SearchNodes, tags |
| `a4d3b2580` | fix(P1): spark_node Perfectionist achievement uses HIDDEN_TRIGGER |
| `d978969fb` | fix(P1): community GetFeed auth middleware, LikePost already checks RowsAffected |
| `bb3e6b75a` | fix(P1): schedule background embedding for document-imported nodes |

---

## 下一步

Phase 3 继续 P1 剩余项（P1-8 到 P1-21），然后 Phase 4 Flutter UI/UX，最后 P2/P3