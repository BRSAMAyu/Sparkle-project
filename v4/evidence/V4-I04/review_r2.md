# V4-I04 整改复审 receipt（独立审查 R2）

- **审查会话**：wtI04R2（未参与 I04 实现、一审与整改）
- **审查对象**：branch `agent/v4/i04`，HEAD `74626753`（实现 `2be0be2a` → 一审 receipt `1c10361a` → 整改 `74626753`；处置全文 `remediation_r1.md`）
- **审查日期**：2026-09-28
- **方式**：只读审查 + 独立复跑 + 结构性 grep + mutation 亲证（全部变异 `git checkout --` 还原，终态两改动文件 sha256 与 commit `74626753` 版本**逐字节一致**）+ 语料外边界探针
- **总裁决**：**PASS——一审四项跟进闭环成立，建议销账（DONE_REVIEWED 口径达成）**。无新增 CHALLENGED。一审 PASS_WITH_CHALLENGES 的 4 项非阻塞挑战全部以「代码/测试 + mutation 自证 + 文档同步」方式闭环，闭环质量复核通过。

---

## 复审靶 1 · F-1 闭环核（最重项）— **闭环成立**

### 1a. `_answer_turn` 单点门：shadow 只观察不行为的**结构保证**

- 亲读 wiring 现码：marker 行为（`_skip_turn`/`_pause_turn`）的唯一调用点在 `friction_chat_wiring.py:402/407`，双双位于 `if correction_mode == "live":`（:399）分支内——`grep -n "_skip_turn\|_pause_turn"` 全文件仅此两处调用 + 两处定义，无旁路。
- 第二问压制（同型第二处）：`budget_declared_replay`（:503）+ 注记/斜坡现在整体收在 `if correction_mode == "live" and diagnosis.outcome == "ask":`（:498）内；shadow 走 `elif`（:513）只发 metric + 日志，**不替换 diagnosis、第二问照常出面**。
- shadow 分支（:410-424）只构造观察 dict（kind/marker/applied:False）+ `_record_correction_metric("marker_observation","shadow")` + 结构化日志；随后该观察经 `_with_shadow_marker_observation` 注入三条出口 annotations（weak/unresolved/answered，:451/:467/:493）。**不清 pending、不产 no_action、不出斜坡、不压制第二问**——四条红线在代码路径上逐一核对成立。
- off：词表零接触（`== "live"`/`== "shadow"` 显式双分支，无 `!= "off"` 兜底触发 marker 行为）。

### 1b. mutation 亲证（本会话独立执行）

| 变异 | 结果 |
| --- | --- |
| 变异①：仅 :399 `== "live"` → `!= "off"`（marker 行为不限 live） | `test_shadow_mode_marker_sentence_keeps_pending` **FAILED**（`assert 'ask' == 'no_action'`——shadow 下「先暂停一下」清 pending 转 no_action，泄漏复现）；1 failed / 38 passed |
| 变异①+②（叠加 :498 `== "live"` → `!= "off"`） | **2 failed / 37 passed**——与 remediation_r1.md 自证数字**逐字吻合** |
| 变异②单独（仅 :498） | 两个新 shadow 测试**均红**（marker 测试第三轮断言「结构化回答后第二问照常出面」同样咬住压制面——交叉钉，双测各覆盖两条红线） |
| 还原 | `git checkout --` 后 `git diff 74626753 -- wiring` 空、sha256 与 commit 版本一致、**39 passed** 复绿 |

整改声明的「还原 wiring 修复 → 2 failed/37 passed → 复原 39 绿」**独立复现成立**。

### 1c. 「同型第三处」排查（全仓 grep）— **无第三处**

- `budget_declared_replay` 全仓（app/）仅 2 个调用点：wiring :503（live 门内）+ :575（`_skip_turn` 方法体，而该方法唯一入口是 live 分支）。
- `match_skip_marker`/`match_pause_marker` 全仓消费仅 wiring :400/:405（live 应用）与 :411/:412（shadow 观察），无其它模块调用。
- `NO_ACTION_CORRECTION_MODE` 全仓唯一消费面 = wiring 模块（settings 定义 + 模块 docstring 提及除外）。
- 其余 `correction_mode != "off"` 三处（:529 纠正追踪 / :705 free_supplement 追踪 / :742 补充入口）逐一核对：均为 shadow 档**只算 metric+日志、不 attach 载荷**（`base.correction_trace`/`supplement_entry` 仅 live 赋值）——观察面，非行为面。
- 域外同名物：`app/aurora/runtime_v1/telemetry.py` 有私有 `_SKIP_MARKERS`——本分支零触碰（`git diff be495611..74626753 -- runtime_v1/` 为空）、不经 correction mode 门，属 V1 遥测既有面，**不构成本卡 shadow 面的第三处同型**（登记为事实澄清，非缺陷）。
- 两个新 metric surface 值（`marker_observation`/`second_ask_observation`）走同一 `AURORA_NO_ACTION_CORRECTION_TOTAL{surface,mode}` 计数器（metrics.py:797，标签维度制、无冻结枚举）——与 remediation「surface 新增两值，同计数器」一致。

### 1d. `applied:false` 注记可审计性 — **成立**

链路亲核：`annotations` → `FrictionWiringOutcome.to_dict()`（:255）→ orchestrator `state.context_data["friction_decision"]`（orchestrator.py:2840）→ `response_metadata["friction_decision"]`（response_builder.py:1261-1263 json 序列化）。即 shadow 档 marker 命中的 `{kind, marker, applied: false}` 随 response metadata 与 checkpoint 持久，事后可审计「live 将做什么/本档未做」。测试侧 `shadow_annotations.pop("shadow_marker_observation")` 后与 off 档**逐项恒等**断言 + observation dict 精确匹配（`{"kind":"pause","marker":"暂停一下","applied":False}`）双钉。

## 复审靶 2 · F-4 非空样例断言真咬合 — **成立（伪造/丢引用均变异变红）**

- 独立引擎重放：`apply_free_supplement("真的做不下去了，最近状态很差", spine_state_keys=("crisis_mode",))` → `diagnosis.evidence_refs == ('signal://crisis_mode',)`（非空，非测试自证）；旗舰样例 `不是不会，是不知道怎么开始` → 三处确为空 `() / [] / []`——整改对空集事实的描述**如实**。
- 三处恒等断言（诊断 passthrough / `experience["evidence_refs"]` / `trace["basis"]["evidence_refs"]`）+ 逐条封闭 scheme（`signal`/`user_state`）在测，且本会话变异实证：
  - 变异 A（experience 伪造一条 `signal://forged_key`）→ `test_apply_free_supplement_propagates_nonempty_engine_evidence_refs` **FAILED**；
  - 变异 B（trace basis 引用置空=丢引用）→ 同测 **FAILED**；
  - 还原后 sha256 与 commit 一致、套件绿。
- 旗舰样例改显式空集断言（`diagnosis.evidence_refs == ()` + experience/trace 同空）——「零伪造」从隐含转显式。生产代码零改动（引用本就是 passthrough），与一审 R4 口径一致。

## 复审靶 3 · R2 否定前缀守卫 — **成立（3 条指定边界 + 封闭性 + 宁漏报方向均亲测）**

- 指定 3 条：`别停一下` → **None**；`先暂停一下` → **「暂停一下」命中**；`don't skip` → **「skip」（英文否定不在守卫域——登记边界如实，测试钉同向）**。
- 封闭集：`MARKER_NEGATION_PREFIXES` 实测 15 成员、全部 ≤2 字、frozenset；`test_marker_negation_prefixes_frozen_closed_set` 钉子集 + 窗口契约。
- 宁漏报方向复核：守卫只看命中 span 前 1-2 字窗口、命中即作废该出现（fail-closed = 漏报向）——与「误清 pending/误静默代价高」的裁决一致；`_match_marker` 同 marker 多出现逐一判前缀，实测 `别跳过，跳过就直说` → 第二处纯出现**照常命中**（不因首处被否定而整 marker 作废，符合声明）；成员否定词本体不误杀（`这个先不用问了`→`不用问了`、`不想回答`→命中）。
- 语料外追加探针：`我不想跳过，但先别停一下` → 双 None（窗内复合否定全灭，漏报向）；`请先不要跳过这一题` → None（窗内）；`不是不想回答` → None（双重否定 fail-closed）。
- 残余边界如实：`我不会去跳过的` → 仍命中（否定词与 marker 间隔 >2 字窗不识别）——与 limitations §4 ②登记完全一致（该残余即一审 R2 既有过报面的收窄后余量，方向已声明）；limitations.md §4 已同步更新（diff 核实）。

## 复审靶 4 · 勘误 — **数字与措辞均核销**

- **880 加和**：77+49+76+118+208+352 = **880**（复算一致）；`diff_or_evidence_only.md` 交付物索引已改 880 并注明以明细为准；`test_results.json` 明细与整改后 `rectification` 块自洽。
- **「行为级零差量」措辞**：settings.py:966-970、wiring 模块 docstring/`_correction_mode` docstring、off 档测试 docstring 四处已同步收敛为「行为级零差量（version 串 v3→v4 与 3 个 null 键除外）」——与代码实测差量面**逐项吻合**：`version` 为 `FRICTION_CHAT_WIRING_VERSION` 常量（v3→v4），`to_dict()` 新增键恰 3 个（`supplement_entry`/`exit_ramp`/`correction_trace`，:252-254，off/shadow 恒 None）。
- 附带核实：`run_manifest.json.artifacts_sha256` 六文件逐一重算**全部匹配**；`review_r1.md`/`review_receipt.json` 在 `1c10361a..74626753` 间**零改动**（整改未动一审 receipt，声明属实）。

## 复审靶 5 · 复跑（2026-09-28，env `SECRET_KEY=ci-test-key DATABASE_URL=sqlite://`，主检出 .venv 解释器）

| 面 | 结果 |
| --- | --- |
| 新测 39 + I03 77 + I09 49 + wiring 76（单命令） | **241 passed** |
| contract 全量 | **352 passed** |
| A-03/J-05/A-05 相邻 + orchestration 全量 | **326 passed**（118+208） |
| 合计 | **919 = 880 回归 + 39 新测**，与整改 receipt 一致 |
| mypy 改动文件 | `no_action_supplement.py`/`friction_chat_wiring.py` **0 errors**（import-follow 带出的 30 条全部命中其它文件，改动文件名 grep 零命中） |
| mypy 棘轮（`scripts/ci/mypy_ratchet.sh`） | **53 / baseline 77**——与整改声明数字一致（零新增；test_results.json 原始 summary 块记 55 为实现时点值，方向同为 ≤ 棘轮，非矛盾） |
| ruff + black（4 个改动代码文件） | **全部通过**（black line-length 120） |
| 真实模型调用 | 0（全链确定性重放/fakeredis，本审亦零调用） |

零删除既有断言核实：整改 diff 中唯一被替换的断言是 F-4 的 vacuous 空转循环——替换为**更强**的显式断言组；其余测试改动均为新增或 docstring 勘误。

## 复审靶 6 · 合并落差预判 — **零冲突面（origin/main 已推进至心跳#7）**

- base `be495611`；`origin/main` 现 HEAD `934b420c`（心跳#7：CI36 三漏修复 + I08 销账 18/58；含 I08 双审合并线、CI36 契约补课）——较一审审查时（`71553984`）又前进多提交。
- **main 侧改动面**：docs 自托管静态资产、runs API/run_steps/agent_run_service、gateway models/schema.sql、I08 新测文件——与本卡改动面（`no_action_supplement.py`/`friction_chat_wiring.py`/`settings.py` 注释/`test_no_action_supplement.py`/v4 evidence 目录）**零交集**；`git log be495611..origin/main` 对 I04 三文件**空**。
- **试合并（`git merge --no-commit --no-ff origin/main`）**：自动合并成功**零冲突**（唯一双面文件 `v4/04_tasks/tasks.json` 自动合并通过）；已 abort，终态 worktree clean @ `74626753`。在航卡交集预判：I08（已并入，未触碰本卡文件）与 CI36（迁移/OpenAPI 面）均不与本卡摩擦；后续若心跳#8 落点仍为 state/tasks 文件，同此结论。
- **摩擦面函数级预判**：main 侧零提交触碰 `friction_chat_wiring.py`/`no_action_supplement.py`/`test_no_action_supplement.py`——无语义冲突候选。

## 结论

一审四项跟进的闭环质量逐项复核通过：F-1 以 `_answer_turn` 结构单点门把 marker/第二问压制的**行为应用收口 live-only**，shadow 只留可审计的 `applied:false` 观察注记，全仓 grep 证无第三处同型，mutation 亲证与整改声明数字逐字吻合且还原字节级；F-4 非空样例让三处恒等断言真咬合（伪造与丢引用均实测变红）；R2 守卫 15 成员封闭、1-2 字窗口、宁漏报方向与三条指定边界全部亲测吻合，残余边界如实登记；勘误两处（880 加和、行为级零差量措辞）与代码/明细逐字对账。复跑 919 全绿 + mypy 棘轮 53/77 + ruff/black 零新增。合并落差零冲突面（main 已至心跳#7 仍零交集）。

**总裁决：PASS——I04 可销账（DONE_REVIEWED）。无新增 CHALLENGED。** 一审 R1 遗留的两项观察（经验记录接线归记忆 owner 卡、`V4_AUTO_CLARIFICATION_BUDGET` 声明常量）维持原登记不重开；本审新增观察仅 1 条非阻塞事实澄清（runtime_v1 telemetry 私有 `_SKIP_MARKERS` 为域外既有面，勿与本卡 shadow 面混淆），无需行动。
