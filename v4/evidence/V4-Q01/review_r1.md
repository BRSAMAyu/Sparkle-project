# V4-Q01 独立审查 R1（Q01 首审）

审查人：wt 独立会话（未参与实现）· 2026-09-29 · 分支 `agent/v4/q01`
被审对象：12b3bdba 五件套 + raw/ + db/ + video/（自报 REVIEW_READY，value=FAIL）
审查方式：全部亲验（活库只读探针 + console/语义树/帧逐项核对 + 代码锚核验），不信自报。
审查证据：`raw/review_r1_probe_20260929.txt`（本审查追加的只读 DB 探针快照）。
边界：未触发任何新 hybrid start；未改产品码；未 push。

## 0. 结论

**裁决：PASS_WITH_CHALLENGES —— Q01 可闭账（value=FAIL 如实记录，终门读 FAIL）。**

主证骨架（L3 接续/卡住/澄清/纠正提交 PASS；G6 产品级挂死反例；G5 投影缺口；value=FAIL）经独立复算全部成立。三处 MEDIUM 级叙事失实（§5 纠正落账单元格、§6 LLM 机制归属、G6 反例台账两处归属）须在闭账 commit 中一并更正——均为文档更正，不需要新运行，不改变裁决方向。

---

## 1. 逐靶裁决

### 靶1 主证复算 —— PASS_WITH_CHALLENGES

**persona 锚 ✓**：`db/r1_attempt10_db_evidence.json` memory_goals 1 行 active（id `ccdc03d5`，"两周内掌握线性代数矩阵特征值…"，created 09:58:17Z=17:58:17+08），与 steps `goal_anchor_created` @17:58:36、console `POST /api/v1/profile/onboarding` 1 次三向一致；活库复查（probe §7）该用户 active_goals=1。帧 `06-persona-step1.png` 亲阅为真实画像引导 UI（5 步+跳过），与 J-02 快车道叙事一致。

**文档底料 ✓**：archived json stored_files 1（`251617d5`，processed）+ document_chunks 9（chunk_index 0-8，真实特征值笔记分块）；活库复查（probe §8）processed_files=1、chunks=9。管线时间自洽：stored_files created 09:58:36Z → fixture step 17:59:22（≈46s，与"48s"口径相符）。celery 日志本体未归档（LOW，DB 产物已足证）。

**纠正提交 ✗（MEDIUM-1）**：§5 attempt10 行"calibration_runs 1 + memory_corrections 1（纠正提交服务端落账）"不成立——
- archived json 内 memory_corrections/calibration_runs 两查询均为 `__error__`（列名不存在），实现侧从未见过真实行；
- 活库（probe §4）：memory_corrections / stuck_journey_corrections / understanding_calibration_runs 三表当日全部 **0 行**；
- attempt10 console 变更端点清单：仅 `/experience/stuck-journey/start` + `/answer`，**无 `/correct`、无 action-proposals**——纠正提交在 attempt10 面上是 UI 层动作（步骤 note "scope cards visible=true" 如实），服务端无落账；实现侧后续 commit 0278618f 亦自证"仅本次不写 memory_corrections=语义一致"。
- 服务端落账的真例在**种子面**：action_proposals `ecf15f20`（pilot，COMMITTED，payload estimated_minutes=30，13:05:05）与 `ec5521f1`（attempt2，COMMITTED，15，16:09:08）——probe §5 活库亲验。种子任务 `cab05cd4` 现 estimated_minutes=15（attempt2 合法覆写，§5"30（commit 版本）"为采集时点值，payload 链可复原）。

**video 合成口径 ✓（附 LOW-3）**：两个 manifest 均如实披露"引擎 RepaintBoundary 抓帧+物理录屏黑帧 probe 实证+mtime 墙钟合成+帧内容零加工"；`r1_attempt10_part1.mp4` sha256=`002e98d2…` 与 run_manifest 完全一致（亲算）；frame_count=24 与 raw 帧数一致；attempt10 帧序列逐帧 hold_seconds 披露。LOW-3：manifest 写"timeline=real wall-clock"，实际单帧 hold 封顶 30s → 视频总长 364s vs 真实墙钟 653s（压缩墙钟），出处声明宜补一句 hold-cap 披露；不构成冒充实拍（从未声称物理录像，limitations §1 已如实降级 L3）。

### 靶2 反例本体核验 —— PASS_WITH_CHALLENGES

**僵尸 run 行 ✓**：活库（probe §1）与 archived db 文件逐字一致：`9ff03120`（18:04:14，q01up874775）、`a77f9eb0`（18:14:06）、`57f4a41f`（18:41:03，q01up083360），均 RUNNING/prep/trace=hybrid_journey，updated_at-created_at≈20ms（prep 后即挂）。

**锁级机制 ✓（补 LOW-1）**：limitations §2 的 pg_stat_activity 叙事无 raw 留痕（证据目录 grep 仅命中文档本身）——但本审查活栈复现（probe §2）：多条 `idle in transaction` 会话末语句确为 `SELECT user_push_opt_in…`，且多条 `active|Lock` 会话阻塞在 `SELECT agent_runs…` 上，其中两条 backend_start 可溯源至 attempt10 时代（09:57:30/09:57:40Z）——挂死事务与锁链**至今仍活**。机制叙事为真，缺的只是留痕（本次 probe 已补）。

**台账失实两处（MEDIUM-3）**：
1. limitations §2 表把 `a77f9eb0` 记为 q01up054542（r4 用户）——DB 事实：其 task_id `2ea9fe0c` 属 **q01up874775**，r4 用户（q01up054542）的 db 证据 agent_runs=**0** 行。`a77f9eb0` 是同一用户（attempt10 用户）的第 2 次 POST（18:14:06，与 §2"第二次 POST 实测复现阻塞"互证）。
2. diff §4 "r4：hybrid 503（G6 第二例）"无证据支撑：archived r4 console（6666 行）Q01_STEP 止于 `task_execution_open`，`journey/hybrid` 请求数=**0**，后接 flutter_tools 崩溃。
   → 按被审证据口径，G6 反例实为 **3 次 POST / 2 个独立用户**（874775×2 + 083360×1），非"3/3 用户"。

**强度结论**：缺陷定性（产品级挂死，非环境抖动）依然成立且更强——prep 均 4s 内真实命中 9 chunks 文档后挂死；run 行 20ms 后永停；锁链被本审查活栈复现；且审查窗口内并行会话 r8/r9 又新增 2 例（`20770aed` q01up981034 19:26、r9 用户 q01up980549 19:39，probe §1/§2），累计 **5 次 POST / 4 个独立用户 / 同一产品 sha**。

**"网关 503"措辞（LOW-2）**：全部 archived console 的观测失效面是**客户端 30s receiveTimeout 中止**（attempt10 duration_ms=30098、r5=30276，status_code=null），未见任何被捕获的 503 响应；gateway 代码确有 `RequestTimeout: 30s`（network_resilience.go:77），"网关 30s 超时→503"是合理推断而非被记录的观测。FIX-583 卡面宜以"30s 无响应超时（客户端中止实测；网关 30s 上限代码在位）"表述。

### 靶3 三证对齐抽查 —— PASS（附 LOW-3 标注修正）

抽 2 份语义树交叉：
- `semantics_r1_part1_task-execution.txt`：头部 ts=**18:02:10** = attempt10 `task_execution_open` 步骤时刻——即 attempt10 **本体**证据（非 §5 标注的"pilot 同构面"，实际比标注更强）；内容"Map the baseline / 预估时间：25 分钟 / 00:25:00 / 卡住了?"与 DB tasks 行（STUCK，25min）逐字一致。
- `semantics_r1_part1_hybrid-judgment.txt`：ts=18:08:30 = attempt10 `hybrid_judgment_stage` FAIL 时刻；内容"一起推进：备料·你研判·交付 / Failed to start hybrid journey / 重试"与帧 `22-hybrid-judgment.png`（亲阅）与 console Q01_TEXTDUMP[hybrid-judgment] n=60 三向逐字一致。
- 附加核对：root 级 `committed`/`diff-review` 树 ts=17:19:07/18:04:06——前者实为 **attempt6** 遗留（其 commit 有 proposal `c9ce8541` COMMITTED @17:18:51 背书，probe §5），后者为 attempt10 的 FAIL 态现场；§5 标"pilot 面"不准——pilot 本体副本在 `raw/pilot_r1/semantics_r1_part1_{diff-review,committed}.txt`（ts=13:05:11/13:05:20 ✓ 存在且与 pilot steps 一致）。`home-seeded`（17:51:39）为 attempt9 遗留、未被引用。
- 帧数：attempt10 raw 帧 24 = manifest frame_count 24 ✓。

### 靶4 token 用量账 —— PASS_WITH_CHALLENGES

**数字精确成立**：活库复算（probe §3）——claim 时点存在的 5 个 q01up 用户（350302/370599/874775/054542/083360）各 2 次调用：2730+2749+2800+2787+2670 = **13,736** tokens / 10 calls，与 §6/run_manifest 逐位一致；"与同栈舰队共享日志流、不编造每卡 token"的红线守住了。

**但机制归属失实（MEDIUM-2）**：
1. §6"向导意图分析、恢复旅程澄清问、Hybrid prep 检索均为真实 LLM 调用"——代码证伪：向导意图分析 `goal_intent.py:132` 自述 "Rules-based intent analysis (≤60s budget, **no LLM**)";澄清问 `stuck_journey_service.py:10` 自述 "diagnose_friction，**LLM 0 次**";Hybrid prep = 注册工具 `retrieve_user_material` 真实检索（工具非 LLM；LLM 在后续起草段，未到达）。计划预览 `decompose_goal_preview` 调 `goal_decomposition_service.preview()` 纯确定性服务。driver 步骤注记 "real LLM intent analysis returned=true" 为**失实注记**。
2. 13,736 的真实构成（probe §3b）：每用户 2 次调用时刻=17:58:26/17:58:41——**persona onboarding 会话轮次**（dashscope_fast），非向导/澄清/Hybrid。
3. "明细在 db/*_db_evidence.json"——被审的 5 份 archived db 文件 token_usage 查询全部 `__error__`（r8 起脚本才修复），该句对被审证据不成立。
结论：数字不假、红线未破；但"真模型"叙事须更正为——本卡实测 LLM 调用=persona 会话轮（已计量）；向导意图/计划/澄清问=确定性服务（代码锚如上）；Hybrid 起草 LLM 未到达。

### 靶5 挑战①-⑤ 复核（⑥ leader 已裁决，本审无异议）

| # | 实现侧预登记 | 本审裁决 |
|---|---|---|
| ① | G6 反例充分性 | **事实层充分，可立 FIX-583**（建议含"僵尸 run 补偿"+"扇出移出请求事务"两子项）；组件层"通知/推送扇出嫌疑最大"只能作假设写入（无栈证据），FIX 卡内应含根因行级定位步骤。审查窗口内新增 2 例（r8/r9）进一步加固。 |
| ② | 同版本 3 重复口径 | **接受"产品同版本+失败全保留"口径**：git diff 5cbc715f→HEAD 在 mobile/lib、backend/、proto/ 为空（亲验），12+ 轮产品码逐字节一致；driver 为披露的度量基建。 |
| ③ | fixture 路径合规 | **接受**：经 app 自身会话走真实上传管线（prepare→MinIO→confirm→celery 分块），DB 产物（stored_files processed+9 chunks）亲验，无手插 DB；披露如实。否则 Hybrid prep 永远诚实 no_materials，旅程不可闭环——"前置条件等价物+披露"正确。 |
| ④ | 回执腿验证面 | **裁决：机制已验、投影缺口另立产品卡**。种子面 3 例服务端 COMMITTED（pilot 30、attempt2 15、attempt6 15）为机制铁证；向导面被 G5 挡住=r5 实测仍 null。（参考：审查窗口后 r8 已在向导任务面走通 commit——13fc4bd5 COMMITTED 19:26:05，属后续证据，不入本次判定。） |
| ⑤ | L3 录像语义 | **接受为 L3**：黑帧 probe 实证+出处 manifest+帧内容零加工+sha 可复算；条件：manifest 补 hold-cap（364s vs 653s）一句披露。不接受"原生操作录像"字样，现文本未用，合规。 |

### 靶6 value=FAIL 判定正确性 —— PASS

`v4/06_evaluation/EVALUATION_PROTOCOL.md:30`："Q任务的implementation可完成，value verdict仍FAIL；终门读取后者"——与 review_receipt.json（PENDING_INDEPENDENT_REVIEW、verdict=FAIL）及 tasks.json 卡（status=REVIEW_READY、evidence_verdict=FAIL）一致。scope_and_denominator（3 腿 PASS、1 腿 partial、3 腿被产品缺陷阻断）与证据吻合，无拔高。

### 靶7 可复测性 —— PASS

栈活：50051/8000/8080 全开放，uvicorn/grpc/gateway/celery 进程在位；运行中 gateway 二进制 sha256=`711997d0…` 与 manifest 一致（亲算）。本审查全程 SELECT-only，未触发任何 hybrid start。审查窗口内并行会话 r8/r9 自行新增 2 例僵尸 run（20770aed、r9 用户），佐证缺陷持续在现。

---

## 2. FIX-583 / FIX-584 归属确认

- **FIX-583（G6 hybrid start 挂死）：归属确认，产品缺陷成立。** 事实层：5 次 POST / 4 独立用户 / 同 sha 5cbc715f，100% 超时，run 永久 RUNNING/prep（updated≈created），prep 均 ~4s 成功后挂；锁链活栈复现（idle in transaction @ user_push_opt_in 末语句 + agent_runs 查询 Lock 等待）。组件层（扇出假设）须随卡补根因定位。
- **FIX-584（G5 校准投影缺口）：归属确认，产品缺口成立。** baselineMinutes=null 在向导直达执行面复现（r1/r5），r5 水化绕道后仍 null（疑投影按 today 过滤）；hasAnchor 门不出假入口属正确设计，缺口在读侧投影口径，须产品裁决（过滤 vs 水化时机）。

## 3. 挑战分级汇总

| 级别 | 内容 | 处置 |
|---|---|---|
| MEDIUM-1 | §5 attempt10 "calibration_runs 1 + memory_corrections 1（服务端落账）"无 DB 支持（三表当日 0 行；无 /correct 调用；archived 查询全 error） | 闭账 commit 更正 §5 该格：attempt10 纠正=UI 层 PASS、服务端落账仅在种子面（proposals 铁证） |
| MEDIUM-2 | §6 LLM 机制归属失实（意图分析 no-LLM、澄清 0-LLM、prep=工具；13,736 实为 persona 会话轮；"明细在 db/*.json"对被审证据不实） | 闭账 commit 按 §靶4 事实更正表述；步骤注记 "real LLM intent analysis" 随 driver 修正 |
| MEDIUM-3 | G6 台账：a77f9eb0 误记为 r4 用户（实为 874775 二次 POST）；r4"第二例"无证据（console 0 次 hybrid 调用）；"3/3 用户"应记"3 POST/2 用户（审查时点）" | 闭账 commit 更正 limitations §2 表与 diff §4 r4 行 |
| LOW-1 | pg_stat_activity 锁证据无 raw 留痕 | 本审查 probe 已补（raw/review_r1_probe_20260929.txt §2），随证据入库 |
| LOW-2 | "网关 503"为推断，实测观测=客户端 30s receiveTimeout 中止（网关 30s 上限代码在位） | FIX-583 卡面措辞按此校正 |
| LOW-3 | 零散：root 语义树 committed/diff-review 面源标注（实为 attempt6 遗留/attempt10 FAIL 态）；attempt10 实为 17 PASS/5 FAIL（自报 16，保守少计）；video 364s vs 墙钟 653s（hold 封顶 30s 未明示） | 闭账 commit 顺手更正，不动结论 |
| INFO | 双会话交叠持续：审查窗口内出现 9753e0db/31875991/72e7a826/0278618f 四个后续 commit 与 r6-r9 运行（均 test/evidence-only，产品码 5cbc715f→HEAD 逐字节一致亲验）；r8 证据由实现侧自证"仅本次不写 memory_corrections"，与本审 MEDIUM-1 相互印证 | 按 leader 挑战⑥裁决办理；本审锚定 12b3bdba |

## 4. 闭账判定

**Q01 可闭账：value=FAIL 如实记录，终门读 FAIL。**
闭账前置（文档更正，不需新运行）：MEDIUM-1/2/3 三处更正落入闭账 commit（可附于本 review commit 之后的 evidence-only 提交）；FIX-583/584 按第 2 节归属立卡（583 含僵尸 run 补偿与根因定位子项）。
