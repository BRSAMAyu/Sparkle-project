# V4-D04 · 独立一审 receipt（wtD04R1）

- 审查人：wtD04R1（未参与实现的独立会话）；日期 2026-09-28
- 对象：分支 `agent/v4/d04`，commit `d96a4458c12bb5b4c06edda03c4ac7edb4a65333`（base `7fd77b6d`）
- 方式：只读实现审计 + 独立复跑 + 自建夹具穷举探针 2 组 + 突变 M1/M2 亲做 + merge-tree 预演；探针文件跑毕即删，终态 `git status` 干净（除本 receipt）
- 环境：共享 venv Python 3.11.15 / pytest 9.0.2，`SECRET_KEY=ci-test-key DATABASE_URL=sqlite://` 全程

## 总裁决：**APPROVE**（附 2 项挑战级发现 F-1/F-2 需处置登记 + 7 项观察；均不阻断本卡验收）

三卡面验收逐条亲证成立（正反配对全部真实命令/可失败测试，逐条见 §A）；预登记①-⑦逐判见 §B；无断言削弱（§C 逐字节核）。发现与观察见 §D/§E——**F-1/F-2 不推翻验收，但须在销账前获得处置（limitations 补披露或独立小卡认领）**。

## A. 卡面验收亲证

### ① 只学习计时不显示掌握；Agent产物不计人类能力 — 确认 PASS
- 正：`test_time_only_spark_leaves_mastery_untouched_but_grows_trace`（解锁/study_count/minutes 增长，mastery 恒 0）；`test_quiz_verified_completion_fuses_and_lights`（VERIFIED 融合点亮，`oc=` 幂等标记）。
- 反：`test_repeated_time_sparks_never_display_mastery`（5×60min spark 后 mastery 仍 0，审计行全 projection、真实证据计数 0——D04 前该路径点亮，红转绿实证）；`test_run_receipt_outcome_alone_never_lights_never_unlocks`（SUCCEEDED receipt 不解锁不融合只溯源）。
- 写路径亲核：`stats_service.spark_node` 纯时长分支 `new_mastery = old_mastery`；`_calculate_mastery_delta`/`capped_legacy_mastery` 保留为纯函数兼容面（V3 断言在 `test_mastery_evidence.py:79` 原样）。内部 spark 调用方（task_service/feedback_service/event_listener）均不传 outcome——零隐藏融合点。

### ② 撤回证据后节点、列表、insight 同 version — 确认 PASS
- 世代机制亲证：trace 行钉 `epoch=N` 进 request_id 空位（`test_recompute_trace_row_pins_base_epoch` 断言精确串）；同秒撤回场景墙钟门确实漏检（`assert not (last_retraction_at > last_recompute_at)`）而世代门节点级+用户级同判 pending——D03 R2 量化的系统性漏检闭合。
- commit 门：窗口内 epoch 前进拒绝 / 世代未动放行 / 不可证（None）拒绝——fail-closed 三态亲测。
- 同门同 version：图响应带 `capability_read_state`（D03 `evaluate_read_gate` 出口透传）+ 节点/列表 `projection_version`（=revision）+ insight 面 pending 禁建议、收敛恢复——一个门多出口，测试 `test_predict_next_gated_by_pending_read_state` 全绿。

### ③ sprint奖励不读AI掌握分，跨用户分享不加个人能力 — 确认 PASS
- 分享：`KNOWLEDGE_SHARE_BONUS` 常量与 `update_node_mastery` 调用已删（全仓 grep 无 live 引用；`test_wt598` 中的残留串是迁移回填奇偶测试的历史 reason 形状，正当保留）。三测亲证：掌握分毫不动+溯源 `capability_effect=none`+事件 delta=0；零审计行零状态行创建；非节点资源只有 community 事件。
- sprint：`sprint_task_ledger`（BP-4 单一事实源）只读 `Task.status`，零 mastery 读点（grep 亲核）；本卡零改动差量举证，符合卡面「当前仓库已满足时做差量举证」。

## B. 预登记①-⑦逐判

| # | 预登记 | 独立判 |
|---|---|---|
| ① | focus 覆盖 ACTUAL→PRACTICED 是「最激进读法」，请审查裁决 | **维持实现侧，不放宽。** 独立论证：focus session 就是学习计时（含覆盖率门槛的时长型行为观察）；若归 VERIFIED 即「门槛化时长点亮掌握」，与验收①字面直接冲突——PRACTICED 不是最激进读法而是**唯一兼容读法**。设计真源（DATA_AND_GRAPH §星图权威「独立测验/修正过的练习证据才能支撑」）中 focus 两者皆非。关键边界保持干净：D-02 账本真相面（`classify_task_completion` focus 覆盖→ACTUAL）零改动，分歧只在星图消费面——「工作真的发生了」与「能力得到独立检验」分离，正是本卡要语义。放宽路径（`_HUMAN_VERIFICATION_EVIDENCE_SOURCES` 加 focus_session）若未来裁决，须显式留痕并重开验收①——本审不支持。`behavioral`（M-06 非时长型服务器观察）→VERIFIED 不违此判。 |
| ② | 练习标签封顶 SHINING（80+）vs GLIMMER | **SHINING 合理。** 80=NODE_MASTERED 触发线/mastered_count 统计线（产品「已掌握」语义线），封顶恰好切除「精通声明」保留序数信息；GLIMMER 封顶会把 30-79 存量与 5 分节点无差别化，丢失参与足迹梯度。亮度按存量分数保留（「亮但不叫精通」组合被 `test_unverified_high_score_never_displays_mastery_labels` 钉死：shining + brightness>0.5 + practiced）。边界如实性：`verified=None` 不封顶有测试钉住（`test_unknown_verified_face_keeps_legacy_display`），与 limitations #3 一致——但未封顶集含生产路由，见 O-4。 |
| ③ | D03 移交落地完整性 + 迁移前行墙钟兜底同款 | **落地完整。** 与 D03 R2-C1 原文（review_r2.md §靶5）逐字对照：a)「commit 前重读 epoch」→`_commit_epoch_gate` 单一判定点，fail-closed 口径（任一侧 None 即拒）✓；b)「把重算钉的 epoch 落进 trace（request_id 空位可用）」→`_write_recompute_trace_row(base_epoch=current_epoch)` 写 `epoch=N` ✓；c)「让 capability_node_read_state 切 epoch 比较」→钉世代为主判定 ✓；d)「墙钟只是兜底」→兜底分支与 D03 版**逐字节一致**（git show 对照：`_last_recompute_at`/`_last_retraction_at` 比较式与 `evaluate_read_gate(None, None)` 出口全同）✓。`_pending_by_epoch` None→恒 False 的不越权口径被用户级测试钉住（`test_user_gate_fresh_when_no_retraction_despite_memory_epoch`）。但节点级门的世代源选择引入新问题，见 F-1。 |
| ④ | 账本未命中 fail-closed PRACTICED vs TRACE_ONLY | **PRACTICED 方向正确。** 独立论证：完成行曾到达 X-08 捕获面（事件本身即参与主张的证据），未命中是有界扫描的基础设施边界（3×100，I01 同款；新完成首页必中）而非参与造假信号——因基础设施边界隐藏真实参与（TRACE_ONLY）比「可见但不声称能力」误差方向更差；且两方向都不融合，能力不变量两侧均保持。ghost guard 先拦已删任务、重放场景幂等 duplicate 不再分类——残余暴露面极窄。limitations #1 如实登记且给出单点改法，接受。 |
| ⑤ | practiced 进读面失效集是否流量放大 | **无实质放大，实测为净减。** D04 前自报完成走 lit（本就失效）；D04 后 practiced 同样失效——自报风暴场景失效流量不变。反向：NON_HUMAN/TRACE_ONLY 不在失效集，receipt/demo 风暴场景较 D04 前（一律 lit 必失效）**减少**失效流量。duplicate 重放不失效的精确性测试（`test_outcome_read_model_visibility.py:196`，`len(calls)==1`）复跑绿。失效为用户作用域 DEL，爆炸半径单用户。接受。 |
| ⑥ | 15 处断言更新合法性（重点） | **无削弱，CHALLENGE=∅。** 逐文件 diff 亲核：数量对齐 1(stats)+1(mastery_evidence)+10(absorption)+2(visibility)+1(delete_correction)=15（§5 表头「9 处」为笔误，其枚举本身 10 项，见 O-2）。两处断言改写均为卡面行为契约变更的**从严**方向：`mastery>0`→`==0`、`==LEGACY_TIME_MASTERY_CAP(40)`→`==39`；V3 封顶公式纯函数断言原样保留。**FIX-292 数值逐字节亲核**：`assert mastery_a == pytest.approx(40.0)`、`assert mastery_b == pytest.approx(46.666666666666664)` 与 GJ05 `assert status.mastery_score == pytest.approx(30.0)`（含 message 变体共 6 处 30.0）在 base 与 HEAD 间零字节差。被更新的 10 处点亮机制测仅新增 `_add_quiz_pass`（arrangement），断言文本未动。5 个既有测试文件全部在 §5 登记，无未登记测试改动。 |
| ⑦ | integration SHA 复验 | **复核成立且需更新。** main 在审查时点已前进至 `f6de174c`（越过 receipt 记录的 8458d3c7：F03/FIX-560/I04/CI38）。重算交集：`git diff --name-only 7fd77b6d..f6de174c` 与本卡变更文件交集仅 `v4/04_tasks/tasks.json`（状态文件，双侧改不同卡条目）；backend/app 零交集维持 ✓。merge-tree 预演（merge-base `d96a4458`×`f6de174c`）：**零冲突标记**，tasks.json 自动合并。合并时按流程做集成 SHA 复验+全批重跑的要求维持。 |

## C. 靶项补充核验

- **通道分类语义（靶1）**：D-02 `TruthClass` 恰 5 值（actual/self_reported/estimated/demo/unknown）；自建夹具穷举 20 组合亲测（非复用实现测试夹具）：**demo→trace_only**（透传展示不计个人能力）、self_reported→practiced、estimated/unknown→trace_only、static-map 对非 ACTUAL 4 值无缺员；ACTUAL 证据面细化 verified/non_human/practiced/trace_only 四臂 + 优先级（人类检验 > receipt > focus）+ 全部 fail-closed 臂（损坏 truth_class/未知 source/证据面不可读）逐臂实测通过。DB 面三规则各一正一反在 46 新测内全绿。
- **spark 零掌握（靶6）**：见验收①；封顶边界如实性见预登记②。
- **分享 +5 删除（靶7）**：正当性三源——卡面验收③字面指令（最强）、DATA_AND_GRAPH「能力证据与活动轨迹分离」（分享=参与轨迹）、I07「Agent代答不能结算人类掌握」（同族能力结算语义）。跨用户分享 +5 mastery 本是能力通胀向量（分享可刷），删除是修复而非行为破坏。
- **突变复现（靶8，亲做）**：M1（`if channel is not VERIFIED`→`if False and ...`）：突变前 sha256 `1e9f77f554cc32879578b6604aff1f6ba5979b61a8387e112a3527df381618ba`（与实现 receipt 快照前缀逐同）→ `test_outcome_absorption_channels.py` **4 failed**（focus 点亮/点击完成点亮/receipt 解锁/重放非 duplicate，签名与声明逐同）→ 还原后 sha256 **恒等**。M2（`_pending_by_epoch` 恒 False）：7 passed（0 failed）——契约层 `evaluate_read_gate` 世代比对构成第二道防御，还原 sha256 恒等；「非测试空洞、纵深防御实证」的自我声明**属实**。
- **复跑（靶9，全真实命令）**：46 新测（22 纯通道+7 吸收通道+7 spark 标签+7 读门世代+3 分享）**46 passed**；撤回面 23+11+7=**41 passed**（构成=核心契约 23+服务层 11+读门世代 7，其中 7 为 D04 新测——「D03 撤回 41」口径见 O-7）；galaxy 目录 **178**（164+新 14，构成核实）；全受影响面批（manifest 原命令）**472 passed in 145.02s**（声明 470，+2 方向安全零失败）；`mypy app --ignore-missing-imports --no-error-summary | grep -c 'error:'` = **56**（≤77，逐同）；ruff 同批 **All checks passed**；black 存量漂移 hunk 逐文件 worktree=main（absorber 1=1/stats 15=15/schemas 2=2/api 3=3/galaxy_service 6=6/community 0=0/retraction 0=0）零新增 ✓——但「新增文件 clean」声明面见 O-3。
- **合并落差（靶10）**：见预登记⑦。

## D. 挑战级发现（须处置，不阻断验收）

### F-1 · 节点级读门世代源用全局记忆 epoch 计数器——纯记忆域 bump 误判 stale（潜在，探针实证）
`capability_node_read_state` 主判定 `current_epoch = MemoryService.get_memory_epoch(user_id)`（全局计数器，含 M-01 记忆域 bump）；而 `_pending_by_epoch` docstring 与用户级门（`_last_retraction_epoch`，撤回事件谱系）都明确「记忆域 epoch bump 不越权判星图过期」。**亲测探针**（临时测试文件，跑毕即删）：钉世代 trace(epoch=1) + 纯记忆域 bump（`memory:delete`，epoch→2，零撤回）→ 节点级门 `pending_recompute/stale=True`，用户级门同场景 `fresh`——节点级违反本卡自己 codify 的不越权原则。缓解：`capability_node_read_state` **无生产消费点**（图面/建议面只接 `capability_user_read_state`，亲核 grep），故零用户可见暴露；D03 原语义（墙钟、撤回谱系）只在兜底分支保留。处置建议：消费卡接线前把节点级世代源切 `_last_retraction_epoch`（一行）或在该函数 docstring 显式钉死「世代源=全局记忆域」的语义决定；D03 R2-C1 原文未指定世代源，此为本卡的选择空间——选了较宽的一档且未登记。

### F-2 · 客户端自报 outcome 融合面未收口未披露（V3 既有，非本卡回归）
`POST /nodes/{node_id}/spark`（`app/api/v1/galaxy.py:412`）接受客户端提供的 `SparkOutcomeEvidence`（`evidence_type: quiz, value 0-100, confidence 0-1`，仅 pydantic 界校验）并经 `spark_node` 直接贝叶斯融合——无 D-02 账本条目、无 quiz 物化、不经过本卡通道分类器。按 D04 自己的词表，客户端自报 quiz 证据 = SELF_REPORTED → PRACTICED（零融合），该端点是通道纪律的旁路面。后果可达：自报 outcome → mastery ≥80 → 成就引擎 `mastery_threshold` 读共享标量发光子（奖励完整性面）。定性：**V3 既有入口，D04 未引入未恶化**（D04 前该路径同样融合，且时长另有封顶 40 增长）；卡面验收①字面（「只学习计时」「Agent 产物」）不受挫，四停止条件（权限/跨用户/复活/假成功）均不触及；服务级 outcome 融合本身被 `test_evidence_outcome_still_fuses_in_spark` 作为 G-01 数学钉住（合理）。但 D04 limitations（10 条）未披露此相邻融合面，与本卡「星图只接有效 outcome」的语义闭环存在公开缺口。处置建议：limitations 补披露一条 + 独立小卡收口（API face 通道化：客户端 outcome 一律 PRACTICED，或参数降级为诊断展示）。

## E. 观察（非阻断）

- **O-1** `fusion_observation_params` 无生产消费点：吸收器 VERIFIED 路径硬编码 TASK_OUTCOME 观察参数（60/0.8），quiz_feedback→QUIZ 档映射仅在纯函数测试面（docstring 已自述「quiz 事件当前无 outcome.recorded 生产者」）。消费接线时须真正路由过该函数，否则词表与行为漂移。
- **O-2** 证据 §5 表头「test_outcome_absorption.py 9 处」实为 **10 处**（其括号枚举本身 10 项；总数 15=1+1+10+2+1 正确）。文档笔误，不削弱。
- **O-3** black 棘轮声明「新增文件 clean」实测仅覆盖 manifest 命令中的 2 文件（capability_channel.py clean；retraction_recompute_service.py 存量 0=0）；其余 4 个新测试文件各有 32-163 行 black 重排面（docstring 内嵌 SQL 的 dedent 风格族），与 tests 树既有漂移同族（`test_stats_service.py` 在 main 即不 clean）。存量 hunk 持平声明逐文件复现属实。建议措辞收敛为「新增生产文件 clean；新测试文件随 tests 树既有漂移族」或顺手格式化。
- **O-4** 封顶未覆盖面含**生产路由** `POST /nodes/viewport`（`get_galaxy_graph_viewport` 两分支 `from_models` 均未装配 verified 计数——该面无 capability_channel、无标签封顶、mastery_evidence=None）。limitations #3 字面覆盖（「get_galaxy_graph 之外的 from_models 直呼点」）但未点名该用户可达路由；F 线扫尾应显式含它。
- **O-5** 证据 §2「AI 打分…**无任何奖励/付费路径读它**」措辞强于事实：成就 `mastery_threshold` 条件读共享 `mastery_score` 标量（AI set-point 与 legacy 存量共同构成）。limitation #7 已披露存量成分；§2 该句建议收敛为「sprint 奖励/排行路径零 mastery 读点；成就 mastery_threshold 读共享标量（限制#7）」。
- **O-6** `get_evidence_counts_by_node` 排除 `retracted` 臂无直接测试（projection 臂有：时间 spark 只留 projection 行→counts=={}；两臂共享同一 SQL 谓词；D03 面测墓碑零贡献但非该计数查询）。
- **O-7** 复跑口径微差：全批 **472** vs 声明 470（+2，零失败，方向安全）；「D03 撤回 41」实际构成 23（契约）+11（服务）+7（读门世代——含 D04 新测），D03 本卡遗留部分为 34。构成披露建议精确化。

## F. 结论

V4-D04 的核心语义闭环——**VERIFIED 才融合、PRACTICED 只解锁+溯源、NON_HUMAN/TRACE_ONLY 只留痕、纯时长零掌握增长、分享零能力效果**——实现与测试两面均成立且可失败（M1 四红实证门是承重墙）；D03 移交项按 R2-C1 建议完整落地且墙钟兜底逐字保留；15 处断言更新全部合法且关键数值逐字节保留。裁决 **APPROVE**。F-1（节点门世代源）/F-2（自报 outcome 旁路面）需在销账前获得显式处置（披露或独立卡认领），O-1..O-7 随 receipt 归档供后续卡消费。

- 审查人签名：wtD04R1 · 2026-09-28 · 本 receipt commit 于 `agent/v4/d04`（不 push）
- 复跑命令与 exit code：见上文 §C 各条（全部本轮真实执行，非转录实现 manifest）
