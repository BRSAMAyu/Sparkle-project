# D-02 REVIEW_RECEIPT_3 · R2 Delta 复核（返修后二次验收）

- **Task**: D-02「成果账本 Outcome Ledger」（risk high, reviewers_required=2）
- **Reviewer**: R2（DeepAudit，第一手记录持有者），2026-09-19 返修轮
- **对象**: wt5 @ `fedc6a8e`，返修后 4 文件（与再生成的 changes.patch 逐行哈希一致，见 §6）
- **方法**: 第一轮复现手法原样重放（同刻探针/变异 M1/M6）+ 新增变异（裸 id 退化、import 断言、E/F/G 门）+ live PG 独立复算（自有 SQL + 真服务只读 walk）；变异全部走 cp /tmp 备份法，收尾 md5 与备份一致；禁 stash/reset/clean/切分支全程遵守
- **总 Verdict**: **ACCEPT**（全部 P1/P2 修复经独立复验成立；2 项残余观察登记，不阻塞）

---

## 1. 逐项复验结论

| # | 返修自报 | R2 独立复验 | Verdict |
|---|---|---|---|
| P1 | `_stream_key_expr` 全局键 keyset（`'<source>:' \|\| id.cast(String)`，:135-143）；task 流内部锚点同步全局化（:429/:458） | 代码读验：五流 keyset（:437/:747/:804/:867/:932）+ task 批间锚点均带前缀，与 `merged.sort` 的 `(occurred_at, key)` 全序严格同构；**第一轮的两条重复交付复现（focus-tie/quiz-tie 原构造原样重放）现在恰一次**；新增阳性对照（正常路径不因修复过紧而失效）| **PASS** |
| §5.1 回归 | 6 项同刻测试 | 实读测试：5-way tie×两档 limit=1 全量翻页恰一次+严格降序（:731）、页边界参数化×4 逐源钉死 R2 复现链（:774）、翻页≡大页等价（:808）——机制级在位。**变异裸 id 退化实际红 8 项**（>自报 6：连锚点行自排除也一并破坏，守卫强于自报） | **PASS（超自报）** |
| §7.1 live | 72bfdfc4 恰一次 | **自有 SQL 复算**（不同表述：全边界锚不变式「严格在锚下方行数 = total − rn」）：72bfdfc4 total=3 **违规 0**；771c64e7 total=1（echo 行正确不入独立流）**违规 0**。**真服务只读 walk**（asyncpg 连接 + `SET default_transaction_read_only=on` 硬保证）：两用户 × limit∈{1,2,3} 全部 dup=0、严格降序、与 count_by_source 一致；另抽 focus 大户 fc7c84b9：101 条 6 页 dup=0 计数吻合 | **PASS** |
| P2-1 | `EVIDENCE_KIND_REF_SCHEMES` 白名单（v1 仅 artifact/file×document；code 恒空；task/subtask 移出）+ TaskDocument 显式挂载 + UUID 规范化 | 第一轮四个洗白构造（code+document/无关旧文件/uploading 文件/own-task ref）重放全部 **self_reported**；挂载+就绪+关联三条件齐备的阳性对照仍 **actual**（不过紧）；映射整表逐值冻结测试在位（:101-114） | **PASS** |
| P2-2 | status∈{uploaded,processed}+lifecycle active+erased_at NULL | 代码 :686-698 在位；变异 Mut-F（删三过滤）→ **8 红**（revoked/orphaned/erased 参数化全触发） | **PASS** |
| P2-3 | `start_time < Task.completed_at` JOIN（:600-610） | `test_focus_starting_exactly_at_completion_does_not_count`（:586）钉死 == 边界为排除；变异 Mut-G（删 JOIN 条件）→ **2 红**；完成后 2 小时会话重放 → self_reported | **PASS** |
| P2-4 | goal 排除决策记录（§8③：派生聚合面、入册即重复计数、解除条件明示） | 决策合理（goals.progress/mastery 确为滚动聚合，live 4 行无独立完成生产者）——第一轮要求的「显式声明」已满足，解除条件（一等生产者出现→bump 版本双人评审）可执行 | **PASS（文档项）** |
| P2-5 | 档位整表字面断言 + cohort 字面钉死 + leaderboard 双向对照 | **M1′ 重跑（user_confirmation→verifiable）→ 2 红**（values_frozen + never_verifiable）；**M6′ 重跑（去 seed）→ 1 红**（vocabulary_frozen :893-902 三重断言）；对照方 `leaderboard_service.py:65` 与主仓一致 | **PASS** |
| P2-6 | quiz/behavioral 补 not_deleted | `_quiz_feedbacks` :862、`_behavioral_outcomes` :928、count_by_source 同步、`_task_focus_sessions` :607 证据面补齐；`test_deleted_quiz_and_behavioral_rows_leave_the_stream`（:312）在位 | **PASS** |
| C2-1 | outc_* 非 canonical UUID 的接线限制已纠 | core docstring + §2/§8① 表述与 `event_registry.CorrelationIds` 校验一致（第一性核对过 :477-487 值域门） | **PASS（文档项）** |
| P3-1/P3-2/P3-3/P3-6 | _safe_uuid_str / 无生产者表述 / 截断 docstring / 删充数断言 | `_safe_uuid_str`（:127-132）在 quiz 双处使用（:631/:887-889）；§3 注与 §9.3 措辞核实；grep 无 `__doc__` 断言 | **PASS** |
| 基线 | 92 passed（36+56） | 实跑 **92 passed**（我的沙箱缺 email-validator 时 1 error——`requirements.txt:73` 已声明该依赖，属我环境缺口非代码问题；补装后全绿）；+X-01 契约回归共 **121 passed** | **PASS** |

## 2. 变异重跑表（全部 cp/备份还原，md5 与返修基线一致）

| # | 变异 | 红 | 备注 |
|---|---|---|---|
| A | 五流 keyset 退回裸 `id.cast(String)` | **8** | 超自报 6：`test_keyset_walks…`/`single_stream_dominant…` 也红——裸 id 对全局锚连锚点行自排除都破坏，守卫强于声称 |
| M1′ | 档位 user_confirmation→verifiable | **2** | 第一轮缺口已闭合 |
| M6′ | cohort 去 "seed" | **1** | 第一轮缺口已闭合 |
| D | X-01 `EVIDENCE_KINDS` 加第 8 kind | **import 即 AssertionError**（collection error） | fail-fast 真实触发；且主仓 HEAD 的 action_plan.py 与 wt5 基线 md5 一致（9c0ab7cc…），X-02/C-02/M-07 未动词表，合入无断言风险 |
| E | artifact 配对放宽接受 task:// | **1** | kind 门有牙 |
| F | 删文件生命周期三过滤 | **8** | 生命周期门有牙 |
| G | 删 focus 时间方向 JOIN 条件 | **2** | ==completed_at 边界测试在位且红 |

## 3. 残余观察（不阻塞 ACCEPT）

1. **relevance 门的最终落点是「显式挂载」而非「客观相关性」**：`task_documents.linked_by ∈ {user, ai}`（attach 服务端验文件归属，task_document_service.py:52-75），`linked_by='user'` 的挂载仍是用户动作——owner 仍可"挂载+声明"两步走把自有文件升 actual。相比第一轮的"拥有任意文件即洗白"已是实质收紧（任务特定绑定、服务端校验、留痕可审计），属 v1 合理信任边界；建议登记：若未来要求更强，可对 `linked_by='ai'` 挂载或上传时间早于完成时间的挂载才计 verified。
2. **quiz/behavioral/`_task_quiz_feedbacks` 的 meta 关联仍非 `trigger_task_id` 列**：REPORT §3 注已把列列为接线真源建议，本轮未改（无生产者、live 0 行，改了也无从验证）——与自报一致，接线卡落实即可。

## 4. 集成与交付完整性

- **patch↔树**：4 块逐一归一化哈希 IDENTICAL（`PATCH<->TREE OK`）。
- **3way apply**：对 `0ea1e198` 与主仓 HEAD `4b16573b` 双双 `--3way --check` CLEAN（/tmp 克隆中执行，主仓零接触）。
- **零写路径**：返修后 service 仍 16 处 `select(`，写形 grep 命中仅为 `set.add`；无 alembic 改动；主仓 action_plan/task_document/file_storage 三文件自 wt5 基线以来零漂移（md5 相同）。
- **live 只读纪律**：SQL 复算 + 服务 walk 均走 `default_transaction_read_only=on` 连接，零写。

## 5. 第一轮发现处置对照

P1 修复（机制+测试+live 三层独立复验）｜P2-1/2/3/5/6 修复（重放+变异双层）｜P2-4 文档决策记录｜P3-1/2/3/6 修复｜P3-4 表述已改｜P3-5/7/8/9 登记在案（消费点接线、gen/ 合入确认、import 断言设计、estimated/demo 生产者现状）。第一轮回执的全部 P1/P2 均有对应处置且经本复核证实，无假通过项。

## 6. 收尾状态

wt5 终态 = 4 个交付文件 + `v3-output/D-02/`（REPORT/changes.patch/REVIEW_RECEIPT{,2,3}.md），与本轮开工清单一致；探针/venv//tmp 克隆与备份/`.pytest_cache` 已全部清除；`backend/app/gen/` 本轮不存在（与返修自报一致）；未 commit/push、未 stash/reset/clean/切分支；主仓与 dev DB 全程只读。

**总 Verdict: ACCEPT**
