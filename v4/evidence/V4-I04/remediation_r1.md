# V4-I04 · 一审（R1）跟进项整改 receipt

- 整改会话：wtI04（原实现分支续作，未 push）
- 整改对象：`review_r1.md` §挑战登记 1-4（PASS_WITH_CHALLENGES 的四项非阻塞挑战）；一审 receipt 文件与 `review_receipt.json` 未动
- 分支：`agent/v4/i04`，一审 receipt commit `1c10361a` 之上
- 方法：每项最小改法 + 一正一反测试 + **mutation 自证（还原修法 → 对应测试红，复原后绿）**；回归面全量复跑；ruff/black/mypy 零新增

---

## F-1（最重）shadow 档跳过/暂停词表真实改变行为（与「shadow=观察零行为变化」声明不符）

**处置：按协调方裁决把 marker 词表（及同面第二问压制）的「行为应用」收口为 live-only；shadow 只观察；off 保持 V3 链。**

- **一审实测病灶**：shadow 档下「先暂停一下」会清 pending + outcome=no_action（off 档同句 pending 保持 + ask）——shadow 的 marker 分流（`_skip_turn`/`_pause_turn`）在「不清 pending/不产 no_action」的红线上泄漏。复查发现同型第二处：已答一轮后的第二问压制（`budget_declared_replay` 替换诊断 + 压制注记）此前 `correction_mode != "off"` 即应用，shadow 档同样改变 payload/出口——一并收口。
- **改法（`friction_chat_wiring._answer_turn` 单点门）**：
  - `live`：marker 先于分支解析分流（行为照常）；已答仍想追问 → 压制第二问 + 出口斜坡（行为照常）；
  - `shadow`：词表命中只产出**观察**——metric（`marker_observation` / `second_ask_observation`，surface 新增两值，同计数器）+ 结构化日志 + 出口 annotations 注入 `shadow_marker_observation = {kind, marker, applied: false}`（协调方明示允许的「shadow 注记」）；**不清 pending、不产 no_action、不出斜坡、不压制第二问**；
  - `off`：词表零接触（行为级零差量不变）。
  - `_skip_turn`/`_pause_turn` docstring 增记「入口仅 live 分支」契约（方法体行为不变）。
- **测试（一正一反）**：
  - 正例 `test_shadow_mode_marker_sentence_keeps_pending`：shadow「先暂停一下」→ outcome=ask、pending 保持、三新面恒 None；annotations 与 off 档**逐项恒等**（唯一差量 = `shadow_marker_observation` 注记，`applied=false`）；下一轮结构化回答照常消费（V3 第二问链未被破坏）；
  - 正例（同红线第二处）`test_shadow_mode_keeps_v3_second_ask_chain`：shadow 档已答一轮 → 第二问照常出面并挂新 pending（与 off 零差量），无压制注记/斜坡/追踪；
  - 反例/live 照常：既有 `test_skip_turn_clears_pending_with_conservative_or_honest_no_action` / `test_pause_turn_is_visible_user_choice_not_failure` / `test_live_mode_suppresses_second_ask_with_exit_ramp` 双钉不变。
- **mutation 自证**：还原 wiring 修复（marker 行为不限 live）→ 两个新 shadow 测试 **FAILED（2 failed / 37 passed）**；复原后 **39 passed** 全绿。

## F-2（勘误）回归计数 660 与明细之和 880 不符

**处置：文档算术勘误，以明细为准。** `diff_or_evidence_only.md` 交付物索引「6 面回归 660 passed」→ **880**（77+49+76+118+208+352=880，与 test_results.json 自附明细及一审独立复跑一致）。代码零改动。整改后复跑同面全绿（见 test_results.json `rectification` 块）。

## F-3/R2（词表过报收紧跟进）否定前缀复合句命中（「别停一下」/「不想跳过这题」）

**处置：选择「按宁漏报原则收紧」（一审给的两个选项之一），并如实登记残余边界。**

- **改法（`no_action_supplement.py`）**：新增封闭守卫词表 `MARKER_NEGATION_PREFIXES`（别/莫/勿/甭/不要/不想/不是/不能/不可/不准/不许/先别/不用/无需/无须，15 成员）+ `_match_marker` 统一匹配：命中点紧邻 1-2 字窗口为否定前缀 → 该命中作废；同 marker 多出现位置逐一判前缀（任一非否定出现即命中）；全被否定继续尝试下一 marker。判定依据：误触发（清 pending/本域静默）比漏识别（用户再点选或改述，可恢复）代价高——与一审「过报后果实测有界但存在」的实测一致，方向取保守。
- **不受影响面（守卫只看命中 span 之前）**：「不用问了」「别问了」等否定词**本身是词表成员**的照常命中；纯命中（「先暂停一下」「跳过，先不回答」「我要求暂停一下」）照常。
- **测试（一正一反）**：`test_negation_prefix_compounds_fail_closed`（「别停一下」「先别停一下」「不想跳过这题，让我再试试」「不是不想回答」→ None，后两者为一审实测过报句）；`test_negation_guard_does_not_kill_plain_marker_hits`（纯命中照常+成员否定词不误杀）；`test_marker_negation_prefixes_frozen_closed_set`（守卫词表封闭 + 1-2 字窗口契约 + 英文边界钉）。
- **残余边界（如实登记，limitations §4 同步更新）**：①英文否定（don't skip）不在守卫域——测试钉为已知边界；②否定词与 marker 间隔 >2 字的复合否定不识别；③漏报后果 = 该轮回答未被解析、pending 保持（保守向，可恢复）。后续词表/守卫变更仍过 reviewer（词表冻结纪律不变）。

## F-4/R4（vacuous 断言）旗舰样例 evidence_refs=[] 使 apply_free_supplement 断言空转通过

**处置：补非空 evidence_refs 样例让传播断言真咬合 + 旗舰样例空集语义显式钉死（一审建议的两条都做）。**

- **实测确认**：旗舰样例「不是不会，是不知道怎么开始」引擎重放 `evidence_refs==()`（utterance 无 signal:// 级证据）——原 `for ref in experience["evidence_refs"]` 循环零迭代空转。
- **改法（纯测试）**：
  - 正例 `test_apply_free_supplement_propagates_nonempty_engine_evidence_refs`：`spine_state_keys=("crisis_mode",)` → 引擎产出 `["signal://crisis_mode"]`（非空）；断言诊断/经验记录/纠正追踪三处**恒等**（零伪造、零丢失）+ 逐条既有封闭 scheme（signal:// / user_state://，引擎 docstring 契约）——实现若伪造或丢引用即刻红；
  - 旗舰样例改空集显式断言：`diagnosis.evidence_refs == ()` 且 `experience["evidence_refs"] == list(diagnosis.evidence_refs) == []` 且 trace basis 同空——「引用是引擎 passthrough，无伪造」从隐含变显式。
- 生产代码零改动（引用本就是引擎 passthrough，无伪造；接线缺口归记忆 owner 卡的登记维持一审口径）。

---

## 整改后复跑（2026-09-28，env `SECRET_KEY=ci-test-key DATABASE_URL=sqlite://`，本机解释器复用主检出 .venv）

| 面 | 结果 |
| --- | --- |
| 新测（39=33+6）+ I03 77 + I09 49 + wiring 76 | **241 passed** |
| A-03/J-05/A-05 相邻面 | **118 passed** |
| orchestration 全量 | **208 passed** |
| contract 全量 | **352 passed** |
| ruff / black（整改 4 文件，line-length 120） | **全部通过** |
| mypy 改动文件 | **0 errors**（grep 零命中） |
| mypy 棘轮 | **53 / baseline 77**（零新增） |
| 真实模型调用 | **0 次**（全链确定性/引擎重放/fakeredis） |

改动文件：`backend/app/aurora/no_action_supplement.py`、`backend/app/services/friction_chat_wiring.py`、`backend/app/config/settings.py`（注释勘误）、`backend/tests/unit/test_no_action_supplement.py`、`v4/evidence/V4-I04/{diff_or_evidence_only.md,limitations.md,test_results.json,run_manifest.json,run_manifest.json.artifacts_sha256}` + 本文件。零删除既有断言或检查。
