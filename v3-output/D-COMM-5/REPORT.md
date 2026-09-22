# D-COMM-5 · 错题卡分享（小队知识互助：谁在哪卡住了）

- Worker：D-COMM-5 ｜ worktree：`wt164` ｜ 基线：`9640f13f`（含 D-COMM-3/4）｜ 未 commit
- 设计依据：D-COMMUNITY 设计卡第 5 卡（P2）；共同约束见主仓 `v3/FLEET-BRIEF.md`（反刷分红线、诚实性、口径单一事实源）
- 交付物：`REPORT.md`（本文）+ `changes.patch`（新文件 `--- /dev/null` 头；已验在基线克隆可干净 apply，apply 后引擎 89 用例 + 网关路由测试全绿）
- Mobile：不做（入口盘点归 MOBILE-GAP 纵队统一管，本卡为后端面交付，回执即本行）。

## 一、可分享字段裁决（含答案是否分享）

分享内容 = POST 时刻服务端从 `error_records` 取真实内容的**白名单投影**（冻结为快照）：

| 字段 | 裁决 | 理由 |
|---|---|---|
| `question_text` 题目 | **分享** | 备考互助的核心载体：看到原题才知队友卡在哪 |
| `question_image_url` 题目图 | **分享，仅 `sparkle-file://` 引用原样透传** | 图片查看走既有网关内 MinIO 鉴权面；分享面不解析、不新开公共/预签名 URL（隐私红线） |
| `subject_code` / `chapter` | **分享** | 科目/章节定位，列表扫读必需 |
| `affected_node_id` + `linked_knowledge_node_ids`（含节点名） | **分享**（primary 置前、去重；节点已删则如实缺席不造名） | 「谁在哪卡住了」的直接答案；队友可直连星图对应知识点 |
| `cognitive_tags` | **分享** | 错因维度标签，低成本高信号 |
| `latest_analysis.error_type` / `root_cause` / `study_suggestion` | **分享** | **错因是本卡的互助价值本体**：根因描述「卡在哪」，诚实呈现（不粉饰），且不含可直接抄的解法 |
| 掌握度快照 `mastery_level` / `mastery_delta` / `review_count` | **分享（分享时刻快照）** | 设计卡明文要求；负 delta（错题诊断扣分）如实呈现，不粉饰——这是「卡住了」的量化证据 |
| `note` 分享者附言（新增可选字段，≤500 字） | **分享** | 分享者自己的话是「哪一步想岔了」的最高信号，与快照文本同过安全过滤 |
| `correct_answer` / `user_answer` | **不分享** | **抄答案防线**：完整正确答案让小队流退化成答案库，破坏备考训练价值；本人答案属个人作答痕迹，无私互助价值且有隐私面 |
| `latest_analysis.correct_approach` / `similar_traps` | **不分享** | ≈解题思路/答案的同构物，与上同一条红线 |
| `latest_analysis.ocr_text` | **不分享** | 与题目内容重复且含 OCR 噪声 |
| `ai_analysis_summary` | **不分享** | 自由文本 AI 摘要，可能整段含解析，无法逐字段保证不泄答案 |

**裁决一句话**：题目 + 错因 + 知识点 + 掌握度快照分享（有互助价值且不泄答案）；完整答案与解题思路不分享（防抄答案）；答案字段在 schema/服务层双重物理隔离（响应模型根本没有这些字段，非前端隐藏）。

## 二、实现清单

| 文件 | 类型 | 说明 |
|---|---|---|
| `backend/app/models/squad_shared_error.py` | 新增 | `SquadSharedError`（一条记录=一次分享：`group_id`+`error_id` 引用+`sharer_id`+`content` 快照 JSONB+掌握度快照三列；部分唯一索引 `uq_squad_shared_error_active` 双方言等价，照 D-COMM-4 先例） |
| `backend/alembic/versions/dc5share_20260922_squad_shared_errors.py` | 新增 | 迁移挂唯一 head `dc4room_20260922`；含 Migration Contract；upgrade/downgrade 双向在 sqlite 隔离库验证通过 |
| `backend/app/models/__init__.py` | 修改（+3 行） | 登记 import + `__all__`（照 D-COMM-4 惯例） |
| `backend/app/schemas/community_shared_errors.py` | 新增 | `SharedErrorCreate`（**只收 `error_id`+`note`**——客户端连可伪造内容的字段都没有）、`SharedErrorEntry`（白名单投影，无答案字段）、列表/撤回响应；`MAX_ACTIVE_SHARED_ERRORS_PER_MEMBER=50` 防刷量 |
| `backend/app/services/community_shared_error_service.py` | 新增 | `SquadSharedErrorService`：share（鉴权→源错题校验→幂等→**SAFETY 词库面过滤**→快照落库）/list（成员可见+liveness）/retract（软删，仅本人）；复用裁决见文件头注释 |
| `backend/app/api/v1/community_squad_shared_errors.py` | 新增 | 3 端点，独立路由文件（D 线惯例，不增重 community.py 5111 行） |
| `backend/app/api/v1/router.py` | 修改（+5 行） | 注册新 router 至 `/community` 前缀 |
| `backend/gateway/internal/handler/proxy_routes.go` | 修改（+10 行） | 网关代理 3 条新路由（proxyWithHeaders，auth 继承，带 D-COMM-5 注释锚点） |
| `backend/gateway/internal/handler/proxy_routes_dcomm5_test.go` | 新增 | 网关 3 路由钉住测试（防 404 回归） |
| `backend/tests/unit/test_community_shared_errors.py` | 新增 | 15 用例（见 §四） |

端点面（引擎 REST，网关一一对应代理）：
- `POST /community/squads/{group_id}/shared-errors` —— 分享自己的错题（引用 error_id，服务端取真实内容；同错题幂等；安全过滤命中 400）
- `GET /community/squads/{group_id}/shared-errors?limit&offset` —— 成员可见列表（新→旧，分享者/科目/知识点/掌握度快照/时间）
- `DELETE /community/squads/{group_id}/shared-errors/{share_id}` —— 撤回（软删；仅分享者本人）

关键语义：
1. **内容服务端取、不可伪造**：请求体 schema 白名单只有 `error_id`/`note`；服务端校验「本人名下+未删除」后取真实内容投影。所有权检查先于幂等检查——他人分享非本人错题必 404，不会被幂等分支吞掉。
2. **快照即所服务内容（TOCTOU 关闭）**：安全过滤（`core/llm_output_validator.py` 的 `output_validator` 单例，SAFETY-LEX 词库面）检查对象=快照本体；分享后再 PATCH 源错题夹带违规内容，小队流里仍是分享时刻被审过的快照（测试钉死）。
3. **安全过滤 fail-closed**：命中即拒（400 一律话术，违规明细只进服务端日志，不回泄露过滤规则），零落库。
4. **隐私**：非成员 403（POST/GET/DELETE 三拦）；非 SPRINT/不存在小队统一 404 不泄露存在性；源错题被主人软删→分享自动从流中消失（删错题=撤回所有下游曝光；列表读侧 liveness 过滤，不碰 error_book 写路径）；图片仅 `sparkle-file://` 引用透传。
5. **反刷分红线（D20）双钉**：AST 导入扫描（四模块禁 import photon/experience/leaderboard/xp 域）+ 行为断言（分享后 photon_balance 不变、`photon_transaction_history` 零写入、小队榜逐字段不变；光子/火苗扰动不改变分享流）。分享是纯读+分发，不碰 mastery 写路径（ERR-IDEM 域不受影响）。
6. **方言陷阱记录**：`error_records.id` 是原生 `postgresql.UUID`（sqlite 侧存 32 位 hex），与 `BaseModel.GUID`（36 位连字符串）跨类型 SQL join 恒不匹配——列表 liveness 用「取回后按 id 集合过滤」实现（方言无关），已在代码注释钉明防回归。

## 三、冲突面声明

- **本卡触碰面**：`app/api/v1/router.py`（+1 import、+4 注册行）、`app/models/__init__.py`（+2 行 import/`__all__`）、`gateway/internal/handler/proxy_routes.go`（+10 行，squads 段 D-COMM-4 块之后）。均为单点追加，无语义改写。
- **与 wt161（驱动器）**：无交集——本卡不碰 sprint_task_ledger、CP-04~08、任务账本；唯一共享点是都「读」squad 聚合（我只在测试里对比榜分不变）。
- **与 wt162（TOUR）**：低风险——TOUR 串测的新面清单（计划确认/小队/自习室/榜/自我锚/兑换）不含 shared-errors；若其旅程脚本对 `/community/squads/**` 做全量路由快照比对，会多出 3 条新路由（新增，不破坏既有）。
- **与 wt163（MOBILE）**：无代码交集；本卡新增 mobile 待接入入口 3 条（见上端点面），已在本报告登记供其补盘点。
- **与 SAFETY-LEX/SAFETY-FP（今日 `llm_output_validator.py` 的词库修订）**：本卡是该词库面的**纯消费方**（`output_validator` 单例 import），零改动；若该词库后续再收/放，分享过滤行为随之自动一致。
- **迁移链**：`dc5share_20260922` 挂当前唯一 head `dc4room_20260922` 之后，`tests/test_migrations_single_head.py` 全程绿（合入时若主链已前移，需按主会话惯例改挂新 head）。

## 四、回归验证（对比法）

- **新面**：`tests/unit/test_community_shared_errors.py` 15 用例——分享/列表回路+掌握度快照诚实（负 delta 不粉饰）、快照防篡改（TOCTOU）、内容服务端取不可伪造（含塞伪造字段被无视、非本人错题 404、图片引用透传）、安全过滤命中拒分享+零落库+API 400、撤回（本人/非本人/重复撤回/撤后再分享）、幂等（同错题单记录）、非成员 403/非 SPRINT 404/源错题删除自动消失、零光子零榜分（AST+行为双钉）、error_book 只读面对比锚。
- **对比法**：基线克隆（`9640f13f`，`git clone` 至 /tmp，天然不含本卡改动）跑 `test_community_squad_mvp.py + test_community_study_room.py + test_error_book_mastery_sync_service.py + test_error_mastery_idempotency.py + test_migrations_single_head.py` = **74 passed / 0 failed**；本 worktree 同集合+新 15 用例 = **89 passed / 0 failed**。**error_book+squad 域零新增失败，ERR-IDEM 域（mastery 同步 39 例+幂等 8 例）抽查零回归。**
- **Patch 自包含验证**：`changes.patch` 在基线克隆 `git apply --check` 干净 → apply 后上述 89 用例全绿。
- **网关**：`CGO_ENABLED=0` 全 handler 包 `go test` 通过；`go build ./...` 通过；patch 后克隆的路由测试同样通过。
- **迁移**：隔离 sqlite 库 stamp→upgrade→表+8 索引（含部分唯一索引）就位→downgrade→表消失，双向可逆。
- **Lint**：新增 6 文件 ruff 全绿；black 对新增文件已过（`router.py`/`models/__init__.py` 本身基线即非 black-clean，系存量债，本卡不加宽、不代偿格式化以保 patch 最小）。

## 五、诚实申报

1. **分享列表非 SQL 分页**：全集取回后内存过滤+切片。依据：行数有硬上界（每成员 50 张 × 小队 8 人 ≤ 400 行）；换取的是跨方言类型安全的 liveness 过滤（见 §二-6 方言陷阱）。若未来放开上限需改回 SQL 级分页+Union 类型归一。
2. **知识点名称解析为每条目查询**（页内 ≤100 次）：沿用 D-COMM-3 榜分页的 N+1 先例；量级受页大小约束，未做批量优化（可作后续微优化，不影响语义）。
3. **安全过滤是词库面而非语义审核**：复用既有 `LLMOutputValidator`（敏感信息/恶意指令/注入/合规词库四层）。语境级变体（如拼音、拆字）不在其能力内——这是平台既有能力边界，不是本卡引入的弱点；命中策略 fail-closed。
4. **`snapshot_note` 附言是设计卡之外的最小增量**：直接服务「谁在哪卡住了」的互助语义，成本一行列+同过安全过滤；不需要可让Leader在合入时剥离（剥除后 note 恒为 None，其余语义不变）。
5. **worktree 内有两处 gitignored 的生成代码副本**（`backend/app/gen`、`backend/gateway/gen`，自主仓复制，proto 已 diff 确认与基线逐字节一致）：网关/引擎测试的编译依赖，保留供合入验收在树内直接跑测试；不入 patch、不入库。
6. **对比法基线为本 worktree HEAD（9640f13f）克隆**，非主仓实时 HEAD——wt161/162 若已合入新迁移/路由，主会话合入时以惯例改挂与重跑为准（已在 §三声明）。

## 六、收工核查

- [x] `/tmp/wt164-baseline`（对比法克隆）已删除
- [x] 迁移验证用临时库 `/tmp/dc5mig.db` 已删除
- [x] pytest tmp（`/tmp/pytest-of-*`）无本卡残留，已清
- [x] 无独立端口进程残留（本卡纯 pytest/go test，未起服务）
- [x] 主仓只读未动；worktree 内改动=patch 所列 10 文件，无越界
- [x] 零凭据入交付物
