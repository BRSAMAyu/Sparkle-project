# D-02 REVIEW_RECEIPT_2 · R2 深层验收（DeepAudit 路线）

- **Task**: D-02「成果账本 Outcome Ledger」（stream DATA, risk high, reviewers_required=2）
- **Reviewer**: R2（DeepAudit），2026-09-19
- **审查对象**: wt5 @ `fedc6a8e`，4 个新增未跟踪文件（与 changes.patch 逐字节一致，收尾哈希校验通过）
- **方法**: 主仓只读锚定（B-02 台账 / X-01 契约 / D-01 event_registry / V3-FIX-01 leaderboard / models / 任务卡原文）；wt5 内 sqlite 全量重跑；6 项变异实验（全部还原，还原后 4 文件与 patch 哈希一致）；沙箱特征化探针（已删）；live PG 只读 SELECT（只查 sparkle_db，未触任何写路径）
- **总 Verdict**: **CHANGES**（1×P1 + 5×P2 + 若干 P3；架构与零写路径成立，但两条卡面验收各有一处实证击穿）

---

## 0. 复验基线（自报核对）

| Worker 声称 | R2 复验 | 结果 |
|---|---|---|
| 63 项测试全绿 | sqlite 内存库实跑 `36+27=63 passed`（+X-01 契约回归 29 → 92 passed） | 属实 |
| 零 schema/零写路径/零 Alembic | 两模块仅 `select(`×19；无 insert/update/delete/commit/flush（grep 命中均为 Python `set.add`）；`git diff HEAD -- backend/alembic` 为空；patch 恰 4 文件、无 gen/ | 属实 |
| 分页 bug 修复 + 回归钉住 | 变异 M2（删 focus 探针）→ 回归测试必红 | 属实 |
| echo 谓词钉死 | 变异 M3（去谓词）→ 必红 | 属实 |
| focus 门槛边界钉死 | 变异 M4（`>=`→`>`）→ 3 项必红；`required_focus_minutes` 对 actual_minutes=0/None 给 10（绝对下限），actual=20 → 门槛 10，无 off-by-one | 属实 |
| EVIDENCE_KINDS 七值对齐 | 与 `app/core/action_plan.py:76-92` 逐值一致，import 期断言在位 | 属实 |
| cohort 词表与 V3-FIX-01 一致 | `outcome_ledger_service.py:72` == `leaderboard_service.py:65` == `("guest","seed")`；B-02 台账 INV-06/07 命名空间同为 guest/seed（B-02 无 "system" registration_source） | 属实 |
| live smoke 79/79 0 重复 | 未复跑其脚本；但见 §1——live 数据本身已含 tie 对，该 0 重复是页边界未落在 tie 上的运气而非不变式成立 | **不成立（见 P1） |
| 「code v1 不可解析永不单独升 actual」 | **机制上不成立**（见 P2-1 特征化复现） | 不属实 |
| 「user 档永不升…是守卫钉死」 | 词表**值**无测试钉（变异 M1 改档位全绿，见 P2-5） | 部分不属实 |

---

## 1. P1（必修）· 跨流同刻 tie 时 keyset 分页重复交付，直接违反「不重复计数」验收

**Finding**。`_stream_anchor`（`outcome_ledger_service.py:109-119`）把全局游标键剥前缀后拿**裸 UUID** 与本流 `id.cast(String)` 比较；当游标来自**词序更小前缀**的流（behavioral/focus_session/quiz_feedback/study_record）时，其余流的 keyset 在 `occurred_at == anchor_ts` 处退化为永真（任何 UUID 字符串都 < `'focus_session:…'`/`'behavioral:…'`/`'quiz_feedback:…'`，因前缀第二字符 'o'/'e'/'u' 均大于十六进制字符集上界）。而全局合并序（`merged.sort` 按 `(occurred_at, key)` 倒序，:200）要求同刻时**前缀更大的流排序在上**——已被本页返回。两条规则矛盾 → 同刻条目被**重复交付**。

**Execution Chain**：页末条目为 focus/quiz/study/behavioral 流 × 同刻存在 task/study/quiz 流行 → `next_cursor` 取该条目 → 下页各流 keyset 用裸 id 对比外流键 → 同刻的高前缀流行重取 → 重复进入 `merged` → 重复返回。

**复现**（wt5 sqlite 探针，已删，输出原样）：

```
focus-tie:  seen = [task_completion:d1284ebe…, focus_session:234752d6…,
                   task_completion:d1284ebe…(重复), focus_session:216bd57d…]   # 3 行数据翻出 4 条
quiz-tie:   seen = [task_completion:8c0bb1bc…, quiz_feedback:9647b042…,
                   task_completion:8c0bb1bc…(重复), focus_session:e4815708…]
```

**live 触发条件已存在**（只读 SELECT）：`tasks(coalesced completed_at,created_at)` 与同用户 `study_records.created_at` **精确同刻 2 对**，属主均为 `email` 用户（`72bfdfc4-…`、`771c64e7-…`，任务 `a7c89c79-…`/`1fe56adb-…`）——`exclude_seed_cohort=True` 也保护不了；当前 task↔focus 同刻 0 对。worker 的 79/79 翻页 0 重复只是页边界未落在 tie 上。

**为何测试全绿**：63 项测试的时间戳构造系统性避开 tie（`test_keyset_walks_all_outcomes_no_dup_no_miss` 恰好 `ts + timedelta(seconds=1)`，:399；多数用例只放单流数据）。这是「测试全绿但不变式为假」的典型。

**Impact**：任何按游标翻页的消费方（Aurora 事实面注入、WVPL 统计）在同刻处**重复计数**——正是卡面 acceptance「Outcome 能跨模块被查询且不重复计数」要防的事；重复条目 outcome_id 相同，下游若以 id 幂等去重可止血，但账本自身承诺的「不重不漏」不成立。

**Remediation**（小改）：各流 SQL keyset 直接用**全局键形态**比较——`literal('<source>:') || id.cast(String)` 对 `anchor_key`（不再剥前缀），使 SQL keyset 与 `merged` 的全局排序严格同构；删除 `_stream_anchor` 的跨流换算。补钉死测试：跨流同刻 + 页边界落在外流条目上的翻页用例。

**Verification**：复现脚本翻页 0 重复 0 漏；对五流两两组合的同刻矩阵穷举。

---

## 2. P2（应当修）

### P2-1 · 证据验证只验「归属」不验「来源」——REPORT §4.1 至少一条声称被机制证伪

`_resolve_declared_refs`（:595-682）的「已验证」= ref scheme ∈ {document,task,subtask} 且行存在且属本人。**不校验 kind↔scheme 配对、不校验与任务的关联、不校验文件生命周期**。特征化探针（wt5 sqlite，全部实跑）：

| 探针 | 结果 | 判定 |
|---|---|---|
| kind=**code** + `document://<自有文件>` | truth=**actual** | REPORT §4.1「code … 永不单独升 actual」被证伪——该不变式只靠「code 不会配 resolvable scheme」的君子协定，X-01 契约层（action_plan.py:224-227）也不查 kind↔scheme 配对 |
| kind=artifact + `document://<与任务无关的自有旧文件>` | truth=**actual** | 验证的是归属不是相关性：上传过任意一个文件的用户可把之后所有完成都洗成 actual |
| kind=artifact + `task://<自己的另一个任务>` | truth=**actual** | 自我声明洗白：被指向的 task 行本身也只是用户主张，「声明不构成证明」在 owner 内部维度失效（跨用户注入防住了，自引用没防） |
| 完成后 2 小时才开始/结束的 40 分钟 focus | truth=**actual** | 见 P2-3 |

守卫语义与 B-02 反污染哲学的偏差：焦点/quiz 是「服务器独立观察」成立，但 artifact/file 档的「已验证」在 owner 内部几乎等于「声明即证明」。**Remediation**：kind↔scheme 配对白名单（code 无可解析 scheme → 永不 verified）；document ref 至少校验 `status`/`lifecycle_status`（见 P2-2）；task:// 不应作为完成证据可解析 scheme；中期：ref 与 task/plan 的关联性（StoredFile 若有 plan/task 关联列则校验）。另：`resolved` 集合不分 scheme（:634-660），`document://<task uuid>` 也会因 task 解析而命中——配对修复时一并处理。

### P2-2 · StoredFile 生命周期被忽略：uploading/orphaned/revoked/erased 文件全部算「已验证证据」

解析查询（:636-643）只有 `StoredFile.not_deleted_filter()`。但 `file_storage.py:13-20,34-39`：`status` 默认 **'uploading'**（从未传完的文件即存在行）、`lifecycle_status ∈ {active,archived,revoked,orphaned}`、另有 `erased_at`。探针实证 `status='uploading'` 文件 → actual。被撤销/被抹除/孤儿化的文件仍然把完成升为 actual。**Remediation**：resolved 需 `status` 就绪且 `lifecycle_status='active'`（且 `erased_at IS NULL`）。

### P2-3 · focus 覆盖率无时间方向约束：完成后的会话追溯升级，truth_class 随时间非单调翻转

`_task_focus_sessions`（:562-574）对 focus 无任何与 `completed_at` 的时间关系约束（探针：完成后 2 小时的会话 → actual）。账本是读模型、每次查询重算——**同一个 outcome_id 今天 self_reported、明天 actual**，且升级证据可以发生在「完成所声称的工作」根本不可能被该会话覆盖的时间段。对 Aurora「事实面注入」与 WVPL 这类把 truth 当快照用的消费方，这是隐蔽的时点语义陷阱。live 现状 0 例（`start_time > completed_at` 的完成任务为 0），V3 上线前必须定方向。**Remediation**：仅计入 `start_time < completed_at`（或 `end_time <= completed_at` + 宽限窗）的会话；docstring 明示 truth 的时点性。

### P2-4 · goal evidence 静默出册：卡面 Work ① 明列 goal，交付物既未映射也未列入「未做」

任务卡 Work ①「映射现有 task completion/artifact/focus/quiz/**goal** evidence」。`goals` 表具备 outcome 面（`status='completed'`、`completed_at`、`minimum_acceptance_criteria`，goal.py:39-68），X-01 `ACTION_SOURCE_REF_SCHEMES` 含 `goal://`（action_plan.py:110），但：五源无 goal、`RESOLVABLE_REF_SCHEMES` 无 goal、correlation 无 goal_id（task→plan.goal_id 的链路也未带出），REPORT §8「未做」清单**只字未提 goal**。属未声明的范围收缩（行为Outcome≠goal）。对 REPORT §6 声称的「WVPL goal-linked outcome 判定用本账本」——无 goal 维度，该消费方式无法落地。**Remediation**：至少补（a）goal:// 解析或（b）correlation.goal_id 经 plan 链（c）显式写入未做清单并给出排除理由，过卡面口径确认。

### P2-5 · 冻结纪律缺测试牙齿：信任档位值与 cohort 词表改错全绿

- 变异 M1：`EVIDENCE_TRUST_TIERS["user_confirmation"] = VERIFIABLE` → **63 全绿**。冻结测试（contract :74-77）只断言键集合覆盖，不断言值；`test_user_tier_evidence_never_upgrades_to_actual`（:116-134）传 `verified=frozenset()`，改档位后照样过。REPORT 称「user 档永不升 actual…测试钉死」——钉的是分级函数在正确档位下的行为，不是档位本身。配合 P2-1 的 kind 洗白路径，档位漂移无任何红灯。
- 变异 M6：cohort 词表去掉 `"seed"` → 27 全绿（测试只造 guest 用户）。与 leaderboard 的「一致」是拷贝约定不是机制。

**Remediation**：契约测试逐 kind 断言档位值与 cohort 元组（对照 leaderboard import 或字面钉死）。

### P2-6 · quiz/behavioral 两流缺 `not_deleted_filter`，五流删除口径不一致

`_quiz_feedbacks`（:818-828）与 `_behavioral_outcomes`（:882-891）谓词均无 `not_deleted_filter()`（两者都继承 BaseModel、有 deleted_at），而 task/study/focus 三流都有；`count_by_source` 同样缺失（:262-272）。软删除的 quiz 反馈/行为结果会计入账本与计数。`test_deleted_rows_are_excluded` 只测 task+focus。live 两表 0 行故今日无实害，M-06 起行即成真缺陷。**Remediation**：补两处谓词 + 测试。

---

## 3. P3（观察/登记）

1. **quiz 流对脏 meta 会整查询崩溃**：`_quiz_feedbacks` 的 `_uuid_str(meta["task_id"]/meta["node_id"])`（:843-845）与 `_task_quiz_feedbacks` 的 `UUID(str(raw))`（:592）对非 UUID 字符串 raise ValueError → 该用户整个 query() 500。上游 `_record_feedback`（feedback_service.py:178-207）把 event_data 原样并入 meta_data，而 event_listener 传入的是 **UUID 对象**、引擎无自定义 json_serializer（session.py:94 用默认 json.dumps）→ PG 上含 UUID 对象的写入会 TypeError 且被 try/except 吞掉——quiz 流第一行真数据落库前，生产者自身还有一道坎。「上线第一次遇到真数据最可能炸的点」清单：非 UUID task_id/node_id、`meta_data` 为 list、trigger_task_id 列（galaxy.py:319，当前无人写）与 meta 双轨漂移。建议 quiz 接线卡把 `trigger_task_id` 列为关联真源而非 meta。
2. **「代码路径在册」表述过强**：`quiz_passed/quiz_failed` 事件**没有任何发射方**（全库仅 FeedbackType 枚举与 collect_implicit_feedback 的存储函数），不是「live 未触发」而是「无生产者」。
3. **truth_coverage 截断语义**：默认 limit=1000（上限 2000）静默截断、ratio 按截断窗计算——已在 REPORT §9.3 披露，接受，建议返回值带 `truncated` 标志。
4. **「与 B-02 完全对齐」措辞**：B-02 台账 inventory 的 truth_class 是另一套分类学（demo/mock/seed_namespace/pollution/actual…）；五值 = 卡面四值（actual/self-reported/estimated/unknown）+ demo。合成合理，但「完全对齐」应改为「卡面 ∪ B-02 概念的合成词表」，防下游误以为存在单一权威五值真源。
5. **消费点零接线**：全仓无任何模块 import OutcomeLedgerService（docstring 登记 ≠ 接线）。卡面 Work ③「提供 outcome query 给 Aurora/EM/Galaxy」以库级查询面满足是可辩护的边界读法，但 acceptance「能跨模块被查询」目前只在库层成立——需在 A-05/M-06/G-01 卡登记强制接线项，防止读模型长期无消费者而语义漂移（P1 修复正说明无消费者的不变式会烂）。
6. **测试含充数断言**：`assert service.query.__doc__ is not None`（service 测试 :546）。
7. **wt5 内残留 `backend/app/gen/`（未跟踪、且在 wt5 的 .gitignore 下未被忽略）**，目录 mtime 2026-09-19 15:41:45（晚于 REPORT 15:26 的「验证完即删」，非本 reviewer 产生）。合入时主会话须确认不入库。
8. **import 期断言**：X-01 词表演进会让全后端 import 崩溃——同一部署单元内属故意设计（fail-fast），接受，登记在案。
9. **estimated/demo 无生产者、unknown 仅 26/378 legacy 行触发**（completed_at NULL 实测 26 行）——与自报一致。

---

## 4. 九大风险面逐面 Verdict

| # | 风险面 | Verdict | 要点 |
|---|---|---|---|
| 1 | 真相分级语义 | **CHANGES** | classify 纯函数本身判序正确、边界无 off-by-one（M4 红×3）；但「code 永不升」「声明不构成证明」在 owner 内部被 P2-1/P2-2 证伪；档位值无冻结测试（M1 绿） |
| 2 | 去重身份长程 | **PASS（带 P3）** | (source, source_id) 各流均为 UUID 主键，跨表身份冲突不可能；echo 谓词覆盖 live 全部 record_type（task_complete 12=11 echo+1 standalone，error_review/diagnosis 无 task_id）；「同 task 在两流」有测试且 M3 必红；ECHO 词表漂移风险已自报（§9.5）；focus 既当独立 outcome 又当任务证据是设计选择（不同 outcome_id），语义上说得通但应在 docstring 点明 |
| 3 | 分页正确性 | **CHANGES（P1）** | 同刻 tie 重复交付（复现）；limit+1 探针与批次推进逻辑本身正确（M2 红、深扫/空页/满页路径推演无漏）；tie 外无重漏 |
| 4 | 聚合退化 | PASS | 批量查询无 N+1（每批 ≤7 条 SQL、IN 列表 ≤2001 参数）；count_by_source 五条独立 COUNT；`tasks.completed_at` 无索引致翻页重复全表扫（dev 规模可忍，REPORT §9.3 已披露） |
| 5 | cohort 排除一致性 | PASS（带 P2-5 半） | 词表与 leaderboard/B-02 逐值一致；但值本身无测试钉（M6 绿） |
| 6 | 解析路径 live 空窗 | **CHANGES** | sqlite 覆盖的解析器从未见过真数据；生产者侧 quiz 无发射方 + UUID 序列化缺陷 + meta/列双轨（P3-1）；解析器自身的四个语义洞见 P2-1/P2-2 |
| 7 | 零写路径 | PASS | 仅 SELECT（19 处）、无 DDL/迁移、patch 恰 4 文件 |
| 8 | 测试语义（变异） | **CHANGES** | M2/M3/M4 必红（回归钉真实有效）；M1/M6 全绿 = 冻结契约值无牙 |
| 9 | 消费点缺口 | PASS（登记） | 卡面无「必须接线」硬性条款，库级查询面 + 文档登记是可辩护读法；P3-5 要求后续卡强制登记 |

---

## 5. 变异实验清单（全部还原；收尾 4 文件与 changes.patch 归一化哈希一致，`ALL RESTORED OK`）

| # | 变异 | 结果 | 判定 |
|---|---|---|---|
| M1 | `EVIDENCE_TRUST_TIERS["user_confirmation"] → VERIFIABLE` | 63 全绿 | **守卫缺口**（P2-5） |
| M2 | focus 流 `.limit(limit+1) → .limit(limit)`（去探针） | 1 failed（single_stream_dominant 回归） | 钉住，有效 |
| M3 | study standalone 流去 echo 谓词 | 1 failed（echo merge 测试） | 钉住，有效 |
| M4 | `covered >= threshold → >` | 3 failed（contract+service 门槛边界） | 钉住，有效，无 off-by-one |
| M6 | cohort 词表去 `"seed"` | 27 全绿 | 未钉（P2-5） |
| M5 | code kind + document ref 是否升 actual | 特征化探针实证 actual | REPORT 不变量证伪（P2-1，非变异、为行为复现） |

## 6. live PG 只读证据（全部 SELECT；未写任何行）

- task↔study 精确同刻 **2 对**（email 用户，见 §1）；task↔focus 同刻 0 对；task↔behavioral 0。
- `expansion_feedback` 全表 **0 行**（非仅 quiz 源）。
- COMPLETED 378 中 completed_at NULL **26** 行 → unknown 档有真实输入。
- 完成后开始的 focus 会话：**0**（P2-3 目前纯前瞻）。
- study_records 词表：task_complete 12（11 带 task_id=echo）/error_review 12/error_diagnosis 6，与 REPORT §1 一致。

## 7. 收尾状态

wt5 终态 = 4 个交付文件 + `v3-output/D-02/`（含本 receipt）+ 未解明的 `backend/app/gen/`（非本 reviewer 产生，合入时主会话处置）。探针测试文件、/tmp venv 与比对产物、`.pytest_cache` 已全部清除；无进程/模拟器/浏览器；未 commit/push；dev DB 全程只读。

**总 Verdict: CHANGES** —— P1（tie 分页重复）与 P2-1/P2-2（验证语义洞）修复前不得合入；P2-3/P2-4/P2-5/P2-6 随返工一并处理或显式立卡。
