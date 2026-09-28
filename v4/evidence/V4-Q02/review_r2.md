# V4-Q02 · 独立二审 receipt（R2，wtQ02R2）

- 审查会话：wtQ02R2（未参与 Q02 实现与一审；worktree `/Users/brsama/code/GitHub/wtQ02`，分支 `agent/v4/q02`）
- 被审交付：commit `6ff6cc8e`（一审 receipt `7f3d7de6` → C1 整改 `6ff6cc8e`；基线 main `a2b17f1c`；审查时工作树干净）
- 审查日期：2026-09-29
- **裁决：PASS_WITH_CHALLENGES_CLOSED**（一审 C1 必改项经逐字复核+底层事实亲验确认闭合；C2 暂缓决定经复核接受；C3 维持已申报记录。无遗留阻断项）
- 审查方式：只读 + 本地复跑探针（venv 共享主检出 `Sparkle-project`，`backend/app/gen` 两次拷入用后已删；复现亲跑未用 `--write`、repro 工作区已还原；零产品代码改动、未动交付与证据原文、未 push）

## 一、逐靶下判（八靶全验）

### 靶1 C1 整改复核（首靶）—— 通过，无残留、无新失实 ✅

`git show 6ff6cc8e`：恰 3 文件 3 行（tasks.json progress_note / diff_or_evidence_only.md M11 段 / limitations.md §2），零数据变更。与 R1 §靶2(b) 修正表述逐字对照：

1. **「逐记录恒等」→「结局级」**：三处旧表述（limitations §2 旧句 `A≡C≡D 逐记录恒等`、`admission 收益门…未出现…形态`；diff M11 段旧句 `I05 live 门与 I02 门在该回路无可触发条件（逐记录恒等实证，非假设）`）全部清除；grep 复核仅剩修正后用法与 compare 算法名（`reproduce_counterexample.py` 的「逐记录深度比对」属脚本功能描述，无关）。
2. **「无可触发条件」限定**：三处现存用法全部带 `decision 门出` 限定；`I02 门在该回路无可触发条件` 保留成立（回路根本不达该面，R1 已裁定 I02 半句边界不变）。
3. **边界精确性底层事实亲验**（不轻信一审）：
   - 结局级：两 seed 各 120 episode，A/C/D 三臂 `resolved/utility/wrong/questions/intrusions` 逐结局比对 diff=0/120（s20260928、s20260929 双 seed 亲跑）。
   - C≡D 记录级：id 归一化（除 arm 标签）120/120 identical 双 seed 成立。
   - A vs C 记录级差异：s1 turn-records 360 vs 359、patch_moves 9 vs 4、patch_ids_seen 6 vs 2；episode 面唯一差异记录=`holdout_s20260928_p17:d8:skill`（decision_rounds A=2/C=1，结局相同）；s2 patch_moves 18 vs 13、applied ids 11 vs 7。
   - **一处压缩注记（非失实）**：tasks.json progress_note 只写「结局级恒等：120/120…非记录级」，未含 C≡D/A-vs-C 细分；完整边界由 limitations §2 括注承载，progress_note 为摘要位，判定可接受。

### 靶2 一审 M11 定性独立复判 —— 独立维持「harness 面局限+门触发被吸收；非产品接线缺口」 ✅

**I02 门**：`backend/app/core/context_pack.py:1599`（`ENABLE_MEMORY_UTILITY_GATE` 效用门）行号精确；三个产品装配集成点逐一亲验：`app/api/v1/chat.py:1036`（`ContextPackBuilder(db, …)`）、`app/orchestration/context_focus.py:383`（ENABLE_CONTEXT_FOCUSING 内）、`app/orchestration/plan_review_service.py:2426`（planning intent）。harness 决策服务 `friction_chat_wiring.py`、`stuck_journey_service.py` grep `context_pack` **零命中**（exit 1）。

**I05 门**：`policy_patch_service.py:445`（admission 收益门：`may_auto_activate && verdict != BENEFIT_OBSERVED` 不静默自动激活）、`:785-787`（decision_context 缺席=fail-closed 不命中）、`:816-838`（decision 门 `apply_live_bounds`）、`friction_chat_wiring.py:835`（`patched_decision_inputs` 确不传 `decision_context`）、`settings.py:984`（`EXPERIENCE_STRATEGY_LIVE_WINDOW_HOURS: int = 72`）、`tests/aurora_ablation/engine.py:584`（patch 载荷仅 `{intervention, direction: prefer}` + scope_friction_tag）——六锚全中。

**触发实证（runs/raw 亲跑，独立于一审探针）**：
- s1（s20260928）：patch_moves A=9 → C=4；patch_ids_seen A=6 → C=2；**admission** A `{evidenced:35, active:4}` vs C `{evidenced:36, active:3}`（=1 次自动激活被收益门拦截转 evidenced/confirm）；patch_confirmation A=35 vs C=36。
- s2（s20260929）：admission 三臂 `{evidenced:47, active:5}`；A applied_patch_ids uniq=11 vs C=7（一审「s2 ids 11→7」为 applied 口径，亲验对表；窗过期收窄 active 集成立）。
- **定性复判**：I02 面 harness 结构性不可达 + I05 decision 门出无可触发条件（wiring 缺席）+ admission/72h 真实触发但差分被 confirm-backstop 吸收、结局零变化——**不是 FIX-562/564 同族接线缺口，不登记 FIX 台账**，独立维持一审结论。

### 靶3 原反例复现链（抽 2 步亲跑）—— REPRODUCED @ 6ff6cc8e ✅

1. **sha256 对表**：本人独立 `hashlib` 复算 B03 冻结行 `V3-NEG-A08-POSTFIX-NOMEMORY-BEATS-FULL` 的 `source_sha256` 六工件——**6/6 MATCH**（v3-output/WT412-FRICTION-FIXES/a08-post-fix/ 下 EVAL_RESULTS.md、summary.json、raw/{full,no_memory,no_experience,fixed_policy}.jsonl）。
2. **全链复跑**：`backend venv python v4/evidence/V4-Q02/reproduce_counterexample.py`（未带 --write）→ **exit 0，verdict=REPRODUCED**，repo_head=`6ff6cc8e`（当前 SHA，比一审的 `a2b17f1c` 更进一步）。full=9/20（utility −9.2）、no_memory=11/20（0.0）、no_memory_beats_full=true（+10pp）；两臂 `normalized_identical=true`；applied 归因只收窄（full 冻结 8→新 2、no_memory 10→4，**零 fresh-only**）；首个分歧点全部落在三类已声明分歧（diagnosis version v1_2→v1_3 / UUID·盐 id / 归因收窄）。
- 附注：`runs/repro/repro_result.json` 现存文件为一审 `--write` 产物（repo_head=35c2e034、generated_at 2026-09-28T18:28Z，先于一审 receipt 提交 20 分钟）；本审亲跑后已将 repro/raw 还原为一审期状态。该子树为 gitignored 工作区，字节随重跑在声明分歧类内变化，非基线扰动。

### 靶4 统计面 —— 独立重算全对 ✅

- runner 实现复核（`scripts/devtools/q02_run_four_arm_utility_eval.py:348-365,414-443`）：配对差值=逐 profile 相减、重抽样单元=30 profile 簇、percentile bootstrap 10000 次——与声明一致；`:442` `hash(name)` 种子 wobble 事实确认。
- **CI 独立重算**（本人全新实现，bootstrap seed=42，从 runs/raw jsonl 重聚合）：
  - utility A−B：s1 点 −1.8167 CI [−2.717,−0.817]（报告 −1.816667 [−2.698,−0.842]）；s2 点 −1.2533 CI [−2.152,−0.308]（报告 [−2.157,−0.333]）——全部落在 hash-seed wobble 带内；
  - M12 C−B：s1 +3.3pp、s2 +5.8pp CI [−2.5,+15.0] 与报告精确一致（s1 报告 hi +10.8 在本人 +11.7 带内）；
  - M11 C−A / D−A：30/30 逐 profile 差值恒 0（双 seed）→ CI[0,0] 为精确结果，非 bootstrap 产物。
- 聚合亲数：s1 A=C=D 42/120(0.350)、B 38/120(0.317)；s2 56/120(0.467)、49/120(0.408)；dev 16/30 vs 17/30=−3.3pp、dev utility A−B=−9.2；wrong s2 A=196/B=67 与披露精确一致（s1 212/55）；簇 6×5（per_cluster n_profiles=5）。
- 两 seed 敏感性：resolve-rate dev −3.3 / s1 +3.3 / s2 +5.8 符号不稳定、utility 两 seed 稳定为负——复核一致。

### 靶5 验收三条（oracle 抽验 + I05 fold 107）—— 通过 ✅

1. **合成不宣称真人留存；比较不丢失败**：s1 亲数 episode_end 42+episode_fail 78=120（未排失败）；NOT_MEASURED_HUMAN 与 value_verdict.anti_gaming 在案。
2. **B 臂不剥夺当前约束；selected 与 all 同可见范围**：`runs/surface2_results.json` 九场景 `all_ok=true, failures=[]`；goal_present 三方式（gate_off/gate_on/no_history）九场景全 true 亲读；`selected ⊆ episodic_ids` 逐场景亲验（selected=0 场景平凡成立，selected=1 场景逐 id 对表）；oracle_frozen 文本在案。
3. **同源多摘要不加 n；利益门失败不靠全拒通过**：分析单元=episode/profile 簇（无摘要级 n）；**ctx08 bypass 实证**——`ctx08_all_optional_rejected_mandatory_kept` gate_meta：`required_memory_detected=true, required_memory_recall=false, passed=false, precision=null, verdict="required_memory_recall_miss_bypass", bypassed=true` 且 episodic 非空（回退保召回）；代码路径 `context_pack.py:1613-1627`（`if not utility_gate_meta.get("passed", True)` 回退 `_pre_gate_episodic`）逐行亲验。
   **I05 fold 107 亲跑**：`test_memory_utility_gate.py(25) + test_memory_utility_gate_wiring.py(9) + test_experience_strategy.py(56) + test_experience_strategy_service.py(17) = 107 passed`（fold_evidence_refs 测在 `test_experience_strategy.py:198-204`，套内全绿）；73=56+17 亦亲跑通过；邻接候选文件全绿（prefilter 61 / receipt_wiring 11 / receipt_sources 8 / laplace 3）。注：「180=107+73」中 73 批的邻接文件清单存在多种等价组合（61+11+… 或 56+17 等）均全绿，属非阻断账目模糊，无任何失败被掩盖。

### 靶6 BLOCKED 诚实性 —— 亲验通过 ✅

`v4/06_evaluation/budget.example.json`：`enabled=false / max_spend=null` 亲读；卡面 `heavy_token_required=false`；worktree 无 `backend/.env`、无 `.env`（ls 亲验）；`run_manifest.json` `model_requested_vs_actual.actual` llm_calls/llm_prompt_tokens/llm_completion_tokens/llm_cost 全 0；`/stack/llm` 明文「零调用（Provider 无 key 初始化失败日志=预期噪声）」。L1 零模型为结构事实，本人复跑聚合逐数复现佐证确定性。未以 Mock 冒充模型结果。

### 靶7 裁决校准 —— 正确 ✅

- 权威层：`v4/06_evaluation/METRICS.json` M11/M12 `evidence_layer=LIVE_MODEL_SYNTHETIC`（:86-101），M11 阈值「点估计≥+10pp 且簇 bootstrap95% 下界>0」——L1 实测点估计=精确 0，未达如实报 0，不降阈值。
- 协议边界：`EVALUATION_PROTOCOL.md:30` 「Q任务的implementation可完成，value verdict仍FAIL；终门读取后者。Budget/权限缺失记明确BLOCKED，不是PASS或无声SKIP」逐字在案——`FAIL_L1_BLOCKED_L2`（L1 效果门 FAIL + L2 NOT_RUN/BLOCKED_EXPLICIT）+ value NOT_PASS 口径精确；复合词在库（tasks.json 多例）。
- 反例：冻结行 `status_at_freeze=OPEN_AS_V4_BASELINE`，翻案条件「full−no_memory≥+10pp」未满足（实测 −10pp）如实维持 OPEN。
- 「live 门起作用仍零收益」逻辑链：修正后的表述（admission 拦截+窗过期真实发生、confirm-backstop 吸收、结局零变化）不仅不失实，反而**强化** L1 FAIL 的稳健性——live 机制在被 harness 触达的面上工作正常仍未带来收益；同时「不能据此宣称 V4 机制无效」的警示边界（I02 面不可达）如实保留。

### 靶8 C2 暂缓决定复核 —— 接受 ✅（附一条非阻断跟进）

- 暂缓理由（保冻结工件数字一致性）成立：`runs/artifacts_sha256.json` 31 pin 亲验 27 MATCH（含全部 dev/holdout/analysis/surface2 数据文件）；本轮改 runner 种子映射将制造「交付 runner ≠ 产出冻结数字的 runner」代际错位，比 ±0.03 wobble 代价更高。
- wobble 不翻转任何显著性结论（本审 CI 独立重算全部带内实证）；C2 在 R1 即定性为「建议，非阻断」。
- **非阻断跟进（登记后续触达 runner 时同 commit 小改）**：① `hash(name)` → `zlib.crc32(name)` 固定映射；② limitations §8 补一句 CI 边界 wobble ≈±0.03 披露（§8「同一 seed 内运行全确定性」未覆盖 analyze 步的进程内 hash 盐）；③ pinning 排除 `artifacts_sha256.json` 自引用销。

## 二、本审新发现（均非阻断）

- **D1（记录）**：`runs/artifacts_sha256.json` 31 pin 中 4 mismatch 全部归因闭合：`artifacts_sha256.json` 自引用销 1（文件含自身哈希必不自洽）+ `repro/raw/*.jsonl`×2 与 `repro/repro_result.json`×1 为一审 `--write` 重跑产物（repo_head=35c2e034、时间戳在案；声明分歧类内字节变化）。**全部被审数据文件（dev×4、holdout×16、analysis、surface2、freeze、runner_meta 等 27 件）逐 pin MATCH**。
- **D2（记录）**：`review_receipt.json` 一审未回填条目（只有 review_r1.md 落盘）；本审按 V4-I05 惯例回填 R1+R2 两条款目，R1 条目 provenance=review_r1.md + commit 7f3d7de6，标注 backfilled_by=wtQ02R2。
- **D3（建议）**：四臂交付物中 `runs/` 为 gitignored 工作区（符合仓库标准），committed 证据链=脚本+种子+`run_manifest.json(.artifacts_sha256)`+双 md；fresh clone 复验需单命令重跑——建议后续卡在 run_manifest 中内嵌 analysis.json 关键聚合 JSON 片段，降低复验成本（非本卡义务）。

## 三、结论

八靶全验：C1 整改逐字闭合且底层事实亲验成立；M11 定性独立复判维持一审（harness 面局限+I05 门触发被 confirm-backstop 吸收，非产品接线缺口，不登记 FIX）；复现链在当前 SHA 亲跑 REPRODUCED；统计面独立重算带内、M11 精确 0 为结构性事实；验收三条亲验通过（oracle+ctx08 bypass+fold 107）；BLOCKED 诚实性、裁决校准、C2 暂缓全部成立。披露三处措辞整改后无残留旧表述、无新失实。

**裁决：PASS_WITH_CHALLENGES_CLOSED**（一审 C1 已闭合；C2 暂缓接受并登记跟进；C3 维持已申报记录）。建议销账 DONE_REVIEWED，evidence_verdict 维持 `FAIL_L1_BLOCKED_L2`（评测轴，与审查轴独立）。

— wtQ02R2（独立审查，未参与实现与一审；gen 探针已删、repro 工作区已还原、工作树恢复干净）
