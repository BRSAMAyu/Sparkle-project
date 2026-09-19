# A-01 · AuroraDecision 契约与现有 Runtime 映射 — Worker 报告

**STATUS: READY_FOR_REVIEW**

- 卡片：`v3/07_tasks/cards/A-01.md`（Stream AURORA，Gate V3-2，risk high，Reviewers 2，locks aurora-contract）
- Base SHA：`cba29db192b9b98c9e435b110ce3a078d9afa4cc`（origin/main，含 B-06/C-01/C-02/C-03/X-01/X-02/D-02/M-01..M-04/M-07+FIX 全部合入）
- Final SHA：同上（未 commit；交付物 = 本目录 + `changes.patch`，改动文件清单见 §6）
- 真实 LLM 调用：0 次（纯契约+确定性接线；X-02 语义层默认关且本卡未触碰）

---

## 1. 实际解决的问题

Aurora 现状是「元数据 sidecar + 散点决策」：20+ 组件里控制决策散落在 backbone 路由、
materiality 门、L0-L4 分层、spine 管道等处，各自持有互不兼容的内部形状（自由串
evidence_refs、ad-hoc dict、pydantic 记录层），没有统一的「控制决策」面。本卡把它
升级为显式控制决策面，同时**零重建**：C-01 装证据、X-01 管任务结构、X-02 管执行
分配，AuroraDecisionContract 只拥有「选什么干预/为何/哪档认知/或为何不行动」。

## 2. 关键设计决策

1. **契约落位 `backend/app/core/aurora_decision.py`**（`aurora_decision.v1`），与
   `decision_context.py`/`action_plan.py` 同址同纪律：冻结 dataclass + 封闭词表 +
   版本戳 + extend-only（可选尾字段）。
2. **词表冻结**（全部 frozenset，测试 sha256 双钉）：
   - 干预目录 17 项 = AURORA_V3 §2 原文；
   - ref scheme = **X-01 ACTION_SOURCE_REF_SCHEMES 结构派生**（`frozenset(X-01 | {"signal"})`，
     X-01 的 11 scheme 自动包含，Aurora 域仅新增 `signal://`——spine StateRegister/L0 观测）；
   - uncertainty 6 类 / cognition tier 6 档（L0-L4+rule_fallback）/ no-action 原因 7 项 /
     governance {live,shadow} / policy patch 白名单 6 面。白名单归因（P2-2 勘误）：
     parameter_write_authority 仅 {ux_intent, aurora_presence}；capability_gate 仅
     writable_policy_scope 的 task_execution/meta_reflection 两变体（2/4，变体级授权）；
     顶层阈值面 {proactive_policy, materiality_threshold}；intervention_preference 为
     AURORA_V3 §4 规格层来源（yaml 全文无）。
3. **三态 kill switch 契约化**：`live`/`shadow` 是契约字段（`governance_mode`）；
   **`off` = 不存在契约实例**（治理关闭不是一种决策——C-01 FIX-09 纪律在决策侧的对偶）。
   现存 22 个 `aurora_*_kill_switch_service` 与契约的映射规则见 RUNTIME_MAP §4，零改动。
4. **确定性 decision_id**（`aurora_<sha256[:32]>`，governance_mode/created_at/annotations
   不参与哈希）⇒ 同输入同结论的 shadow 与 live **共享同一 id**——shadow/live 可对比的锚点，
   且复用 X-01 `decision://` 命名空间（前缀 `aurora_`，与 X-02 的 `alloc_` 同族）。
5. **命名消歧**（C-01 对 SituationBrief 同款纪律，写入双方 docstring）：
   `app.core.aurora_decision.AuroraDecisionContract` = 控制决策契约；
   `app.aurora.runtime_v1.decision_loop.AuroraDecision` = LLM 决策环 harness 执行决策
   （emit_message/wait/…）。同名近义、禁止混用；runtime 对象的升级路径在 RUNTIME_MAP R-08。
6. **交叉字段规则进 validate()**（不是文档级愿望）：no_action ⇔ 无 execution_mode 且必有
   原因码；`clarify` 必带 clarifying_question；`memory_use_receipts ⊆ evidence_refs`；
   `action_proposal_ref` 只认 `task://`、`allocation_ref` 只认 `decision://`（X-01/X-02 边界
   的机制化）；`consistent_with_allocation()` 为 A-04 联合接线提供一致性检查前置。
7. **示范接线选 L2**（`runtime_v1/l2_intervention.py`）：spine 聊天管道的真实决策点
   （`on_chat_turn → _run_signal_pipeline → _check_l2_escalation`），确定性、无 LLM、
   升级收益真实（其输出原本是不透明 dict）。映射 `L2_INTERVENTION_TO_CATALOG` 冻结：
   error_replan_bridge/adaptive_replan→`rescope`，reduce_load→`pause`；
   execution_mode=HYBRID（重排经 planning 管道+用户确认）；evidence=`signal://<state_key>`；
   新增 `decide()` 全结局契约视图（命中/无命中/冷却/空输入；无副作用，生效路径仍是
   `check_escalation`）；legacy dict 原样保留并附加 `aurora_decision` 载荷——
   spine 零改动即流经 `pipeline_context["l2_escalation"]`。

## 3. 交付物

| 文件 | 内容 |
|---|---|
| `backend/app/core/aurora_decision.py` | 契约真源（dataclass×3 + 7 词表 + 边界声明 + from/to_dict + 一致性检查） |
| `backend/tests/contract/test_aurora_decision_contract.py` | 冻结 parity guard：30 tests（字段指纹 + 词表 sha256 + 交叉规则 + 往返 + JSON 安全 + 确定性 id + X-02 一致性） |
| `backend/app/aurora/runtime_v1/l2_intervention.py` | 示范接线（check_escalation 附契约 + decide() 全结局视图；legacy 面不变） |
| `backend/tests/unit/test_a01_aurora_decision_l2_wiring.py` | 接线测试：15 tests（含映射全员覆盖纪律 + 非 UUID legacy 兼容 + P2-3 两条 decision_id 日志观测；全部哈希种子无关断言） |
| `v3-output/A-01/RUNTIME_MAP.md` | **映射表**：aurora 22 + runtime_v1 14 + orchestration 6 + spine 1 + 治理面 = 44 组件，逐个现状/契约角色/升级路径；26 个决策点；M-04 F-6 挂旗（§5，归 M-06/A-04） |
| `v3-output/A-01/changes.patch` | 上述代码改动的完整 patch（1 修改 + 3 新增） |

**零事件新增**：本卡不产 event_registry 新名（纯契约+映射+旁路载荷；A-04 若需
`aurora.decision_recorded` 再按 X-02/M-07 先例扩 35 名词表）。

## 4. 证据

### 4.1 目标测试（全绿，177 passed, 8.66s；R2 返修后含 2 条新观测测试）

```
SECRET_KEY=test /opt/homebrew/bin/python3.11 -m pytest \
  tests/contract/test_aurora_decision_contract.py \
  tests/unit/test_a01_aurora_decision_l2_wiring.py \
  tests/unit/test_t313_l2_intervention.py \
  tests/aurora/ tests/golden/test_aurora_experience_golden.py -q
→ 177 passed（R1 时 175；返修 +2 条 decision_id 日志观测测试）
```

含既有面回归：`tests/aurora/` 全目录（shadow comparison / signal pipeline / stage4 guardrails
等）+ L2 原有 25 tests 全绿 ⇒ **现有聊天不因接线退化**；`test_shadow_and_live_same_decision_share_id`
⇒ **shadow/live 可对比**（同 id 锚点）。

### 4.2 变异必红（6 组，全部按单文件粒度改动→红→还原，备份与还原 diff 校验通过）

| # | 变异 | 结果 |
|---|------|------|
| C1 | 契约词表删项（intervention catalog 移除 `remind`） | 2 failed（精确集 + sha256 钉双红） |
| C2 | 契约字段追加（`secret_extra_field`） | 1 failed（字段指纹） |
| C3 | 契约字段改名（`rationale_summary→rationale`） | 19 failed |
| W1 | 接线去挂载（check_escalation 不再附 `aurora_decision`） | 2 failed |
| W2 | 映射改词表外值（`error_replan_bridge→mega_rescope`） | 3 failed |
| W3 | 映射改语义（`reduce_load: pause→execute`，仍在词表内） | 1 failed |

### 4.3 基线与既有失败（全部预存在于 HEAD，与本卡无关，逐一在 HEAD 复核）

复核方法：把本卡 4 个文件全部移出 + `git checkout` l2 后在干净 HEAD 重跑，失败集**逐一致**：

- `tests/unit/test_aurora_runtime_decision_loop.py`：2（streak 规则 / fast-track planning，初始提交即有）
- `tests/contract/test_event_registry_contract.py`：1 param（state_aggregator service 引用 tracking_events）
- spine 选择集（-k "spine or l1_light or l0 or energy"）：17（self_model/skills/domain packs/L0 router/metrics）
- `tests/unit/test_aurora_correction_payload.py` 1 + `tests/unit/test_memory_admin_api.py` 1（单独在 HEAD 复核）

## 5. 验收对照

- [x] 契约 dataclass 冻结 + 词表封闭 + 版本戳 + 契约测试（变异必红：§4.2 C1-C3）
- [x] Runtime 映射表覆盖 aurora+orchestration 全部决策相关组件（44 组件 > 20+，逐个现状/契约角色/升级路径）
- [x] 至少一个现状组件按契约完成示范性升级接线（L2，§2.7）+ 接线变异必红（§4.2 W1-W3）
- [x] 与 C-01/X-01/X-02 的边界声明写入契约 docstring（§2 五节 + 命名消歧 + 三态规则）
- [x] 现有聊天不因 shadow Aurora 退化（tests/aurora 全绿 + L2 legacy 面不变测试）；shadow/live 可对比（decision_id 共享）
- [x] 契约可追踪到 source refs（evidence_refs 封闭 scheme；signal:// 直指 spine 状态键；裸 token 被拒有测试）
- [x] 不重建权威真源（execution_mode 复用 ExecutionMode；ref scheme 从 X-01 结构派生；policy 白名单对齐 v1.0.yaml；零 DB/schema/事件改动）
- [x] 不用 mock 冒充真实行为（接线在真实引擎类上，非 mock；mock 仅测试边界惯例）
- [x] 不弱化守卫（legacy check_escalation 语义逐字保留；冷却写/静默降级路径未动；既有 25 L2 tests 全绿）

## 6. 改动文件清单（收工 status 比对基线）

```
 M backend/app/aurora/runtime_v1/l2_intervention.py   （示范接线，唯一代码修改）
?? backend/app/core/aurora_decision.py               （契约，新）
?? backend/tests/contract/test_aurora_decision_contract.py（新）
?? backend/tests/unit/test_a01_aurora_decision_l2_wiring.py（新）
?? v3-output/A-01/{REPORT.md, RUNTIME_MAP.md, changes.patch}（交付物）
```

## 7. 风险与限制

1. **`decide()` 的双重真相风险**：`check_escalation`（生效面，写冷却键）与 `decide()`
   （纯决策面，无副作用）并存——已在两者 docstring 写死分工；A-04 若统一入口须保留
   「生效路径唯一」约束，否则冷却键不会被写（重复触发）。冷却写本身被 legacy t313
   `test_cooldown_key_format_per_user_per_pattern` 钉死（redis.set call_args 断言）。
2. **execution_mode=HYBRID for L2 是镜像值**：L2 重排没有走 X-02 decide_allocation
   （无 allocation_ref），HYBRID 是「planning 管道+用户确认」的现状描述；A-04 接线日
   若让 L2 触发的 replan 产出 ActionPlan，须回填 allocation_ref 并过一致性检查。
3. **trigger_point 未封闭**：v1 保持自由串（信息字段），现有触发点词表
   （pre-node-routing 等）不足以覆盖 spine/planning 面；封闭留给 v2（需 bump 版本）。
4. **非 UUID user_id 不挂契约**：L2 单测史的 "user_abc" 类 id 走纯 legacy 面（有测试钉住）；
   生产 spine 恒为 UUID。若未来出现非 UUID 生产路径，契约覆盖会静默缺位——依赖
   A-04 统一 read 门的覆盖率观测。
5. 预存失败（§4.3）不在本卡范围，未修（Forbidden：不弱化守卫亦不越界扩 scope）；
   建议 Leader 在 FIX 台账登记 spine-17 / event_registry-1 / decision_loop-2。
6. **P3-4（R2 登记）：decision_id 是内容寻址而非 occurrence 寻址**——同用户同模式
   同状态集跨时间（冷却过期后）重现**同一 id**；clarifying_question/uncertainties/
   created_at/annotations 不参与哈希（shadow/live 对比与审计去重的正确取舍）。
   **A-04 做 InterventionEpisode↔decision_id 关联时不得把 decision_id 当唯一发生键**
   （多剧集共一号）；`decision://aurora_<id>` 锚的是「决策类」，不是「决策事件实例」。
7. **P3-8（R2 登记）：`consistent_with_allocation` 对缺 `mode` 属性的 allocation 对象
   静默放行（返回空 tuple）**；且「actionable 但无 allocation_ref 支撑的镜像 mode」
   （如 L2 的 HYBRID）在当前语义下也放行——消费方纪律：读 `allocation_ref is None`
   即知镜像背后无分配决策。A-04 硬化项：把这类情形显式纳入一致性语义（警告级或
   violation），而非静默通过。

## 8. 后续（非本卡）

- A-04 联合接线：RUNTIME_MAP §5 的 🟡 清单（engine/safe_route → escalation → L0/L1 →
  wake_policy → core_session → decision_loop 出口 → sidecar/telemetry），及 M-04 F-6
  lane 守卫类感知（M-06/A-04）；L2 契约载荷喂入 spine 真通道
  （spine_aurora_bridge.feed_aurora_decision → spine:aurora_decisions，RUNTIME_MAP S-01
  「写后待 A-04 喂」）。
- `TransitionDecisionRecord.evidence_refs` 从裸 token 迁移到封闭 scheme（A-08 行，双写迁移期）。

---

## 9. R2 返修记录（2026-09-19，回执 `REVIEW_RECEIPT_2.md`，Verdict CHANGES→修完免重审）

R2 深审计强验证了契约核心（目录 17 项逐字精确 / X-01 派生为真 union 且生长变异自动
显形+钉红 / 边界 scheme 拒 http:// / shadow-live 同 id 被 M-G 变异钉死 / off=无实例实证），
另独立执行 6 组变异（含 Worker 未做的 X-01 生长 M-C 与 governance-入哈希 M-G）全红。
返修五项全部落地：

| 项 | 级别 | 处理 | 位置 |
|---|---|---|---|
| P2-1 | P2 | 哈希种子随机红修复：`evidence_refs`×2 + `matched_states`×1 三处精确有序断言改 `sorted()` 等价（第三处是 R2 清单外的同源问题，实测种子下同样红，一并修）；`PYTHONHASHSEED ∈ {1,7,99,42,12345}` 五种子全绿 | `tests/unit/test_a01_aurora_decision_l2_wiring.py` |
| P2-2 | P2 | capability_gate 归因失实三处勘正（yaml 事实：parameter_write_authority 仅 {ux_intent,aurora_presence}；capability_gate 仅 writable_policy_scope 的 task_execution/meta_reflection 2/4 变体；intervention_preference 为 §4 规格层、yaml 全文无）+ RUNTIME_MAP A-10 变体差异标注 | 契约 docstring（`AURORA_POLICY_PATCH_SCOPES` 注释）/ REPORT §2.2 / RUNTIME_MAP A-10 |
| P2-3 | P2 | 示范接线最小可观测点：`check_escalation` 与 `decide()` 各加一条 decision_id 结构化日志（loguru INFO，`aurora_decision_id=aurora_<id> catalog=<type>`；非 UUID/无映射路径记 `-`）+ 两条观测测试（loguru 临时 sink 断言）；RUNTIME_MAP S-01 标注「写后待 A-04 喂」（pipeline_context 键无生产读者、feed_aurora_decision 通道未喂——A-04 范围，本卡不接） | `l2_intervention.py` ×2 处 / wiring 测试 +2 / RUNTIME_MAP S-01 |
| P3-5 | P3 | 计数勘误：决策点 26→**25**（A 组 9 + R 组 10 + O 组 5 + S-01）；kill switch 22→**23**；「44」注明计法 = 43 表行 + §4 治理家族计 1 组 | RUNTIME_MAP §4/§6 |
| P3-4 / P3-8 | P3 | 登记不动码：decision_id 内容寻址语义（A-04 不得当唯一发生键）与 consistent_with_allocation 缺 mode 静默放行（A-04 硬化项）写入 §7 边界第 6/7 条 | REPORT §7.6/§7.7 |

**不在本卡范围**（R2 已划走，Leader 处理）：P3-6 A-02 卡面 coexecute/connect 拼写对齐；
P3-7 validate 门 vs 构造门（A-04 read 门机制化）。R2 风险面 4 的 P3 建议
（decide() 不写冷却键的负向钉 `redis.set.assert_not_called()`）未在本轮返修范围，留测试
加固轮/A-04。

**返修后证据**：目标套件 **177 passed**（含 +2 观测测试）；`PYTHONHASHSEED=1/7/99/42/12345`
接线测试全绿；契约测试 30 不变（词表 sha256 钉值不受注释勘误影响——集合值未动）；
t313 legacy 25 tests 不变绿。修后 R2 快速复核三项：种子测试 / capability_gate 归因文本 /
decision_id 日志存在。
