# E-02 R1 标准验收收据（合并 R2 返修 delta 复核）

- 验收员：R1（wt8 独占，标准面 + 返修 delta 一趟合并）
- 对象：E-02「Fast Semantic / Deliberate Decision 能力路由」交付（6 M + 2 新增，patch 1643 行，未 commit）
- 基准：wt8 HEAD 0ea1e198 ｜ 主仓参照 03e23023（`git diff --stat cba29db1 03e23023 -- backend` 实测为空，A-01 未合入）
- 方法：全量 diff/patch 审读 + `apply --check --reverse` patch↔树双向核验 + 独立零 LLM 探针重放 + 测试分片实跑（61/174/20/10）+ stage37 预存失败 /tmp 基线克隆归因（即用即删）+ 主仓克隆 @ 03e23023 `apply --3way --check` 预演 + wt9/wt4 在途面重叠核对；未 stash/reset/clean/切分支，未 commit/push
- 前置阅读：`REVIEW_RECEIPT_2.md`（R2 初审 REWORK_DELTA）、`REVIEW_RECEIPT_3.md`（R2 delta 复核 ACCEPT）、REPORT.md §10

## 总 Verdict：**ACCEPT**

R2 两轮结论（F1/F2 闭环、变异必红、合入干净）经独立代码审读+探针重放全部确认；R1 标准面（改动面/卡面/测试实跑/可观测/合入预演）逐项 PASS。无必修项，2 条 P3 观察转 Leader。结论支持合入。

---

## 逐项 Verdict

### 1. 改动面核对 — Verdict: **PASS**

- `git status --short` 与自报逐字一致：6 M（standard_workflow/llm_router/metrics/retrieval_intent/fallback/llm_service）+ 2 untracked（capability_lane.py 400 行、test_capability_lane.py 835 行）+ `v3-output/E-02/`。
- `git apply --check --reverse changes.patch` **exit 0**——patch 与树内 8 文件（含 2 新文件）字节级一致。
- patch 文件清单 = 树内改动清单，无夹带文件；无密钥/凭证形态字符串；无 `/Users/...` 绝对路径与主仓路径；`SECRET_KEY="test-..."` 仅出现于 REPORT 复现命令（测试用例固定值，非密钥）。
- 格式化噪声：`git diff -w` 与全量 diff 差 12 行，逐一核对均为 reversed-insert 重构/l 常量替换伴随的**缩进变化**（如 llm_router.py 候选链块重排、fallback.py `same_tier_models` 缩进），非独立格式化提交噪声。

### 2. 卡面对照 — Verdict: **PASS**

- **fast/deliberate 双档落地**：`ChatCapabilityLane` 双值枚举 + 判定序 8 步（capability_lane.py:241-371，工具流保护→非 standard mode→deep→文档→专家→文档级检索→记忆 FAST→轻量 FAST→默认 DELIBERATE）；generation_node 接线后 tier 落点仍由既有分支执行、lane 反映生效行为（standard_workflow.py:1394-1406 注释明确解耦）。卡「简单 intent 不走 L2」：合成简单批 11/11 全 lane=fast 断言 + `get_configured_llm_service_for_tier(FAST, QUICK_QUERY)` 端到端断言在套件内。
- **V3-FIX-12 首个输入处置**：REPORT §2 基线复现证据完整——探针①破点确定性重现（「帮我记住」→graph_only/ambiguous 被.slim 一票否决、「是什么」→targeted_source_rag）、探针②③④ plus 落点机制闭环（STANDARD 位命中 dashscope_chat + 代码注册 tier=PLUS 记账）。台账行核实：`v3/06_agent_fleet/DYNAMIC_ISSUES.md` V3-FIX-12 = 「T-route-coverage（并入 E-02 能力路由卡首个输入）」，状态 OPEN、建议合入后由 Leader 改 FIXED@E-02——与本卡声明一致。记忆指令/检索问答不再长期 plus+balanced 的修复链（根修早退 + slim 二道防线 + lane FAST）在代码与测试两面闭合。
- **exam_preparation 工具流保护显式测试存在性**：4 处断言齐备（R2 已验 M5b 变异必红，本轮只核存在性）——lane 级 `test_lane_deliberate_for_exam_tool_flow`（:296）、slim 级 `test_memory_instruction_with_planned_tool_sequence_stays_full`（:244）、端到端 `test_generation_node_exam_tool_flow_keeps_deliberate`（:710，含 FAST tier 助手禁入断言）、合成复杂批（:819-820）。

### 3. 测试实跑 — Verdict: **PASS**（全部本机独立复跑，REPORT §8 口径逐字可复现）

| 套件 | 命令要点 | 实跑结果 |
|---|---|---|
| capability_lane 套件 | `pytest tests/unit/test_capability_lane.py -q` | **61 passed**（1.01s）✓ |
| 定向 battery 13 文件 | REPORT §8 原命令 | **174 passed**（1.63s）✓ |
| env 形态批 | dev env 形态 inline × deep_analysis + free_tier | **20 passed** ✓ |
| V3-FIX-04 glm thinking | battery 内 `test_llm_router_glm_thinking.py`(6) + `test_glm_batch_adaptive.py`(4) | **10/10** ✓ |
| 预存失败抽 1 基线归因 | stage37 kill-switch（独立进程）| wt8 内 **2 failed**（与自报一致）；/tmp 基线克隆（HEAD 0ea1e198 无补丁）**同 2 failed 同签名** → 预存、非 E-02 回归 ✓ |

内存纪律：swap 空闲 1.0G、load 4.2，全部分片串行 LIGHT 执行，未跑全量单进程（遵守 §7-6/§8 分片警示）。

### 4. R2 两轮结论复核（轻量，读码确认）— Verdict: **PASS**

- **memory_class_turn 根修**：retrieval_intent.py:395-409 早退（`classify_memory_class_message` 命中 ∧ 非 planning → `no_retrieval/reason=memory_class_turn`），位置在 planning hint 判定后、planning/knowledge 分支前，与 R2 回执一致。
- **`_MEMORY_INSTRUCTION_EXCLUDE_RE` 排除词族**：capability_lane.py:70-78 含 R2 建议全族（`怎么|如何|怎样|方法|技巧|妙招|更快|更高效|更有效`）+ 自报追加（`记住了|记下了|接下来`）；QUERY 侧 F1b 收紧（`我(?!们)` + 排除 `问我`）在 ：61/:89 落码。
- **LIGHT_REPLY_\* 共享常量单一定义**：`LIGHT_REPLY_TOOL_INTENT_MARKERS`/`LIGHT_REPLY_PERSONAL_DATA_MARKERS`/`DEEP_ANALYSIS_TEXT_MARKERS` 全仓字面量定义仅 capability_lane.py 一处，standard_workflow.py:56-58/:288/:2509 纯 import 引用，旧内联清单已删（grep 无第二份）。
- **lane 记忆分支 len≤120**：capability_lane.py:317-321（`len(text) <= 120 ∧ _light_reply_text_allowed`）+ step-8 同源门（:338/:348），与 R2 F2A/F2B 修复描述逐字一致。
- **独立探针重放（零 LLM，本轮新增证据）**：R2 六负样本（怎么记住/如何记住/有什么…方法/我记住了…/我们小组/老师问我）classify 全部 None；三正样本（帮我记住这个/记住我的学号/我喜欢的电影是什么）仍正确命中 memory_instruction/memory_retrieval_query——排除词未误伤主修复路径，与 R2 回执结论一致。

### 5. 可观测面 — Verdict: **PASS**（含 1 条 P3 观察）

- `CHAT_CAPABILITY_LANE_TOTAL{lane, memory_class, retrieval_mode, trigger}`（metrics.py:618-632）：trigger 封闭枚举注释与代码实际 reasons 全集**逐项核对无缺漏**（fast 3 + deliberate 11 形态，`chat_mode_*` 以通配族注明）。
- 结构化日志 `[CapabilityLane]`（capability_lane.py:390-397）+ `context_data["capability_lane"]` 下游透传，遥测失败不阻断主链路（pragma no cover 守护）。
- 与 E-01 ROUTING_MAP §5.1 对齐方式为「有据偏离」：原案 ladder_level label 挂 selection_total 会漏 L0 短路轮（无 selection 事件），独立 per-turn counter 口径更准——REPORT §3-4 落档了理由，lane=fast≈L1 / deliberate≈L2/L3 映射保留；未引入裸字符串 trigger（trigger=reasons[0]，全部代码内枚举）。
- 候选链可观测一致性：`resolve_candidate_models` 与 `_select_by_policy` 同为 reversed-insert（llm_router.py:1023-1038），断言 candidates[0]==selection.model_key 的双场景测试在套件内（:501/:517）。

### 6. 合入预演 — Verdict: **PASS**

- 主仓克隆 @ **03e23023**：`git apply --3way --check changes.patch` **exit 0**——6 个修改文件 cleanly，2 个新文件 direct apply（Falling back to direct application，预期行为）。
- 在途卡重叠预测（实测验证）：
  - **A-01（wt9）**：仅 `backend/app/aurora/runtime_v1/l2_intervention.py`——与 E-02 的 8 文件零交集；**wt9 未触碰 metrics.py，A-01 冲突面条件不触发，无需标注**。
  - **M-05（wt4）**：config/settings.py + core/context_manager.py + core/context_pack.py + orchestration/context_builder.py + 2 测试文件——memory/context 检索面，与 E-02 零交集。
  - E-02 触碰的 llm/orchestration/workflow 面在主仓 03e23023 亦无在途改动（backend diff cba29db1..03e23023 为空）——合入窗口预测干净。

## 必修分级

无必修项。P3 观察 2 条（不阻塞，转 Leader）：

- **O1（P3，观察）**：trigger 的 `chat_mode_{chat_mode}` 族是「有界通配」而非字面封闭枚举——chat_mode 取值由 app chat_modes 模块集合界定，metrics.py 注释已用 `chat_mode_*` 如实标注。可接受；若未来 chat_mode 无序扩张，标签基数需纳入治理。
- **O2（P3，pre-existing，转 Leader 可随 F5 一并登记）**：`standard_workflow.py:2630` `_should_use_slim_deep_analysis_context` 仍保留独立 personal_or_system_keywords 清单（含「我的知识星图」）——该函数属 deep_analysis slim 域、本卡未触碰，不构成 LIGHT_REPLY_* 「第二份」矛盾（R2 单一定义声明按其声明域成立）；仅作后续清单归拢的候选记录。

另：R2-F5（providers 按 model_name 上报健康 vs 选型按 model_key 查，pre-existing）维持转台账处置，与 R2 结论一致。

## 实跑命令清单（全部独立执行）

```bash
cd /Users/brsama/code/GitHub/Sparkle-sysrev/wt8
git status --short; git rev-parse HEAD                       # 6M+2??+v3-output, 0ea1e198
git apply --check --reverse v3-output/E-02/changes.patch     # exit 0
cd backend
SECRET_KEY="test-secret-key-0123456789abcdef0123456789abcdef" .venv/bin/python -m pytest \
  tests/unit/test_capability_lane.py -q                      # 61 passed
SECRET_KEY="..." .venv/bin/python -m pytest tests/unit/test_capability_lane.py \
  tests/unit/test_retrieval_intent_classifier.py tests/unit/test_standard_workflow_generation_routing.py \
  tests/unit/test_unified_intent_router_fast_path.py tests/unit/test_unified_intent_router_fast_path_first_message.py \
  tests/unit/test_unified_intent_router_routing.py tests/unit/test_unified_intent_router_helpers.py \
  tests/unit/test_llm_tier_fallback_order.py tests/unit/test_llm_same_tier_fallback.py \
  tests/unit/test_llm_timeout_fallback.py tests/unit/test_llm_router_health_tracking.py \
  tests/core/test_llm_router_glm_thinking.py tests/unit/test_glm_batch_adaptive.py -q   # 174 passed
SECRET_KEY="..." LLM_PROVIDER=qwen DEEPSEEK_REASON_MODEL=deepseek-v4-pro DASHSCOPE_REASON_MODEL=qwen3.8-flash \
  LLM_TIER_FAST=dashscope_fast LLM_TIER_STANDARD=dashscope_standard_thinking,dashscope_chat \
  LLM_TIER_PLUS=dashscope_chat LLM_TIER_PRO=dashscope_reason LLM_TIER_REASONING=dashscope_reason \
  LLM_TIER_MAX=dashscope_reason .venv/bin/python -m pytest \
  tests/unit/test_deep_analysis_tier_routing.py tests/unit/test_llm_router_free_tier.py -q   # 20 passed
SECRET_KEY="..." .venv/bin/python -m pytest tests/unit/test_stage37_llm_safety_kill_switch.py -q   # 2 failed (预存)
# 基线归因：git clone wt8 /tmp/r1-e02-baseline（HEAD 0ea1e198，ln -s .venv 与 app/gen）→ 同文件 2 failed 同签名 → 克隆已删
# 独立探针重放：classify_memory_class_message 六负三正（零 LLM）→ 与 R2 回执一致
# 合入预演：git clone 主仓 /tmp/r1-e02-main → checkout 03e23023 → git apply --3way --check → exit 0 → 克隆已删
```

## 结论

**ACCEPT**——建议 Leader 合入（patch 对 03e23023 自包含），合入后按 REPORT §7-4 将 V3-FIX-12 更新 FIXED@E-02；F5 + O2 登记 follow-up；A-01/M-05 与本交付无合入冲突，可并行推进。清理确认：/tmp 两个克隆已删，无残留进程/端口/模拟器，主仓与 dev DB 未写，未 commit/push。
