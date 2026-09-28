# V4-D06 一审 receipt（独立审查 wtD06R1）

- 审查人：wtD06R1（独立会话，未参与 D06 实现）
- 审查对象：`agent/v4/d06` @ `3f485262a630eb7073f7ebb20e3ca991df3b001f`（base=`f9729cc5`）
- 卡面：`Sparkle-project/v4/04_tasks/cards/V4-D06.md`；预登记挑战：`review_receipt.json` R1-R5
- 审查日期：2026-09-28
- 环境：wtD06 worktree / python 3.11.15（共享 venv）/ pytest 9.0.2 / `SECRET_KEY=ci-test-key DATABASE_URL=sqlite://` / AGE 无实例（mock 契约面）

## 总裁决：APPROVE（一审通过，无阻塞挑战）

卡面三条验收全部独立复验成立；19/60/178/236/77/21 六个批次复跑全绿；M1/M2/M3 三突变亲做全部变红后 sha256 恒等还原；棘轮（ruff/black/mypy）复核零新增。R1-R5 逐判见下，均不构成阻塞；衍生 3 项非阻塞挂账条件（§挂账）。

## 一、水位双源语义与降级可审计性（亲验）

**关系型水位**（`graph_index_watermark.py`）：`max(updated_at)+双表行数`（knowledge_nodes+node_relations），同事务可见未提交写，失败返回 None→unknown 不猜；行数进版即 E-05 delete-isolation 判例（删除非最新行仍翻版本，有专门测试钉住）。**AGE 覆盖水位**：仅 worker（XPENDING==0）与 `sync_all_to_age` 全量重建后经 `record_age_coverage` 推进；只收真实算得的水位串。**判定**：fresh 恒等才作答；stale/uncovered/unknown 全部落关系型。

**降级可审计性**（逐行核对）：`graph_search` → `self.last_graph_index`（state/mode/fallback_reason/relational_watermark/age_watermark/age_errors/relational_errors/relational_filled_entities/stale_guard_dropped/relational_result_count）→ `retrieve()` 第 2688 行并入 `metadata["graph_index"]`；`_record_fallback` 同步计 `GRAPH_INDEX_FALLBACK_TOTAL{reason}`（7 个 reason 标签与 metrics.py 注释一一对应）+ logger.warning。fresh 面 AGE 故障逐实体结构化收集（不再吞 warning）、关系型补答；守卫查询失败 fail-closed 弃 AGE 行；双读栅栏检出并发写弃 AGE 行。**无静默路径发现。**

## 二、复跑（独立执行，全部 exit 0）

| 批次 | 结果 |
|---|---|
| 新测试 `tests/unit/test_graph_index_freshness_fallback.py` | **19 passed**（6.42s） |
| graph 家族 6 文件 | **60 passed**（3.00s） |
| galaxy D04 基线 `tests/services/galaxy/` | **178 passed**（51.31s） |
| 终态合并批（19+39+178） | **236 passed**（57.24s） |
| retraction/worker/expansion/FF | **77 passed**（63.12s） |
| galaxy grpc + 图盾 | **21 passed**（44.86s） |

## 三、突变复现（亲做：改→红→还原）

| 突变 | 注入 | 结果 | 还原验证 |
|---|---|---|---|
| M1 stale 门旁路 | `if age == relational:` → `if True:` | **2 failed**（test_resolve_state_stale_on_mismatch + test_stale_age_rows_cannot_override_relational_delete） | sha256 `2def5853…` 恒等，git diff 空 |
| M2 守卫旁路 | `_guard_age_rows` kept 条件前置 `True or` | **1 failed**（test_soft_deleted_node_dropped_by_fresh_guard） | sha256 `b90315dd…` 恒等 |
| M3 积压规则旁路 | `if pending_count != 0:` → `if False:` | **1 failed**（test_worker_holds_watermark_while_backlog） | sha256 `926e8a4f…` 恒等 |

三处 sha256 与 run_manifest `changed_artifacts_sha256` 逐一吻合；还原后 `git status app/` 零改动。与实现方报告（2F/1F/1F）完全一致。

## 四、预登记 R1-R5 逐判（独立下判）

### R1 worker XPENDING 并发语义与回收路径 — PASS（保守方向正确，无假 fresh 路径）

亲读 `_consume`/`_recover_pending`/`_advance_age_watermark`。要点：
- XPENDING 是**组级**判定：任一 consumer 的未 ack 消息都会挡住推进——多 consumer 下不可能越权声称覆盖（保守正确）。
- XPENDING==0 ≠ 流排空（未投递尾消息不可见），但推进的是**本批消息自带水位**，对该版本是真实陈述；更新的写必然翻关系型 token → 读门判 stale。语义成立。
- 回收路径（XAUTOCLAIM，既有机制）批内全部成功且零积压才推进；失败消息留 PEL 不推进。D06 增量仅为水位采集/推进，XAUTOCLAIM 本身未动。
- 审查发现三处**保守方向**的边角（非阻塞，记录在案）：
  1. `_consume` 用 `covered_watermarks[-1]`（批内末条）而非最大值——并发入队下流 ID 序与水位序可逆（T2 先提交后入队），覆盖可能记到批内较旧水位；
  2. `record_age_coverage` 无单调守卫——后批更旧水位可覆盖先批较新水位（回退）；两者后果都是"多 stale 一段、下次消费自愈"，等值门下**不可能**因回退产生假 fresh；
  3. 写路径 XADD 在 commit 之前（`graph_knowledge_service.py` 入队→commit 顺序）：worker 理论上可在事务提交前消费并推进"幽灵水位"；若事务最终回滚，覆盖串成为永不匹配的幻影（保守 stale，自愈），且**幻影节点行会被 fresh 面存在性守卫丢弃**（守卫查的是关系型存在性，回滚写不在其中）——兜底成立。

### R2 等值水位 vs 单调 epoch — 边界实证成立，本卡 ACCEPT，挂硬ening 卡（非阻塞）

亲做同 `updated_at` 双写边界实测（sqlite，临时探针 3 用例，跑毕即删）：
- **同毫秒并发创建**：计数翻转区分（`r1→r2`），token 必翻——预登记"靠计数翻转"表述成立。
- **同毫秒原地更新（无行数变化）**：ORM 路径 `updated_at` onupdate 必打新墙钟，token 经时间戳翻转——该路径**碰撞不可复现**；真碰撞需真实提交落在覆盖水位的同一截断毫秒内（生产 ≤1ms 竞态）。
- **同毫秒删除+创建（计数复原）**：**碰撞实证复现**——token 恒等 → `resolve_state()==fresh`，而关系型内容已变（relation_type/strength 均改）。这是等值 token 的真实盲区。

后果评估：假 fresh 要求"删除+创建"与被覆盖写入同毫秒并发且计数恰复原——亚毫秒并发巧合，现实中概率可忽略；命中时 AGE 旧行可答**一轮**，下一不同毫秒写入即翻 stale 自愈。**注意面**：fresh 面守卫只查**节点**存在性/软删，不查**关系**行——此窗口内被删关系的 AGE 行是唯一无守卫复活面。已有 limitations #5 预登记。裁决：等值比较方向正确（假 fresh 仅限上述亚毫秒族），**本卡接受**；单调 epoch 或 µs 精度+计数的硬化建议立项单独小卡（见挂账 H-1），不阻塞 D06。

### R3 双读栅栏毫秒级窗口 vs「新资料立即」— PASS（口径满足）

栅栏把检出窗缩到"读前水位→AGE 查询→读后水位"一次 graph_search 内。剩余不可消除窗 = 写在读后重算**之后**提交——该写在任何单次读取的可见性之外，属线性一致性的基本语义而非陈旧缺陷；下一轮 token 不同 → stale → 关系型作答自愈。"新资料立即"口径按**关系型主真源**核：非 fresh 面关系型一跳是查询时点读（最即时面）；fresh 面窗口内新写至多缺答一轮。**删除面不受此窗影响**：守卫（节点存在性/软删）+ 栅栏 + stale 水位三重。栅栏重算失败放行（fail-open）为已注释的取舍，有守卫兜底、影响限一轮。可接受。

### R4 path-finder 未接门 — 裁决：单独卡收口（挂账 H-2），本卡不阻塞

亲验 `find_learning_path`（:2782）/`find_related_concepts`（:2831）仍直查 AGE，未过时效门；租户过滤保留。可达面：仅 `GraphKnowledgeService.get_learning_path/get_related_knowledge`（orphan-by-design 资产，graph_monitor 消费面 V3-FIX-341 已撤），不在 graph_search 主检索链。同属"AGE 旧数据"风险类但消费方少——与实现方挂账判断一致。**裁决：必须立项单独卡收口**（接同一 watermark 门或改走 graph_search 同型语义），在收口前这两个方法不得新增生产消费方。

### R5 写生产者空缺致常态 stale — 裁决：接受为设计意图，附条件（挂账 H-3）

`expansion_service` 等直写关系表不入队 → 覆盖水位停在旧值 → 门常判 stale → 常态关系型作答。按 DATA_AND_GRAPH §星图权威（关系型主真源、AGE 派生索引），这是**正确性无损**的结果：卡的验收恰是"AGE 不得压过关系型"，空缺使门恒保守。代价是经济性的（AGE 检索收益未兑现），非正确性洞。**裁决：接受为设计意图**；条件：任何后续卡声称"AGE 检索收益/GraphRAG 提效"前，必须先补齐写生产者入队或建立 sync_all_to_age 周期重建（B02 既有缺口一并收口）。

## 五、验收面复验（卡面三条）

1. **新资料立即有明确版本/索引中状态** — PASS。`test_new_relation_answered_immediately_with_index_status`：uncovered 面关系型即答、metadata 携版本串+fallback_reason、AGE 零调用；M1 突变证可失败。
2. **AGE 旧数据不能压过更新/删除的关系型事实** — PASS。stale 门拦已删关系（AGE 零调用）；fresh 面守卫兜窗口内软删（stale_guard_dropped=1）；守卫失败 fail-closed；M2 突变证可失败。唯一理论面为 R2-C 亚毫秒补偿写族（§四.R2，可忽略+已挂账）。
3. **对同题关系型/AGE 来源可复算，失败保留** — PASS。`recompute_graph_sources` 两路同型一跳语义（无向/strength 下限/LIMIT 对齐）并列复算；任一路失败原文保留（age_error/relational_error，match=None）；三用例正反覆盖。

## 六、E-05 delete-isolation 判例在库性 — 在库

先例：`app/services/galaxy/retrieval_service.py` `_compute_knowledge_version`（E-05 修复 docstring：行数进版）；既有判例测试 `tests/services/test_semantic_cache_version_isolation.py`、`tests/services/test_document_retrieval_isolation.py`（需 live PG/Redis）。本卡 sqlite 可跑反例：`test_relational_watermark_changes_on_delete_of_non_latest_row`（删除非最新行翻版本）+ `test_stale_age_rows_cannot_override_relational_delete`（删除不被 AGE 复活）+ `test_relational_one_hop_is_soft_delete_safe`（软删双向过滤）。删除不复活守卫的反例测试在库且可独立失败。

## 七、插曲核（sparkle-cosmos metrics.py 误改还原）

实现方主动报告曾在主检出 sparkle-cosmos 误改 `backend/app/core/metrics.py` 后还原。本审查独立验证：`git -C sparkle-cosmos status` 未列该文件、`git diff HEAD -- 该文件` 为 0 行——**与 HEAD 逐字节一致，还原干净**。处置评价：主动报告 + 可验证还原 = 诚实纪律的正面判例；教训记录：同机多仓/worktree 并行时编辑前应确认 pwd 与 repo 归属（本审查复现突变时同样以 sha256 前后锚定规避）。不计违规。

## 八、合并落差预判

- base `f9729cc5` → main 现 HEAD `8316bdff`（心跳#12，比 receipt 记录的 `3b96039f` 又前进一步）。
- 产品代码（backend/mobile/proto）：`f9729cc5..8316bdff` 共 10 文件，与本卡 8 个产品文件 **comm 交集为空**——零冲突预期。
- `v4/04_tasks/tasks.json`：有交集（main 心跳改其他卡状态，本卡只改 V4-D06 条目）——按流程在销账合并时解，无实质冲突。
- `backend/app/gen` 为 gitignored 实体复制，不入库不入合并。

## 九、棘轮复核

- ruff：8 个变更文件 **All checks passed**。
- black：新增 2 文件 clean；存量漂移 hunk 逐文件 worktree=main（graph_rag **16=16**、worker **6=6**、knowledge_service **0=0**）——零新增。
- mypy：4 变更文件命中恰为 main 基线 3 处（worker str-bytes-safe 192→223、knowledge_service attr-defined 293→298/359→364，纯行号平移）；新文件 `graph_index_watermark.py` 零错误——**新增 0**。

## 十、挂账（非阻塞，随本 receipt 立项建议）

- **H-1（R2 硬化）**：水位单调 epoch 或 µs 精度+计数，消除等值 token 的同毫秒补偿写碰撞族；同时评估 fresh 面守卫扩展到**关系行** deleted_at（当前只查节点）。
- **H-2（R4 收口）**：`find_learning_path`/`find_related_concepts` 接入 watermark 时效门；收口前冻结新增生产消费方。
- **H-3（R5 条件）**：写生产者入队补齐（或 sync_all_to_age 周期化）之前，不得在任何材料中声称 AGE 派生检索收益已兑现。

## 附：本审查过程产物

- 突变注入/还原与 R2 探针均在审查会话内完成并即时清理（探针临时测试文件已删，不入库）；复跑命令与 receipt 记录一致（SECRET_KEY=ci-test-key DATABASE_URL=sqlite://）。
- 审查后工作区状态：`git status` 仅本 receipt 文件新增。
