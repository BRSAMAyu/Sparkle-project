# FIX-562 独立审查 receipt（R1）

- 审查人：wtF562R1（独立会话，未参与 FIX-562 修复实现）
- 日期：2026-09-29
- 对象：`fix/v4/f562-spark-selfreport` @ `9cb9d961`（基线 `04b97fbe`，审查时工作树干净）
- 环境：共享 venv Python 3.11.15 / pytest 9.0.2 / mypy 1.20.2 / ruff 0.15.8 / black 26.3.1，`SECRET_KEY=ci-test-key DATABASE_URL=sqlite://` 全程（conftest `db_session` 钉 sqlite：`tests/conftest.py:300-305`）

## 总裁决：**PASS_WITH_CHALLENGES**（修复成立，缺陷可闭账；1 项挑战级发现 F-1 + 2 项观察 O-1/O-2 须随闭账登记）

FIX-562 的核心主张——**spark 客户端自报 outcome 融合面封死（三层：路由降级 / fuse_mastery 跳过 / 账本重放 real 过滤跳过）+ fail-closed 拒绝门**——实现与测试两面均亲证成立且可失败（mutation 亲放 3 红）。裁决复核成立：缺陷非钉现状。发现 F-1 不推翻修复，但闭账时须登记（见 §F）。

## A. 裁决复核（首靶）：成立

四证据逐条亲读：

- **证据 A（设计真源）**：`v4/03_intelligence/DATA_AND_GRAPH.md:21`——「独立测验/修正过的练习证据才能支撑相应能力描述」；`:21`「成就光子与 sprint 排行只读其原账本」。客户端自报 quiz 无账本条目、无物化、无服务端核验，非独立检验。✓
- **证据 B（契约自相矛盾核）**：`git show 04b97fbe:backend/app/api/v1/galaxy.py`（spark_node 体，基线 :444-448 区域）——`evidence_type=MasteryEvidenceType(request.outcome.evidence_type)` 客户端可控直传融合；对照 `backend/app/schemas/galaxy.py:84`「self_report 永远不接受为 outcome——自评走独立通道，不与测验混算」。declared intent（自报不得当 outcome）≠ behavior（客户端自封 quiz 名义即按 quiz 融合）。矛盾核成立，判缺陷有据。✓
- **证据 C（D04 卡面语义）**：`backend/app/services/galaxy/capability_channel.py` 模块 docstring「在关系型主星图中接**有效** outcome：有效 = D-02 账本真相面 × D-03 撤回投影」——该面客户端 outcome 无真相面。✓
- **证据 D（一审 F-2）**：`v4/evidence/V4-D04/review_r1.md:54-55`——定性「通道纪律的旁路面」，处置建议第一选项即「API face 通道化：客户端 outcome 一律 PRACTICED」。本修法正是该选项。✓

**边界裁决合理性**：「SELF_REPORTED→PRACTICED 静态映射是有意保守不动」成立——封闭词表 docstring 明文（capability_channel.py 模块头）「自报完成……可解锁（参与足迹可见）、可留溯源，**永不**推进掌握度后验」；词表无缺陷，缺陷在路由绕过 `classify_outcome_channel`。修法未新增枚举值（`CLIENT_SELF_REPORT_CHANNEL` 是 `TRUTH_CLASS_CHANNELS[TruthClass.SELF_REPORTED]` 的等价引用常量，capability_channel.py:120），封闭四值与 `CAPABILITY_CHANNEL_SCHEMA_VERSION` 均未动——是尊重封闭词表纪律的正确选择。✓

台账行亲读（`v3/06_agent_fleet/DYNAMIC_ISSUES.md:430`）：修法=台账第一选项逐字落地。✓

## B. 修法行为面：亲证成立

- **三层封死亲核**（读码锚）：
  1. 路由降级：`backend/app/api/v1/galaxy.py:448`（`evidence_type=MasteryEvidenceType.SELF_REPORT`）+ fail-closed 门 `galaxy.py:442-447`（判 VERIFIED 即 422）；
  2. fuse_mastery 跳过：`backend/app/services/galaxy/mastery_evidence.py:246-251`（SELF_REPORT「recorded for observability, never fused」，只增 self_report_count）+ 权重表 `:87`（0.0）+ `REAL_EVIDENCE_TYPES` 排除（`:93-100`）；
  3. 账本重放跳过：`mastery_evidence.py:362-366`（replay `real` 过滤只吃 REAL_EVIDENCE_TYPES）+ `_load_prior_belief` 对 EVIDENCE kind 行回环 `classify_audit_reason("evidence:self_report")→SELF_REPORT`（`mastery_evidence.py:527-530`）后仍被 real 过滤排除——「账本重放跳过」主张成立，重复 spark 先验不漂移。
- **mutation 亲放**：临时还原缺陷行为（`SELF_REPORT → MasteryEvidenceType(request.outcome.evidence_type)` 并中和拒绝门）→ `pytest tests/api/test_fix562_spark_selfreport_channel_gate.py -q` → **3 failed**（正例融合钉 / 反复自报不可达 mastered / 拒绝门 422 钉）+ 1 passed（服务级对照）；还原后复绿。manifest 报 2红 因其 mutation 只改降级行不动门；本审加中和门后 3 红，正反两面均可失败结论不变。探针已还原（`git checkout --`），工作树干净。
- **fail-closed 422 亲跑**：`test_channel_authority_drift_refuses_claim` 单跑 passed——monkeypatch `galaxy_api.CLIENT_SELF_REPORT_CHANNEL=VERIFIED` → 422 且零审计行（`:195-196`）；与 unit 权威钉测（等价引用词表，test_capability_channel.py:266-274）合成「词表+门」双钉。
- **调用面旁路普查**：`grep -rn "EvidenceObservation(" backend/app` 全库仅 2 构造点——本路由（已封）与 `outcome_absorption_service.py:241`（G-02 吸收器，读 D-02 账本服务端权威）。无其他客户端可控融合面。✓

## C. D04 契约零削弱：亲证成立

- **additive 亲 diff**：`git diff 04b97fbe..9cb9d961 --stat -- backend/tests/` = 2 文件 **229 insertions(+) / 0 deletions(-)**；对既有 D04 测试文件零删改。✓
- **121 项亲跑**：`pytest tests/unit/test_capability_channel.py tests/services/galaxy/test_outcome_absorption.py tests/services/galaxy/test_outcome_absorption_channels.py tests/services/galaxy/test_spark_activity_trace_and_capability_labels.py tests/services/galaxy/test_mastery_evidence.py tests/services/galaxy/test_mastery_effect_kind_replay.py tests/services/galaxy/test_stats_service.py -q` → **121 passed**。✓
- **穷举面**：未新增枚举值（见 §A），封闭四值穷举测（`test_channel_vocabulary_closed`）不受影响；新常量有专钉。✓

## D. 调用方普查：亲证成立

`grep -rn "\.spark_node(" backend/app` 共 8 点，生产调用方 5 内部 + 1 REST + 1 委托 + 1 吸收无关：

| 调用点 | outcome |
|---|---|
| `app/api/v1/galaxy.py:453`（本路由） | 有（已被本修复封死） |
| `app/api/v1/subtasks.py:133` | 无 |
| `app/services/galaxy_grpc_service.py:453`（gRPC RecordNodeInteraction） | 无 |
| `app/services/task_service.py:781,804` | 无 |
| `app/services/galaxy/event_listener.py:130` | 无 |
| `app/services/galaxy/feedback_service.py:354` | 无 |
| `app/services/galaxy_service.py:2683` | 透传委托，无独立入口 |

mobile/gateway：grep 无 galaxy spark endpoint 调用方（mobile 命中均为 `sparkle` 包名/触觉品牌词；gateway 为通用代理）。**零现网调用方受行为变更影响**——manifest 主张成立。✓

## E. 机械门：亲证成立

- **OpenAPI**：`git diff 04b97fbe..9cb9d961 -- docs/contracts/openapi_snapshot.json` = 仅 2 条 spark endpoint description（`/node/` 与 `/nodes/` 同路由双别名），请求/响应 schema 零变化；`python ../scripts/check_openapi_contract.py` → passed exit 0（旧描述「走贝叶斯证据融合」描述的正是缺陷行为，再生合法）。✓
- **mypy**：分支与基线各 **34 errors in 32 files**，sort+diff 唯一差异 = `galaxy.py:977→993`（同一错误逐字、行号位移 +16，与文件净增行数一致）。零新增。✓
- **ruff**：4 改动文件 `All checks passed!`。✓
- **black**：新增 2 文件 clean；`galaxy.py`(3)+`test_capability_channel.py`(7)=10 hunks，基线同测 3+7=10——零新增漂移（既有漂移族，D04 审查 O-3 已披露）。✓
- **回归**：galaxy 全目录 **178 passed**；合并批（x08+j06+outbox+shield+wt392+fix562+channel）**47 passed**，与 manifest 分批口径 11+4+32 精确对账。✓

## F. 发现

### F-1（挑战级）：新测两处 `get_evidence_counts_by_node == {}` 断言经异常吞噬真空通过，且其语义主张与生产方言相反

- **现象**：`test_fix562_spark_selfreport_channel_gate.py:150` 与 `:175` 断言计数为空，注释称「自报不清 legacy 旗」。亲测探针（跑毕即删）证明：spark 自报后账本行为 `('evidence:self_report','evidence','obs=90.0;conf=0.9')`；将该函数 WHERE 原样复刻执行返回 `[(node_id, 1)]`；而生产函数返回 `{}`——根因是 `stats_service.py:784-795` 裸 SQL 直绑 `user.id`（UUID 对象），sqlite 下 `ProgrammingError: type 'UUID' is not supported`，被 `except Exception → return {}`（`:793-795`）吞掉。conftest 钉 sqlite（`tests/conftest.py:300-305`），故该断言**结构性**经吞噬路径通过。
- **语义面**：在能执行该查询的方言（生产 asyncpg 原生支持 UUID）下，自报行 `effect_kind='evidence'` + `reason LIKE 'evidence:%'` 双命中，计数 = 1 → `is_legacy_estimate=False`（`galaxy_service.py:2356-2360, schemas/galaxy.py:482`）。即测试注释「自报不清 legacy 旗」**在生产方言不成立**——若环境可跑，该断言会红。
- **影响定量**：仅展示诚实性面（legacy 旗误清：掌握度数值未动、能力标签面 `get_verified_evidence_counts_by_node` 的谓词只认 quiz/task_outcome 前缀+词表，self_report 不在内——标签封顶完好；奖励读的掌握度标量未动）。**相对基线零回退**：修复前客户端伪 quiz 行同样以 EVIDENCE kind 落库并清旗（且还融合）；D04 既有同类断言（`test_spark_activity_trace_and_capability_labels.py:139`）同样真空但「碰巧」与查询语义一致。
- **定性**：不动摇修复核心主张（融合三层封死与 F-1 无关），但断言作为「不清晰旗」的钉是无效钉+误导注释。
- **处置建议**（任选其一，后续小改即可，不阻断闭账）：(a) 自报观测行改写 `effect_kind=PROJECTION`（重放 docstring 本就把「client self-report syncs」列在 projection 族，`stats_service.py:594`）；或 (b) `get_evidence_counts_by_node` 谓词排除 `evidence:self_report`；同时修 UUID 绑定（GUID bindparam，与 G-02 吸收器同款纪律）并更正两处测试注释。

### O-1（观察）：自报观测行 effect_kind=EVIDENCE 的重放锚语义

自报行若为节点首条 EVIDENCE 行会冻结重放锚（`_load_prior_belief` EVIDENCE 分支）——语义无害（锚=融合前存量，自报永不融合，belief 恒等锚值），但若采纳 F-1 处置 (a) 则该面自然消失。

### O-2（观察）：台账修法第三项「成就光子发放改走通道判定」的处置口径

本修复未在成就引擎加通道判定，而是封死其唯一客户端可控输入面（自报融合），其余写入面均为服务端核验（error book / exam sprint = 真独立检验）或已披露存量（D04 limitation #7 / O-5）。缺陷后果链（自报→mastery≥80→NODE_MASTERED→光子）在第一环断链，定性成立；但闭账翻 FIXED 时应在行内备注「该项以『客户端可控面封死+其余写入面服务端核验/存量披露』口径处置」，避免后人按字面等一个不存在的成就引擎改造。

## G. 闭账口径（靶6）

台账 `V3-FIX-562` 行翻 **FIXED@9cb9d961** 的条件核：

- 修法第一选项逐字落地 ✓（§A）；一正一反反例 ✓（4 新测 + mutation 亲放 3 红，§B）；D04 契约零削弱 ✓（§C）；机械门全过 ✓（§E）；F-2 要求的「显式处置」由本 receipt 闭合计数 ✓。
- 附条件：翻账时行内登记 O-2 处置口径与 F-1 待办（F-1 可作后续小改卡，不阻断本缺陷闭账——其影响面为展示诚实性且相对基线零回退）。

## H. 结论

FIX-562 修复**成立且可失败**，缺陷闭环质量高于门槛：三层封死 + fail-closed 门 + 封闭词表等价引用（不破坏穷举）+ additive 契约。裁决 **PASS_WITH_CHALLENGES**：本审通过即满足闭账条件（附 G 节两项登记义务）；F-1 转后续小改。

- 复现锚：§B/§C/§E 各命令均为本轮真实执行（exit code 见文）；
- 探针（`tests/api/test_zz_probe_fix562_review.py`）跑毕已删，工作树干净。

- 审查人签名：wtF562R1 · 2026-09-29 · 本 receipt commit 于 `fix/v4/f562-spark-selfreport`（不 push）
