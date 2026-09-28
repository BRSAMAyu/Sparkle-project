# V4-I04 一审 receipt（独立审查 R1）

- **审查会话**：wtI04R1（未参与 I04 实现）
- **审查对象**：branch `agent/v4/i04`，HEAD `95db18d7`（实现 commit `2be0be2a` + evidence pin `95db18d7`）
- **审查日期**：2026-09-28
- **方式**：只读审查 + 独立复跑 + 语料外变体对抗亲测 + 变异测试（off 零差量反转实证；全部变异 `git checkout --` 还原，终态 worktree clean）
- **总裁决**：**PASS_WITH_CHALLENGES（一审通过，附 4 项非阻塞挑战/勘误登记）**。R1–R5 逐判：R1 PASS / R2 PASS_WITH_CHALLENGES / R3 PASS / R4 PASS_WITH_CHALLENGES / R5 PASS。无阻塞项；挑战项见 §挑战登记，均不要求本卡重开。

## 复跑记录（本会话独立执行，非转录；env `SECRET_KEY=ci-test-key DATABASE_URL=sqlite://`）

| 面 | 命令要点 | 结果 |
| --- | --- | --- |
| 新增测试 | `pytest tests/unit/test_no_action_supplement.py -q` | **33 passed** |
| I03 回归（必跑） | `pytest tests/unit/test_semantic_selector.py -q` | **77 passed** |
| I09 回归（必跑） | `pytest tests/unit/test_deterministic_lane.py -q` | **49 passed** |
| wiring 面（v3→v4 直接改动面） | `pytest tests/services/test_friction_chat_wiring.py -q` | **76 passed** |
| A-03/J-05/A-05 相邻面 | `pytest tests/unit/test_a03_friction_diagnosis.py tests/unit/test_j05_stuck_journey_migration_sqlite.py tests/unit/test_policy_patch_migration_sqlite.py -q` | **118 passed** |
| orchestration 全量 | `pytest tests/orchestration -q` | **208 passed** |
| contract 全量 | `pytest tests/contract -q` | **352 passed** |
| **回归合计** | 6 面 | **880 passed**（+33 新测 = 913；**勘误**：diff_or_evidence_only.md 写「6 面回归 660 passed」，与其自附 test_results.json 明细之和 880 不符——文档算术勘误，实际复跑全绿） |
| mypy 棘轮 | `mypy app/`（全仓） | **54 errors ≤ baseline 77**（零新增；与 evidence 记录 55 的 1 差为本机 mypy 版本/平台时点差，方向同为 ≤ 棘轮）；三改动文件 **0 errors** |
| ruff / black | 6 改动文件 | **全部通过**（black line-length 120） |

## R1–R5 逐点判定（实现方预登记挑战点）

### R1 「今天口径」约束模式覆盖边界 + `_UNIT` 修复真实性 — **PASS**

- **语料外变体亲测（审查指定 2 条 + 追加 9 条，全部实测）**：
  1. `每天就一刻钟` → **None（诚实 fail-closed）**：「每天」不在今日词表、「刻」不在单位表——且「每天」是周期口径，正确地**不**落 `expires_same_day=True` 的会话作用域记录。
  2. `周末抽空学一会` → **None（诚实）**：无今日词/上限词/数量/单位任一算子。
  3. 追加：`今天只有 45 min`（空格+min）→ **HIT**（`\s*` 允许空格，预登记的「空格」疑虑实测不成立）；`今日只剩十分钟左右` → HIT（中文数字+左右后缀）；`今天最多30分钟` → HIT（「最多」在限词表）；`就剩一下午了`/`只有俩小时`/`今天只有两小时`/`每天只有15分钟`/`我每周只有15分钟`/`每次只想学15分钟` → 全部诚实 None。
- **误分类后果方向核实**：全部漏报落在「少记一条会话作用域约束记录」（保守向，不产生错误归因、不写任何面）——与预登记的后果声明一致。
- **`_UNIT` 交替分组修复真实性：**复原复现**成立**。把 `_UNIT` 外层 `(?:...)` 去掉重拼三条模式后，`我每周只有15分钟` 在 pattern `quantity_unit_today_scope` 上**假阳命中**（span「只有15分钟」）——撕裂的 `|` 把 `_TODAY_SCOPE` 切进了第二分支，使 `_LIMIT_WORD+数量+分(钟)?` 单独成支不再要求今日词；修后同句 None。开发中发现并钉死的真 bug **属实**，`test_non_today_horizon_fail_closed` 是有效回归钉。

### R2 跳过/暂停词表复合句误伤面 — **PASS_WITH_CHALLENGES**

- **审查指定复合句 `以后再说，但今天先来十分钟` → marker=None（正确不误伤）**：「以后再说」不在 `SKIP_MARKERS`（词表只有 跳过/不用问了/别问了/先不答/不想回答/skip 系），该句正确流入分支解析面（pending 保持/结构化回答主路径），无误伤。
- **预登记的过报形态实测成立**：`不想跳过这题，让我再试试` → 子串命中「跳过」→ 走 `_skip_turn`：pending 清除 + outcome=no_action + trace(skipped=True) + 出口斜坡（reason=user_skipped_clarification，conservative=None）。**过报后果实测有界**：无锁聊天、无写路径、无不可逆效应，用户下一轮自由输入即恢复；代价是该轮回答未被解析、pending 被清（UX 级损失，可恢复）。
- **新增发现**：`别停一下` → 命中暂停词「停一下」（否定+暂停词同构过报）；后果同向有界（本域静默+可见追踪）。
- **判定**：过报方向可接受（normal risk + 词表冻结声明 + 后果有界）；**挑战登记**：否定前缀复合句收紧（整句匹配或否定前缀守卫）应作为后续词表变更过 reviewer 登记，不阻塞本卡。

### R3 「≤1 轮」作用域 — **PASS**

- **policy 原文核对**：AURORA_SEMANTIC_POLICY「澄清的判据」原文为「**预算初值**：自动澄清≤1轮；仍不清楚时允许『直接说情况/先给保守可试方案/先暂停』，用户主动补充不算系统追问」。「预算初值」措辞支持**每次决策点**读法；全局「每会话 ≤1」硬闸会挡住有证据的新摩擦事件澄清，恰是 FIX-49「降噪不关死」同律所禁。本卡解释（一次问对闭环内 ≤1；跨轮新事件可再问）与 policy 原文**一致**。
- **连环第二问压制实测（live 档）**：T1 `最近做不下去` → ask(q_tried_and_checked)；T2 结构化回答 → **第二问被压制**（annotations `suppressed_second_ask='q_content_vs_state'` + `exit_reason='v4_clarification_budget_exhausted'` + 出口斜坡出面、question 结构性 None）；与实现自带 `test_live_mode_suppresses_second_ask_with_exit_ramp` 互证。
- **跨轮新事件再问实测**：T2 消费 pending 后，T3 新正向词牌摩擦事件（`这个任务真的做不下去，卡死了`）→ **再次 ask**（新闭环新预算）；对照 off 档同序列 T2=ask（V3 第二问链保持）。
- **边界核对**：无效 branch_key 回答 → `unresolved_pending_kept`（V3 行为，非问句出面，无压制矛盾）；`V4_AUTO_CLARIFICATION_BUDGET=1` 为**声明常量未被 wiring 消费**（压制是 answer_replay 链内结构性的，功能上等价 ≤1/闭环）——观察项登记，非缺陷。

### R4 「形成合法经验」口径 — **PASS_WITH_CHALLENGES（口径接受，缺口强制登记）**

- **判定面核实**：结构合法可撤回契约记录属实——`scope=session`、`retractable=True`、`permanent_preference_write=False`、`downstream_legality=memory_gate`；写授权空集 `SUPPLEMENT_WRITE_SURFACES == frozenset()` 有 import 期断言（模块尾）+ 测试冻结双层钉死。
- **「没接线」如实登记核实**：limitations.md §1 明确「写入面未接线（本卡边界内决定）……写入 self_model/experience_memory 并过 I02 效用门属记忆 owner 卡面」，并给出审查否决时的升级路径（独立记忆接线卡）。全链无一处声称经验已入长期记忆——**无夸大声明**。
- **接线面缺口（挑战登记）**：`apply_free_supplement`（经验记录唯一生产点）**零运行时消费者**（grep 核实：app/ 内无调用）；wiring 的自由补充面（`_fresh_turn`）产出 trace+constraint+guard 但**不产出 experience 记录**——纠正行为已接线（FIX97 入口 + fresh 轮重放），经验记录是契约层资产。
- **测试弱点**：`test_apply_free_supplement_without_prior_forms_legal_experience` 的 `for ref in experience["evidence_refs"]: assert ref.split(...)` 对旗舰样例**空转通过**——实测该样例 `evidence_refs=[]`（引擎对该话语无 signal:// 级证据引用），「既有 scheme 证据引用」在旗舰样例上**材料为空**（引用本身是引擎 passthrough，无伪造，但测试断言空洞）。
- **判定**：卡面「形成合法经验」最低要求**满足**（记录结构合法+可消费声明+可审计+显式不可写永久偏好+「没接线」如实登记）；两个强制登记项：①经验记录接线缺口归记忆 owner 卡；②空引用样例的 vacuous 断言应换为有引用样例或显式断言空集语义。

### R5 O-1 快照真值依赖 — **PASS**

- **复算**：独立脚本直读 `probe_corpus_snapshot.json` 23 条（positive 10 + negative 13）对 `probe_complex_expression` + `rule_arm_decide` 重算 → **零 mismatch**（expected/actual/rule_arm_decision 三字段全对）。
- **expected 自身真值独立抽验（不依赖快照）**：3 条手工独立判读（`不是不感兴趣，是资料太多不知道先看哪份`→multi_negation、`以后再说吧`→time_deferral、`不能说没有进步`→multi_negation）与活代码行为**及快照 expected 三方一致**；词牌在 selector 源码中定位核实（`不是不`/`以后再说` 字面在源；`不能说没有进步` 由否定组合模式覆盖）。
- **双份一起漂移残余风险**：本测试只防「行为变更不 bump 快照」与「bump 版本不重生成快照」；若同时 bump+重生成则测试不红——该残余由 `captured_with` 版本钉（不 bump 即红）+ 快照变更在 diff 中必然可见（评审面）+ I03 双审已核 expected + 本审抽验闭合。「当前快照错误」风险已独立排除。

## off 零差量红线（审查靶 6）— **PASS（可失败性实证）+ 精度勘误**

- **反转会不会红：实测会红。**变异测试：把 `_correction_mode()` 硬编码返回 `"live"`（模拟 off 零差量被破坏）→ `test_off_mode_keeps_v3_second_ask_chain` **FAILED**（第二问被压制 → `second.question is None` 断言红）；`git checkout --` 还原后复绿。
- **行为级零差量成立**：off 档三新面恒 None、skip/pause 词表零行为、`_attach_supplement_entry` off 早退、answer 链 annotations 与 V3 同构。
- **精度勘误（非阻塞）**：「逐字节保持」措辞过强——off 档 payload 与 V3 差两处：`version` 串 `friction-chat-wiring.v3→v4` + `to_dict()` 新增 3 个 null 键（supplement_entry/exit_ramp/correction_trace）。grep 核实版本串零消费者、新键均为 None，行为无差；建议文档措辞收敛为「行为级零变化（版本串与 3 个 null 键除外）」。

## I03 移交三项落地核（审查靶 7）— **全部落地，划界成立**

| 项 | 核验方式 | 结果 |
| --- | --- | --- |
| O-1 快照重算测试 | 单测直跑 `TestI03HandoverClosures::test_o1_corpus_snapshot_recomputes_zero_mismatch` + 本审独立复算 | **PASSED，23/23 零 mismatch** |
| O-2 import 期不变式 | `semantic_selector.py:763-769` 断言环（映射值 ⊆ AURORA_INTERVENTION_TYPES，字面量漂移 import 即红）+ 单测复核 | **PASSED** |
| N-2 live 显式 WARN | `test_live_mode_activation_warns_explicitly`（首激 1 次、重入不重复）+ metric `mode` 维度 | **PASSED**（I03 选择器自身 `SEMANTIC_SELECTOR_MODE` 的 live WARN 正确留归 I07——本卡未触碰选择器消费） |
| O-3/N-1/N-3 再移交 I07 | grep 证明本卡**零消费** `context_data["semantic_selector"]`/`["semantic_selector_mode"]`（仅测试 import 供 O-1/O-2 复核）；N-1 属规则臂消费面而本卡消费 `diagnose_friction`；N-3 本卡已知悉并复用同面（friction_decision checkpoint） | **划界理由成立**，键集冻结断言归真正挂消费的 I07 正确 |

## 挑战登记（CHALLENGED，均不阻塞）

1. **F-1（shadow 档跳过/暂停词表行为泄漏）**：实测 shadow 档下 `先暂停一下` 会**清 pending + outcome=no_action**（off 档同句 pending 保持 + ask）——与「shadow = payload 零变化」声明在 marker 语句上**不符**（shadow 测试只钉非 marker 语句）。方向良性（与用户意图一致、无写路径）、默认 off 无生产影响；要求：declaration 勘误或把 marker 门收紧为 live-only，归协调方裁决。
2. **F-2（回归计数勘误）**：diff_or_evidence_only.md「6 面回归 660 passed」与其自附明细之和 880 不符；本审复跑 880 回归 + 33 新测 = 913 passed。
3. **F-3（R2 词表过报收紧跟进）**：否定前缀复合句（`不想跳过…`/`别停一下`）过报确认；词表收紧作为后续词表变更过 reviewer。
4. **F-4（R4 缺口随行）**：经验记录接线归记忆 owner 卡；`evidence_refs` 空集样例的 vacuous 断言应补强；`V4_AUTO_CLARIFICATION_BUDGET` 为声明常量（未消费），若未来改为计数语义需先接线。

## 合并落差预判（审查靶 9）

- base `be495611`（心跳#5）；`origin/main` 现 HEAD `71553984`（F02 销账，17/58；base 之后 15 commits：S04/F02/FIX-559 三线合并+销账 state）。协调方提及的心跳#6 未出现在该 remote main 上（若后续落点为 state/tasks 文件，同下述面）。
- **试合并（`git merge --no-commit --no-ff origin/main` 后 abort）**：**自动合并零冲突**。唯一双面文件 `v4/04_tasks/tasks.json` 自动合并成功（双侧改不同行）；其余 main 增量（docs 自托管静态资产、mobile 像素组件、guards）与本卡改动面（backend aurora/wiring/tests + v4 evidence 新目录）完全不相交。**预判：集成合并无冲突面**。

## 结论

I04 三验收面行为属实且可失败：无提案面自由补充恒可达（FIX97）、今日预算会话作用域+写授权空集结构钉死、「不是不会」难度守卫复用引擎否定感知、一次决策性澄清闭环内压制+出口斜坡（保守方案仅引擎 B1 背书）、纠正追踪内容寻址+重开可见、off 档行为级零差量且反转实证变红。开发中发现并修复的 `_UNIT` 交替撕裂假阳经独立复原**证实为真**。I03 移交 O-1/O-2/N-2 闭合属实，O-3/N-1/N-3 划界成立。**一审 PASS_WITH_CHALLENGES**：4 项非阻塞挑战随 receipt 登记，建议协调方在集成 SHA 复验时顺带裁决 F-1 的 declaration 勘误方向；本卡无需重开。
