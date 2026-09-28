# V4-Q02 · 独立一审 receipt（R1，wtQ02R1）

- 审查会话：wtQ02R1（未参与实现；worktree `/Users/brsama/code/GitHub/wtQ02`，分支 `agent/v4/q02`）
- 被审交付：commit `35c2e034`（基线 main `a2b17f1c`；审查时工作树干净）
- 审查日期：2026-09-29
- **裁决：PASS_WITH_CHALLENGES**（交付可进 R2/合并轨道；2 条披露措辞挑战须在合并前整改，详见 §C）
- 审查方式：只读 + 本地复跑探针（venv 共享主检出 `Sparkle-project`，`backend/app/gen` 从主检出拷入用后已删；零产品代码改动、未动交付与证据原文、未 push）

## 一、逐靶独立下判（七靶全验）

### 靶1 复现链可信性 —— 独立确认 REPRODUCED ✅

- **sha256 亲验**：六个冻结工件用独立 `hashlib` 复算，逐一 MATCH 冻结行 `source_sha256`（`v4/evidence/V4-B03/negative_results.jsonl` 行 `V3-NEG-A08-POSTFIX-NOMEMORY-BEATS-FULL`）。
- **全脚本亲跑**：`SECRET_KEY=… backend venv python v4/evidence/V4-Q02/reproduce_counterexample.py --write` → **exit 0，verdict=REPRODUCED**。双路径重算 full=9/20（utility −9.2）、no_memory=11/20（0.0）；当前 SHA（`a2b17f1c`）复跑聚合逐数全同；`records_normalized_identical_to_frozen` 两臂 true；applied 归因方向检查 fresh⊆frozen（full 8→2 / no_memory 10→4，零 fresh-only）。首个分歧点=三类已声明分歧（诊断版本注记 v1_2→v1_3、UUID/盐 id），无未声明分歧。
- **「V4 六线合并未扰动 V3 基线」声明**：由本人在 `a2b17f1c` 上的独立复跑直接证实（聚合+归一化记录面全同）。

### 靶2 M11 恒等定性（本审最重靶）—— harness 面局限为主；**非产品接线缺口**；但披露文本有实质不准 ⚠️→挑战 C1

**（a）I02 门**：唯一集成点在 `backend/app/core/context_pack.py:1599`（`ContextPackBuilder` episodic 排序后的效用门）。真实产品消费面存在且已接线：`app/api/v1/chat.py:1036`、`app/orchestration/context_focus.py:383`、`app/orchestration/plan_review_service.py:2426`（chat/plan_review 装配链）。A-08 harness 决策服务 `app/services/friction_chat_wiring.py`、`app/services/stuck_journey_service.py` **零** context_pack 引用（grep 亲验）——L1 零模型 harness 的确定性决策回路结构性到不了该面。**定性=评测载荷（确定性响应模型替代 LLM+prompt 面）未覆盖集成面，属 harness 面局限**；产品侧 I02 已接进真实 chat 装配链，**不属于 FIX-562/564 同族「集成面未接线」，不登记 FIX 台账**。

**（b）I05 live 门**：已接在 harness 实际驱动的回路上——`app/services/policy_patch_service.py:445`（admission 收益门）与 `:816-838`（decision 门 `apply_live_bounds`）。逐记录探针实证（runs/raw 对比）：
- **decision 门出确实无可触发条件**：`friction_chat_wiring.py:835` 调 `patched_decision_inputs` 不传 `decision_context`；`policy_patch_service.py:785-787` 明文缺席事实=do_not_apply 键 fail-closed 不命中；harness patch 仅 scope_friction_tag（`tests/aurora_ablation/engine.py:584`），经 situation 预滤后 precondition 恒满足。此半句披露正确。
- **但「无可触发条件」整体不成立**：①72h 有界观察窗（`app/config/settings.py:984` 默认 72h）在两个 holdout seed 都实际触发——s1 patch_moves 回合 A=9→C=4、patch_ids_seen 6→2；s2 ids 11→7（窗过期收窄 active 集）。②admission 收益门在 s1 实际拦截 1 次自动激活：A `patch_admission{state:active}`×4 vs C×3，confirm 35→36——被拦 patch 走 T3 显式确认回流。**披露中「A≡C≡D 逐记录恒等」（limitations.md §2）为假**：C≡D 逐记录恒等成立（本人 id 归一化比对 identical=True），dev 的 A≡C 成立，但 holdout 两 seed 的 A vs C 在 patch 归因/重排面逐记录不同（s1 另有 p17:d8:skill 一条轨迹路径差异：C day8 解决 vs A day9 多一会话后解决——结局相同）。
- **修正后的正确表述**（C1 要求整改）：恒等是**结局级**（resolved/utility/wrong/questions/intrusions 逐数精确 0，两 seed 120/120 episode 结局逐一相同），不是记录级；机制不是「门无可触发条件」，而是「**live 门真实触发（窗过期+1 次收益门拦截）但差分被 confirm-backstop 吸收，未翻转任何结局**」。此修正不翻任何结论——反而强化 L1 FAIL 的稳健性（live 模式起作用仍未带来收益），并保持「不能据此宣称 V4 机制无效」警示中 I02 那一半的面边界不变。

### 靶3 统计面 —— 独立复核全对 ✅（一处非阻断实现瑕疵）

- 实现抽核（`scripts/devtools/q02_run_four_arm_utility_eval.py:348-365,414-443`）：配对差值=逐 profile 相减、重抽样单元=30 profile 簇、percentile bootstrap 10000 次——与声明一致。
- **CI 独立重算**（本人从 runs/raw jsonl 全新实现）：12 个臂聚合（3 集×4 臂的 resolved/utility/wrong）逐一精确吻合；`utility_A_minus_B` s1 点估计 −1.8167（报告 −1.816667），本人三个 bootstrap seed CI [−2.70,−0.857]/[−2.717,−0.817]/[−2.69,−0.835] 均覆报告值 [−2.698,−0.842]；s2 点 −1.2533、报告 CI [−2.157,−0.333] 在本人复算带内；`M12_C−B` s1 点 0.0333/报告 CI [−0.0417,+0.1083] 在带内、s2 [−0.025,+0.15] 精确复现。M11 CI[0,0] 因逐 profile 差值恒 0 属精确结果。
- 双 seed 敏感性声明核对：dev −3.3pp vs s1 +3.3pp vs s2 +5.8pp 符号不稳定、utility 两 seed 稳定为负——与 raw 复算一致。
- 非阻断瑕疵（C2）：runner `:442` 用 `hash(name)` 派生 bootstrap 种子，而 `:69` 进程内设 `PYTHONHASHSEED` 对当前进程无效——字符串哈希随机化未被禁用，CI 边界跨运行 wobble ≈±0.03（本人三 seed 实测），不翻转任何显著性结论；建议改固定映射（如 `zlib.crc32(name)`）。

### 靶4 验收三条对证据核 —— 亲验通过 ✅

1. **合成不宣称真人留存；比较不丢失败** ✅：NOT_MEASURED_HUMAN 显式标注（limitations §1、value_verdict.anti_gaming_notes）；s1 分母 42 end+78 fail=120 未排除失败（本人重数）；分批按原顺序无替换。
2. **B 臂不剥夺当前约束；selected 与 all 同可见范围** ✅：Surface-2 `no_history` 方式仅删 EpisodicMemory 行（`backend/tests/q02_surface2.py:399-409`），goal 三方式全保留——runs/surface2_results.json 九场景 `goal_present` 三方式全 true（亲读）；oracle③ `set_on ⊆ set_off`（`:463-466`）按内容比对逐场景通过=D 门只缩不增无复活。
3. **同源多摘要不加 n；利益门失败不靠全拒通过** ✅：分析单元=episode/profile（`episode_rows`/`profile_metrics`，无摘要级 n）；I05 `fold_evidence_refs` 折叠测在 107 套内（`test_experience_strategy.py:198,202`、`test_experience_strategy_service.py:214`），**本人复跑 107 passed**；ctx08 bypass 实证（runs 工件：verdict=`required_memory_recall_miss_bypass`、bypassed=true、precision=None、episodic 非空；代码路径 `context_pack.py:1613-1627` 回退保召回+计数）。

### 靶5 BLOCKED 诚实性 —— 亲验通过 ✅

`v4/06_evaluation/budget.example.json` 亲读 enabled=false/max_spend=null；卡面 `heavy_token_required=false`；worktree 无 `backend/.env`/`.env`（ls 亲验）；harness 零 LLM 为结构事实（`friction_chat_wiring.py:71`「LLM 0 次（全链确定性服务）」、`stuck_journey_service.py:10`），本人独立复跑聚合逐数复现佐证确定性；llm_calls=0 账目一致。M11/M12 权威层=`LIVE_MODEL_SYNTHETIC`（`v4/06_evaluation/METRICS.json:86-101`），实现把 live 层判 NOT_RUN(BLOCKED_EXPLICIT)、不以 L1 数字外推——**口径正确，非无声 SKIP，未以 Mock 冒充**。

### 靶6 裁决校准 —— 正确 ✅

`evidence_verdict="FAIL_L1_BLOCKED_L2"` 为新复合词条，与库内复合口径惯例一致（PASS_WITH_CHALLENGES_CLOSED 等），语义自明：L1 效果门 FAIL+L2 BLOCKED。符合「评测 FAIL 可交付但 value 不标 PASS」边界（协议 §失败处理「Q任务的implementation可完成，value verdict仍FAIL；终门读取后者」）；未降阈值（M11 阈值 ≥+10pp 未达如实报 0）；反例保持 OPEN_AS_V4_BASELINE；「M11 **形状** FAIL」措辞规避了在 LIVE_MODEL_SYNTHETIC 权威层宣称 M11 本体——用词准确。

### 靶7 数字诚实性 —— 全对 ✅

1080=(30+120×2)×4 臂（本人按 profile 重数：30 profile×4 episode=120/臂/seed）；dev 30=15 profile×2（A-08 冻结 10+种子扩展 5）；簇分布 6×5；pytest **180=107+73 两批本人复跑全绿**；mypy **59 本人复算=59**（≤77 棘轮，新文件在 app 作用域外零新增）；臂定义/旗标（A 默认/B no_memory/C +live/D +gate）与 runner/冻结清单一致；交付 diff 仅评测基础设施+证据+tasks.json 卡状态字段（PENDING→REVIEW_READY），零产品代码改动属实。

## 二、挑战（合并前须整改；不阻断进 R2）

- **C1（必改，披露措辞）**：`limitations.md` §2、`diff_or_evidence_only.md` M11 段、`tasks.json` progress_note 中三处不实/误导表述须改为本 receipt §靶2(b) 修正表述：①「A≡C≡D 逐记录恒等」→「结局级逐数恒等（C≡D 记录级恒等成立；A vs C 在 holdout patch 归因/重排面逐记录不同）」；②「I05 live 门 harness 载荷下无可触发条件」→限定为「decision 门出无可触发条件（wiring 不传 decision_context）；admission 收益门与 72h 有界窗**真实触发过**（s1 拦截 1 次自动激活 4→3、两 seed 窗过期收窄 active 集），差分被 confirm-backstop 吸收、结局零变化」。整改=改文档措辞，零数据变更、零重跑。
- **C2（建议，非阻断）**：bootstrap 种子 `hash(name)` 进程内不可复现（wobble ±0.03），换 `zlib.crc32` 固定映射；随 C1 同 commit 或后续小改。
- **C3（记录，不阻断）**：holdout 生成者与实现者未会话隔离（limitations §3 已如实申报）。本审核验：生成器为声明式 vocabulary 抽样、不触被评机制、seed 显式、单命令可重跑，且本人已从 raw 独立复算全部数字。R2 如需更强保证，可用审查者自选 seed 重跑（成本=单命令）。

## 三、结论

交付的实现质量、数据真实性、统计正确性、BLOCKED 诚实性与裁决校准全部经独立复核成立；原反例 REPRODUCED 由本人全链重跑确认；M11 恒等的**定性=harness 面局限（评测载荷未达 I02 集成面）+ I05 门触发后差分被吸收，非产品接线缺口，不登记 FIX 台账**。唯一实质问题是恒等机制的三处披露措辞（C1），不影响任何数字与结论方向。**裁决：PASS_WITH_CHALLENGES**，建议 R2 重点复核 C1 整改与 Surface-2 覆盖面（CTX 种子化近似，limitations §7 已申报）。

— wtQ02R1（独立审查，未参与实现；临时探针 gen 拷贝已删，工作树恢复干净）
