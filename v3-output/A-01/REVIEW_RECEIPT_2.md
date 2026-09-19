# A-01 · R2 深层验收回执（DeepAudit 路线）

- Reviewer: R2（wt9 独占，DeepAudit）
- 对象: `backend/app/core/aurora_decision.py` + `backend/app/aurora/runtime_v1/l2_intervention.py` 接线 + 本目录 REPORT/RUNTIME_MAP/changes.patch
- Base: wt9 HEAD `cba29db1` + 未提交交付；主仓参照 `03e23023`（只读）
- 方法: 独立 REPL 行为探针 + 6 组独立变异（含 Worker 未做的 X-01 生长变异与 governance 入哈希变异）+ 全链路 spine 消费追踪 + 映射表 6 组件抽检 + patch 双端保真校验 + PYTHONHASHSEED 批次探针
- 变异纪律: 全部 cp /tmp 备份 → 单文件变异 → 红 → 还原 → diff 校验；收工树状态与交付一致（`git status` 5 项不变，43/43 绿）

---

## 逐风险面 Verdict

### 1. 词表封闭的真实性 — **PASS（带 1 个 P3 备注）**

- 干预目录 17 项对照 `v3/02_core_systems/AURORA_V3.md` §2 逐字核对：CLARIFY…NO_ACTION 全 17 项与契约 snake_case 集合**精确一致**（含 `co_execute`、`connect_peer`）。真源无误。
- 封闭机制：构造词表外值**不 raise**，`validate()` 返回 violation（REPL 实证：`intervention_type="escalate_emergency_18th"` 构造成功、validate 2 违规；uncertainty 第 7 类同理）——与 C-01 `decision_context.py` 的 `validate() -> tuple[str, ...]` 约定**同款**，非本卡自创。读侧纪律已写入 `aurora_decision_from_dict` docstring（重构后必须 validate()==() 才可信）。
- 变异实证（我方独立执行，非复述 Worker）：
  - M-A 目录加第 18 项 `escalate_emergency` → **5 failed**（精确集 + sha256 双钉 + 接线面连锁）；
  - M-B uncertainty 加第 7 类 `divine_inspiration` → 红（同批）。
- sha256 钉法核实：7 词表钉值与现行集合实际哈希一致（变异后报出的新哈希 `736896d0…` 证明钉的是真值）。
- P3-7 备注：封闭是 validate 门而非构造门——所有消费方必须调 validate()；A-04 read 门文档已承诺，届时须机制化。

### 2. ref scheme 结构派生 + 边界强制 — **PASS（本卡最强项）**

- 派生真实性（REPL）：`AURORA_DECISION_REF_SCHEMES == ACTION_SOURCE_REF_SCHEMES | {"signal"}` 为 import 时真union，非复制。
- **X-01 生长变异（M-C，Worker 未做）**：向 X-01 `ACTION_SOURCE_REF_SCHEMES` 加 `artifact` →
  (a) 运行时 `AURORA_DECISION_REF_SCHEMES` **自动含 artifact**（13 项）——不会静默缺；
  (b) 契约测试 `test_vocab_sha256_pins` **红**（钉哈希失配）——X-01 扩 scheme 必然在 A-01 显形并强制两位 reviewer 过目。「派生 + 双钉」组合设计成立，声称属实。
- 边界强制（REPL）：`action_proposal_ref="http://evil.example/x"` → validate 报 task:// 违规；`allocation_ref="http://…"` → decision:// 违规；goal:// 塞 action_proposal_ref、task:// 塞 allocation_ref 均有测试钉（`test_boundary_ref_schemes`）。裸 token（`"aurora_route"`，现存 TransitionDecisionRecord 形态）被拒有测试。
- `memory_use_receipts ⊆ evidence_refs`、annotations MappingProxyType 只读、`_INERT_INTERVENTIONS` ⇔ no_action_reason/execution_mode 交叉规则均在 validate 机制化 + 测试覆盖。

### 3. decision_id 确定性 — **PASS（带 1 个 P3 设计备注）**

- 输入域：schema_version/user_id/intervention_type/execution_mode/rationale_summary/cognition_tier/input_context_hash/sorted(evidence_refs)/no_action_reason。**user_id 在哈希内 → 不同用户同输入不撞 id**（测试钉住）。
- M-G 变异（Worker 未做）：把 governance_mode 塞进哈希种子 → `test_shadow_and_live_same_decision_share_id` **精确红**——shadow/live 同 id 是被测试钉死的设计，不是偶然。
- evidence_refs 用 `sorted()` 入哈希 → L2 `_get_matched_states` 的 `list(set(...))` 无序性不破坏 id 稳定性（考虑周到）。
- P3-4 备注：id 是**内容寻址**而非** occurrence 寻址**——同用户同模式同状态集（冷却过期后）跨月重现同 id；且 clarifying_question/uncertainties 不入哈希（REPL 实证：不同 question/uncertainties 同 id）。对 shadow/live 对比与审计去重是正确取舍，但 A-04 做 InterventionEpisode↔decision_id 关联时**不得把 decision_id 当唯一发生键**（多剧集共一号）；`decision://aurora_<id>` 锚的是「决策类」。需在 A-04 施工图中显式注明。

### 4. 示范接线真实性 — **PASS at component level / P2（系统级观测为零，措辞超卖）**

- 组件级真实：`check_escalation` 在真实引擎类上附 `aurora_decision` 载荷（非 mock）；legacy 面逐字保留（diff 证实仅追加，`pattern_name/intervention/reason/matched_states/energy_level` 原样）；非 UUID user_id 走纯 legacy 有测试钉；`decide()` 纯决策面实证（只读 `_is_cooled_down`，无 `_mark_intervention` 调用）；W1 类变异（去挂载）我方复现为红（M-D：3 failed）。
- **但 spine 消费链追踪结果**：`pipeline_context["l2_escalation"]`（spine_orchestrator.py:1470）之后**无任何生产代码读取该键**——policy_engine.evaluate 只读 `aurora_decisions`（另一通道）、`accuracy_trend` 等 7 键，全文件零处 "l2" 引用；`pipeline_context` 本身不落库；trace 只记 `l2:{pattern_name}`（spine_orchestrator.py:1471）；`logger.info` 行无 decision_id；spine 真正消费的 Aurora 决策通道是 `spine_aurora_bridge.feed_aurora_decision → spine:aurora_decisions:{user_id}`（policy_engine._apply_aurora_decision_bias 实际在读），L2 接线**未喂入该通道**；`L2InterventionEngine.decide()` **零生产调用方**。
- 结论：「spine 零改动自动流经」字面为真，但流经终点是无人读的 dict 键——生产链路上契约载荷目前**写后即弃，无任何可观测点**（日志/事件/持久化/指标皆无）。示范价值 = 组件级「决策点如何产契约」的模式，不是端到端可追踪性。卡片验收字面（"至少一个现状组件完成示范性升级接线"）满足；REPORT/模块 docstring 的「流经」措辞会让读者高估其可观测性。**P2-3**：建议返修加一行——现有 `logger.info("L2 escalation: …")` 追加 decision_id（零风险单行），让示范至少有一个生产可观测点。
- 分工安全性独立评估（Worker 自认风险 1）：`check_escalation` 冷却写（`_mark_intervention`）被 legacy t313 `test_cooldown_key_format_per_user_per_pattern` **钉死**（redis.set call_args 断言）——未来若 A-04 误以 decide() 为入口而丢冷却写，t313 必红。双真相边界目前是安全的。缺口：**无测试断言 decide() 不写冷却键**（负向钉缺失，若 decide() 误加 `_mark_intervention` 无测试会红）——P3 建议补一条 `redis.set.assert_not_called()`。

### 5. 映射表抽检（6 组件 + 治理面）— **PASS with 1×P2 失实 + 2×P3 计数错**

| 抽检 | 结果 |
|---|---|
| A-01 `engine.py` | ✅ materiality_check/decide_backbone_route/dispatch_trigger/safe_route 四方法全在（engine.py:54/59/91/219） |
| A-07 `decision_fns/fallback.py` | ✅ build_fallback_decision 在（:23） |
| R-06 `energy_controller.py` | ✅ EnergyDecision + EnergyLevelDecider 在（:25/:45） |
| R-09 `service.py` plan_turn | ✅ stage38 kill switch off 短路在函数头（:516-530），「off=无实例」定义点属实 |
| O-02 `dual_core_router` | ✅ DualCoreDecision（:106）+ 单例（:1333）+ AuroraProjectedDualCoreResult 在 migration.py（:35）——描述与代码一致 |
| A-10 policy v1.0.yaml | ⚠️ **失实**：见 P2-2 |
| §4 kill switch 家族 | ⚠️ 计数：正文「22 个」但枚举 23 个名字，全仓 grep 实际 23 个 distinct 类——off-by-one（P3） |

- **P2-2（失实项）**：契约 docstring、REPORT §2.2、RUNTIME_MAP A-10 三处均把 `capability_gate` 归入 v1.0.yaml 的 `parameter_write_authority`。**实际 yaml**（backend/app/aurora/policies/v1.0.yaml:44-52）：parameter_write_authority 仅 `{ux_intent, aurora_presence}` 两项；`capability_gate` 只出现在 interaction_model_registry 的 `writable_policy_scope`（4 变体中的 task_execution/meta_reflection 2 个）；`intervention_preference` yaml 全文不存在（AURORA_V3 §4 规格层来源——docstring 有披露「外加 §4 本体」，此半句诚实）。6 项集合本身作为「可写面并集」可辩护，但**归因文本错误**，且这是 Bounded Plasticity 治理面——A-04/L4 若照文本信任「yaml 已授权 capability_gate 写」会踩变体级差异。返修：三处归因改为「parameter_write_authority={ux_intent,aurora_presence}；writable_policy_scope 增 capability_gate（2/4 变体）；顶层阈值 {proactive_policy, materiality_threshold}；规格层 {intervention_preference}」。
- P3-5：§6 统计——决策点枚举实数 25（A 组 9 + R 组 10 + O 组 5 + S-01），声称 26；「44 组件」仅当 §4 治理家族计为 1 组件组时成立（43 行 + 1 组），未注明。

### 6. 三处自认风险（§7）评估 — **均为合理 v1 边界，无应堵未堵之洞**

1. decide()/check_escalation 分工：合理。生效路径冷却写有 t313 钉死（见风险面 4）；缺 decide() 不写键的负向钉（P3 建议，非洞）。
2. HYBRID 无 allocation_ref：契约合法（validate 不要求 actionable 必带 allocation_ref，docstring 已声明例外域）；消费方纪律 = 读 `allocation_ref is None` 判断镜像背后无分配决策。L2 的 rescope/pause 属「行动类但无分配」——比 docstring 举例（clarify/no_action 纯对话域）更宽，A-04 硬化时需把这类「镜像值无 allocation 支撑」的情形显式纳入 consistent_with_allocation 的语义（现为返回空 tuple 放行）。P3-8。
3. trigger_point 不封闭：v1 信息字段，已披露，合理（现有触发点词表确不覆盖 spine 面）。

### 7. 测试语义与基线 — **PASS 基线归因 / P2-1 新测试随机红**

- 目标面独立复跑：**175 passed（8.55s）** 与 REPORT 一致。
- 独立变异 6 组全红（M-A/M-B 词表、M-C X-01 生长、M-D 去挂载 3 failed、M-E 映射词表外 4 failed、M-G governance 入哈希 1 failed）——比 Worker 的 6 组多出 M-C/M-G 两个设计钉验证角度。
- 预存失败抽 1 归因：`test_aurora_runtime_decision_loop.py` 2 failed 在交付树上复现，失败本质是 prompt 文本断言（`current_streak_days >= 5` not in prompt_rules），decision_loop.py 对 A-01 四文件零 import 依赖——**与本卡无关属实**。
- **P2-1（新发现，必返修）**：`test_a01_aurora_decision_l2_wiring.py` 两处对 `evidence_refs` 做**精确有序**断言（`test_knowledge_crisis_carries_valid_contract` :82-85、`test_decide_cooldown_returns_no_action_with_evidence` :143），而 `evidence_refs` 源自 legacy `_get_matched_states` 的 `list(set(matched))`（顺序依赖 str hash）。**PYTHONHASHSEED ∈ {1,7,99} 三批次实测红、{42} 绿**——CI 随机哈希下约 3/4 概率假红。legacy t313 测试全用成员断言（`in`）无此问题；flake 是本卡新测试引入的。修复一行：断言改 `sorted(...) ==` 或集合比较。（产品无恙：decision_id 对顺序不敏感。）

### 8. 合入预演 — **PASS**

- `git apply --3way --check` 对主仓 `03e23023`：**exit=0 干净应用**。
- patch 保真：浅克隆 wt9 HEAD 打 patch 后与工作树逐字节 diff 一致（含 3 新文件 + 1 修改）；patch 文件清单与 §6 声明完全一致（1 M + 3 A）。
- 基线漂移：`cba29db1..03e23023` 对 A-01 触碰的 4 文件 **零 drift**。
- 在途卡重叠：wt8（E-02，llm_router/llm_service/standard_workflow/retrieval_intent/capability_lane/metrics）与 wt4（M-05，context_pack/context_builder/memory_use_selfcheck）——与 A-01 四文件**零交集**，合入冲突风险为零。

---

## 发现清单

| # | 级别 | 发现 | 状态 |
|---|---|---|---|
| P2-1 | P2 | 新接线测试 PYTHONHASHSEED 随机红（3/4 种子实测红）：evidence_refs 精确有序断言 × set 派生无序源 | Confirmed（复现） |
| P2-2 | P2 | policy 白名单归因失实：capability_gate 不在 parameter_write_authority（仅 2/4 变体 writable_policy_scope）；契约 docstring/REPORT/RUNTIME_MAP 三处同错 | Confirmed（yaml 直证） |
| P2-3 | P2 | 示范接线生产观测为零：pipeline_context["l2_escalation"] 无读者、日志无 decision_id、真通道（feed_aurora_decision）未喂、decide() 零生产调用——「自动流经」字面真、语义超卖 | Confirmed（全链追踪） |
| P3-4 | P3 | decision_id 内容寻址：跨 occurrence 同号 + clarifying_question/uncertainties 不入哈希——A-04 关联 episode 不得当唯一键 | Confirmed（REPL） |
| P3-5 | P3 | RUNTIME_MAP §6 计数：决策点 25 实 vs 26 声称；44 需计 §4 家族为 1 组才成立；§4「22 个」实为 23 | Confirmed |
| P3-6 | P3 | A-02 卡面目录拼写漂移（`coexecute`/`connect` vs 契约 `co_execute`/`connect_peer`，后者才是 AURORA_V3 §2 真源拼写）——跨卡地雷，需 Leader 在台账对齐，非 A-01 责任 | Confirmed（卡面直证） |
| P3-7 | P3 | 词表封闭是 validate 门非构造门（与 C-01 同约定，可接受）；A-04 read 门须机制化 validate 调用 | Confirmed |
| P3-8 | P3 | consistent_with_allocation 对缺 mode 属性的 allocation 静默放行；HYBRID 镜像无 allocation 支撑的消费方纪律待 A-04 硬化 | Confirmed |

## 变异清单（R2 独立执行，全部还原校验）

| # | 变异 | 结果 |
|---|---|---|
| M-A | 干预目录 +第 18 项 `escalate_emergency` | 5 failed（红） |
| M-B | uncertainty +第 7 类 `divine_inspiration` | 红（同批） |
| M-C | X-01 ACTION_SOURCE_REF_SCHEMES +`artifact` | 运行时自动显形 ✓ + sha256 钉红 ✓（无静默缺） |
| M-D | check_escalation 去契约挂载（pass 替代） | 3 failed（红） |
| M-E | L2 映射 `reduce_load→mega_pause`（词表外） | 4 failed（红） |
| M-G | governance_mode 塞入 decision_id 哈希 | 1 failed（shadow/live 锚点测试精确红） |

## 总 Verdict：**CHANGES（轻度返修后可合）**

契约本体（词表封闭/派生机制/边界强制/确定性 id/测试钉法）经独立变异检验**全部属实，是本 fleet 契约卡的标杆质量**；映射表抽检 6/7 准确；合入预演干净、零在途冲突。但：
1. P2-1 是交付物自带的新随机红测试——合入即污染 CI，必须修（一行）；
2. P2-2 是治理面上的失实文本，A-04 施工图会照抄，必须改（三处归因）；
3. P2-3 建议顺手补 decision_id 日志行（单行），把示范从「构造真实」提到「构造+可观测」。

返修不需要动契约本体与任何词表；以上三项均为测试断言/文本/单行日志粒度。修完免再审（R2 快速复核三项即可）。

---

## Delta 复核（R2 快速复核，2026-09-19 返修轮）——**三项全 PASS，总 Verdict 升级 ACCEPT**

范围锁定三项 + 顺手项，未做全量（契约核心在首轮已变异钉死，本轮无词表/字段改动）。

### 1. P2-1 种子测试 — **PASS**

- 三处 sorted() 等价实勘：`test_a01_aurora_decision_l2_wiring.py:69`（matched_states，返修员自查的第三处，超出 R2 清单的同源问题，一并修）、`:84`、`:144`（evidence_refs×2）；全文无残留精确有序断言（grep `== (` 空证）。
- 五种子实跑：`PYTHONHASHSEED ∈ {1,7,99,42,12345}` 接线测试 **15 passed × 5 全绿**（首轮 1/7/99 三红已消除）。

### 2. P2-2 归因文本 — **PASS**

- 三处与 yaml 事实一致，逐处核对：
  - 契约注释（`aurora_decision.py:148-155`）：parameter_write_authority 仅 {ux_intent, aurora_presence}；capability_gate 仅 writable_policy_scope 的 task_execution/meta_reflection 2/4 变体、按变体生效非全局；intervention_preference 为 §4 规格层、yaml 全文无——与 `policies/v1.0.yaml:44-52/61-84` 直证一致；
  - REPORT §2.2（:31）；RUNTIME_MAP A-10（:44，另加「A-04/L4 消费 capability_gate 须按变体判写权限」施工警示）。
- 词表集合值未动：契约测试 **30 passed**，sha256 钉全绿（钉值不受注释勘误影响，证实集合零改动）。

### 3. P2-3 decision_id 日志 — **PASS**

- 两处结构化日志实勘：`check_escalation`（l2_intervention.py:131-138，`aurora_decision_id={} catalog={}`，contract=None 路径记 `-`；legacy 日志前缀逐字保留仅追加字段）+ `decide()` fired 分支（:170-176，同款）。与自报「各加一条」一致。
- 观测测试 2 条绿：loguru 临时 sink 方案**修法正确**（callable sink `messages.append` + `finally: remove(sink_id)` 防泄漏——loguru 不走 stdlib root，caplog 捕不到的诊断属实）；断言日志中的 id 与载荷重构 id 一致（顺带钉住日志-载荷一致性）。
- RUNTIME_MAP S-01（:87）「写后待 A-04 喂」标注存在，且如实写明该键无生产读者 + feed 通道未喂属 A-04 范围。

### 4. 顺手项 — **PASS**

- 目标套件复跑 **177 passed（8.84s）**（= 175 + 2 观测测试）。
- 变异钉抽检 M-A（目录 +第 18 项）仍红：**2 failed**（精确集 + sha256 双钉），还原 diff 校验通过。
- changes.patch 重生成 1440 行，对主仓 03e23023 `apply --3way --check` **exit=0**。
- 树状态与交付一致（status 5 项不变）；/tmp 备份已清；未 commit/push。

### Delta 结论

首轮 3×P2 全部落地且无回归；P3-5 计数勘误、P3-4/P3-8 登记入 §7.6/§7.7 亦确认到位。
**总 Verdict：CHANGES → ACCEPT**（可合入；A-04 施工注意事项已由 S-01/A-10 标注承接）。
