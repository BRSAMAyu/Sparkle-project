# GALAXY-KW — SearchNodes tags 恒空修复（收工报告）

- Worker：C 纵队 wt174（基线 `2b2bb68c`）
- 卡：SearchNodes 结果 `tags` 恒空 → 移动端搜索结果永远没有关键词标签
- 交付：`v3-output/GALAXY-KW/REPORT.md`（本文）+ `changes.patch`（4 文件，+113/−5）

---

## ① 解法裁决 + REST/gRPC 对齐结论

### 裁决：投影层单点供给（NodeBase.keywords），否决批量 map

债根因不是查询缺失，而是**投影丢失**：retrieval 层 `semantic_search_ranked_nodes`
（`backend/app/services/galaxy/retrieval_service.py:848`）select 的是完整
`KnowledgeNode` 实体，`keywords` 是普通 JSONB 列、随实体已在内存
（`app/models/galaxy.py:135`：`keywords = Column(JSONBCompat, default=list, nullable=True)`）。
丢失发生在 `_format_search_result`（retrieval_service.py:991）→
`NodeBase.from_model(node)`：NodeBase 无 keywords 字段，列在此被丢弃。
gRPC 侧 `tags=r.node.keywords if hasattr(r.node,'keywords') ...` 作用在这个投影上，
hasattr 恒 False → tags 恒 `[]`。

两案对比：

| | 批量 map（handler 内再查一次） | 投影供给（选定） |
|---|---|---|
| DB 开销 | 每次搜索多发 1 次批量查询，**查回本已在内存的数据** | **零额外查询** |
| 修复面 | 仅 gRPC | REST + gRPC 单点同源 |
| 先例一致性 | 照 mastery_map | 照 `_build_auto_tags`（本就从同一 ORM 节点消费 keywords） |

选定投影供给：`NodeBase` 增加字段 + `from_model` 填充（schema 唯一构造路径就是
`from_model`，全仓无 `NodeBase(` 直接构造、无 `NodeBase.model_validate` 调用点，
爆炸半径已核实最小）。

### REST/gRPC 对齐结论（调研确认）

- **REST 面原本不是空、但同样没有 keywords**：`/api/v1/galaxy/search`
  （`app/api/v1/galaxy.py:742`）→ `GalaxyService.semantic_search`
  （`galaxy_service.py:2500`）→ 同一 `_format_search_result`。REST 的
  `node.tags` 走 `NodeWithStatus._build_auto_tags`（schemas/galaxy.py:598）——
  keywords 优先的自动标签（keywords + name/desc 分词兜底 + sector/seed/core 修饰）。
- **修复后双面同源**：REST `SearchResultItem.node` 新增 `keywords` 字段
  （additive，默认 `[]`，向后兼容）；gRPC `tags` = 投影 keywords，与 REST
  `node.keywords` 逐字同源。语义差异如实声明：REST `tags` 仍是 auto-tags
  （契约不变、未动），gRPC `tags` 按 P1-5/6 注释既有意图取纯 keywords。
- **顺带核实、不在本次范围**：GetUserGalaxy 图面（galaxy_grpc_service.py:374）
  keywords 恒缺时落到 `getattr(node,'tags')` auto-tags 兜底，不空、无 bug；
  GetNodeDetail（:494）查 ORM 实体，keywords 真实。两处行为均未改动。

## ② 实现清单

1. `backend/app/schemas/galaxy.py`
   - `NodeBase` 新增 `keywords: list[str] = Field(default_factory=list)`；
   - `from_model` 填充 `keywords=[str(k) for k in (node.keywords or [])]`
     （`str()` 与 `_build_auto_tags.add_tag` 同款防御，脏元素不抛 ValidationError；
     `or []` 兜住 nullable=True 的 NULL 行）。
2. `backend/app/services/galaxy_grpc_service.py`（SearchNodes，:560 附近）
   - 死分支 `tags=...hasattr...` → `tags=list(r.node.keywords)`，附 GALAXY-KW 注释；
   - 空 keywords 节点仍 `[]`（诚实空，不造假）。
3. 测试（4 新增 + 文件头契约注释更新）：
   - `backend/tests/unit/test_galaxy_grpc_search_recommended_user_status.py`
     - `test_search_nodes_tags_carry_node_keywords`：有 keywords 命中搜索 →
       proto tags 非空且逐项相等（旧代码下此断言必红——hasattr 恒 False）；
     - `test_search_nodes_empty_keywords_serve_honest_empty_tags`：空 keywords → tags `[]`；
     - docstring 与旧注释中「NodeBase 无 keywords」的表述同步更新（source_type 部分保留）。
   - `backend/tests/services/galaxy/test_retrieval_service.py`
     - `test_node_base_from_model_projects_keywords` / `..._null_keywords_stay_empty`：
       投影层契约钉（REST 面同路径 `_format_search_result` 复用 from_model）。

## ③ 冲突面声明

改动文件全集（`git status`）：上述 4 个文件，全部位于 **galaxy 检索投影/搜索面**。

- **wt170（achievement_engine + Alembic + photon 写侧）**：零重叠——我不动
  achievement_engine、无 Alembic 迁移（纯 schema 投影层，无 DB 变更）、不碰 photon。
- **wt172（llm_router / settings / celery 路由）**：零重叠——无路由、无配置、无 celery。
- **wt173（纯研究零代码）**：零重叠——其无代码交付。
- `backend/app/gen/` 为 gitignored，已按 wt171 先例从主仓拷贝补齐用于本地测试，
  **不进 patch**。

## ④ 诚实申报

1. **REST `tags` 语义未统一**：gRPC `tags` 现在是纯 keywords；REST `tags` 仍是
   auto-tags（keywords 优先 + 兜底修饰）。移动端若在两面间比对 tags 文案会有差异。
   未擅自统一是刻意的：改 REST tags 契约超出本卡（"回归对比法零新增"），
   如需统一建议另开卡（候选：gRPC tags 改用 `r.node.tags` auto-tags，与图面 :374 先例一致）。
2. **NodeWithStatus（图面/推荐面）keywords 保持缺省 `[]`**：`from_models` 不填充，
   图面 ：374 行为完全不变（仍走 auto-tags 兜底）。若未来图面也要真 keywords，
   需在 `from_models` 显式填充——本卡未做，避免扩战。
3. **`semantic_search` 内既有 per-node `get_user_node_status` N+1**
   （galaxy_service.py:2514，REST/gRPC 共用）是存量问题，本卡不动（mastery_map
   批查在 handler 侧已有先例，但那是 gRPC 附加通道，不是同一处）。
4. **无 REST `/search` 端到端测试**：REST 面覆盖靠投影层契约钉（同一 from_model 路径）；
   未新增 REST API 级测试（tests/api/ 下无 /search 先例 fixture，从零搭超出本卡）。
5. lint：4 文件在 HEAD 即有 black 漂移与 2 处 ruff 既有告警（UP017/I001），
   本改动**零新增** lint 债（对比法核实，见下）。

## ⑤ 收工核查

- 测试（`SECRET_KEY=test DATABASE_URL="sqlite+aiosqlite:///:memory:" python3.11 -m pytest`，
  一次一个文件）：
  - 基线（改前）：search_recommended_user_status 4 ✓ ｜ retrieval_service 24 ✓ ｜
    knowledge_service_semantic_search 1 ✓ ｜ vector_search 2 ✓
  - 改后：search_recommended_user_status **6** ✓（+2）｜ retrieval_service **26** ✓（+2）｜
    关联面回归 test_galaxy_grpc_cached_graph 3 ✓、test_galaxy_grpc_user_status 2 ✓、
    test_f821_undefined_name_bugfix 8 ✓、test_retrieval_cache+mastery_evidence 34 ✓、
    test_stats_service+evidence_pack_sse 15 ✓ —— **合计 94 通过、0 失败**
- 纪律：无 commit / 无 push（`git status` 仅 4 个 modified + v3-output untracked）；
  零凭据；主仓只读；DB 未触碰（无需 SELECT，形状全部从代码核实）；
  lint 对比法：当前 2 错 = HEAD 2 错（UP017@grpc_service:46、I001@test 导入块），零新增。
- 清理：/tmp 探针目录（kw-black-check）已删；无模拟器/无长驻进程/无构建产物。
