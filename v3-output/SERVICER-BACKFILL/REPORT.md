# SERVICER-BACKFILL 收工报告

> 卡：GRAPH-GRPC-SHAPE 登记 follow-up —— SearchNodes / GetRecommendedNodes servicer 的 user_status 同模式补填
> Worker：wt152（基线 6f647323）｜日期：2026-09-23

## ① 消费面证据（mobile 读不读）

**读。结论：SearchNodes 必须补填；GetRecommendedNodes 补填（同模式一致性，当前无 mobile 消费方）。**

- **SearchNodes（`GET/POST /galaxy/search` → 网关 `SearchNodesGPRC`）**：
  - 网关路由：`backend/gateway/internal/handler/galaxy_handler.go:98-99`。
  - mobile 调用：`mobile/lib/features/galaxy/data/repositories/galaxy_repository.dart:171-190`（`GalaxyRepository.searchNodes`）与 `enhanced_galaxy_repository.dart:464-472`，POST `/galaxy/search` 后 `GalaxySearchResponse.fromJson`。
  - mobile 解析：`mobile/lib/shared/entities/galaxy_model.dart` `GalaxySearchResult.fromJson`（~561-591 行）**显式读 `json['user_status']` 并展平进 `GalaxyNodeModel`**；null 时静默默认 `mastery_score=0, is_unlocked=false`。`GalaxyNodeModel.fromJson` 另从 user_status 读共 10 个字段（is_unlocked/mastery_score/study_count/recent_error_count/review_urgency_score/is_review_recommended/review_urgency_reason/mastery_last_updated_at/days_since_mastery_update/first_unlock_at）。
  - 即：gRPC 分支出的 null 在 mobile 搜索结果上 = 全部节点锁定 + 掌握度归零的语义谎言。
- **GetRecommendedNodes（`GET /galaxy/predict` → 网关 `GetRecommendedGPRC`）**：
  - 网关路由：`galaxy_handler.go:106`。mobile **无消费方**（grep 全库无 `/galaxy/predict` 调用；mobile 用的是 `/galaxy/predict-next` → `galaxy_handler.go:107` `ProxyToBackend` 纯 REST 代理，单节点 NodeDetailResponse，不走本 servicer）。
  - 但该路由是活 API 面，网关出站已通过共享 mapper 携带 user_status（见下），引擎侧补一行即与 graph/search 同契约。照卡面要求同模式补填。
- **网关侧（零改动，已就绪）**：`galaxySearchRESTPayload` / `galaxyRecommendedRESTPayload` 均经 `galaxyNodeRESTPayload`（galaxy_handler.go:622-631）→ `galaxyUserStatusRESTPayload`（:649-669），proto 有值即透传为 REST user_status dict，nil → null。

## ② 改动清单

**proto：零改动。** `SearchNodesResponse.nodes` 与 `GetRecommendedNodesResponse.nodes` 均为 `repeated GalaxyNode`，`GalaxyNode.user_status = 6`（GalaxyNodeUserStatus）已由 wt149 落地（`proto/galaxy_service.proto:113`）；`git diff 6f647323 -- proto/` 为空。未跑 `buf breaking`（输入零变化，前提不成立即天然干净）；`make proto-gen` 重跑幂等（工作树仍只有本次两文件）。

引擎 `backend/app/services/galaxy_grpc_service.py`（三处）：

1. **SearchNodes**：节点构造追加 `user_status=self._node_user_status_pb(getattr(r, "user_status", None))`。数据源现成：`semantic_search` 内部已按结果 `retrieval.get_user_node_status` rehydrate 完整 `UserStatusInfo` 塞进 `SearchResultItem.user_status`（`galaxy_service.py:2500-2515` + `retrieval_service.py:991-1028`）——GRAPH-GRPC-SHAPE 报告里「只查 mastery 一列、填半截会造谎言」的分析已过时（当时 servicer 用的是更早的实现路径）。None → 缺省消息（REST null 镜像）。
2. **SearchNodes 阻塞缺陷修复（同块必修，见④）**：`node_type=r.node.source_type or "unknown"` → `node_type=getattr(r.node, "source_type", None) or "unknown"`。
3. **GetRecommendedNodes**：节点构造追加 `user_status=self._node_user_status_pb(getattr(predicted, "user_status", None))`。数据源：`predict_next_node` 返回 `NodeWithStatus.from_models(node, status)`，user_status 与 REST 面同源（`stats_service.py:396-464` + `schemas/galaxy.py:352-411`）。

新测试 `backend/tests/unit/test_galaxy_grpc_search_recommended_user_status.py`（4 用例，全部走生产形状）：

- search/recommended 各一对双向：**有填充**（HasField + mobile 消费 10 字段逐一断言，含 double 保真 25.5、两个 Timestamp）+ **null 镜像**（`not HasField`，绝不落全零块）。
- search 侧顺带钉住：`r.node` 是真实 `SearchResultItem/NodeBase`（无 source_type/keywords 属性）时不抛、node_type 降级 "unknown"；int32 `mastery` 批量回查通道照旧（fake 行 `(node_id, 88)` → `node.mastery == 88`）。

**交付物**：`v3-output/SERVICER-BACKFILL/REPORT.md` + `changes.patch`（修改文件标准头、新文件 `--- /dev/null` 头）。零凭据、零 gen 产物入库（gen 全 gitignored）。

## ③ 冲突面

- 本卡触碰：`backend/app/services/galaxy_grpc_service.py`（仅 SearchNodes/GetRecommendedNodes 两个方法块）+ 新测试文件。
- **与在途 wt144（events 域）：零交集**。events 域不涉 galaxy gRPC servicer 与 unit/galaxy_grpc 测试文件；本卡不触碰 events 任何文件。
- 与已合入基线 wt149（GRAPH-GRPC-SHAPE）：纯追加复用其 `_node_user_status_pb` 与 proto 消息，未改其任何行为（其测试 `test_galaxy_grpc_user_status.py` 2/2 照旧绿）。

## ④ 诚实申报

1. **超出卡面的最小修复**：SearchNodes 的 `r.node.source_type` 直接访问是**前置潜在缺陷**——生产形状下 `semantic_search` 返回的 node 是 `NodeBase`，**没有 `source_type` 属性**（直接探测实证：`AttributeError: 'NodeBase' object has no attribute 'source_type'`）。即补填前任何非空生产搜索都会 AttributeError → except → INTERNAL + 空响应，gRPC 搜索分支从未成功返回过（网关一直靠 REST fallback 兜底，这也解释了为何该缺陷未被打捞：F821 测试用 SimpleNamespace fake 绕开了 schema）。此缺陷在本次编辑的同一行块上、且不修则补填永不生效，故按最小改动修复为 getattr 降级 "unknown"（与 RecommendedNodes 既有写法一致）。**变异验证**：还原旧表达式跑新测试 → 红（`StatusCode.INTERNAL 'NodeBase' object has no attribute 'source_type'`），还原修复 → 绿。
2. **未修的同类观察（登记用，非本卡）**：SearchNodes 的 `tags` 通道读 `r.node.keywords`，NodeBase 只有 `tags`（hasattr 守卫兜住不抛），故 gRPC 分支 tags 恒为 `[]`，而 REST 面出 auto-tags；mobile `GalaxyNodeModel` 读 `tags` 键 → 搜索结果标签空。属数据完整性小缺（proto-only 超集键，gateway 注释已定性 harmless superset），留账不动。
3. **GetRecommendedNodes 现状**：mobile 今日不消费 `/galaxy/predict`；补填是契约一致性投资，活栈无即时行为收益。若主会话判定「无消费方即不改」，回滚 patch 中该 servicer 的一个字段即可，测试删除对应两用例。
4. **`buf lint` 报 2 条**：`proto/websocket.proto` 目录打包问题（multiple packages / package-directory mismatch）——**基线既有**，与本卡无关（proto 零改动），留账。
5. **内存纪律**：全程无 HEAVY（单进程 pytest/go test/代码生成）；收工时 swap free 542M（低于 HEAVY 启动门 1.2G，本卡未启动任何 HEAVY）、load 3.38。无模拟器/浏览器/Gradle 残留。
6. 测试环境：worktree 无 .env，全程 `DATABASE_URL="sqlite+aiosqlite:///:memory:" SECRET_KEY=test` + pytest 绝对路径；Go 侧 `CGO_ENABLED=0`。

## 回归证据（全绿）

| 套件 | 命令 | 结果 |
|---|---|---|
| 新增双向测试 | `pytest tests/unit/test_galaxy_grpc_search_recommended_user_status.py` | 4 passed |
| 引擎 galaxy grpc 域定向（新 4 + wt149 2 + COLDSTART 3 + F821 8） | 同上四文件合跑 | **17 passed** |
| 网关 Galaxy | `cd backend/gateway && CGO_ENABLED=0 go test ./internal/handler/ -run Galaxy -count=1` | ok |
| proto 幂等 | `PROTO_USE_DOCKER=0 make proto-gen` 重跑后 `git status` | 仅本卡两文件 |
| proto 未动 | `git diff 6f647323 -- proto/` | 空 |

## ⑤ 收工核查

- [x] 未 commit / 未 push（`git status`：1 modified + 1 untracked + v3-output 交付物）
- [x] 主仓零触碰；全部改动在 wt152 内
- [x] 临时产物已清：`/tmp/wt152_servicer_backup.py` 已删；无进程残留、无模拟器；gen 产物 gitignored 随 worktree 生命周期回收
- [x] 交付物登记：`v3-output/SERVICER-BACKFILL/`（REPORT.md + changes.patch）
- [x] 零凭据入文件
- [ ] 活栈验证（引擎 :50051 + 网关 :8080 联调）——按卡留主会话
