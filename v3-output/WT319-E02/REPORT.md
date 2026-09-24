# E-02（重跑）任务报告：Fast Semantic / Deliberate 能力路由 —— G-1 修复

- 任务卡：E-02（Stream AI/EVIDENCE-COGNITION / Risk high / Resource MEDIUM / Depends E-01 已完成 / Locks ai-routing）
- worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt319-e02-capability-routing`（branch 同名）
- **base SHA：`12ba22ec`**（开工时 main HEAD；收工时 main 已前进到 `cb022dad`，新提交仅涉 mobile/gateway/plans，与本卡 4 个关注文件零交集，无冲突面）
- **final SHA：见 git log -1（本 commit）**
- 热输入：`v3-output/WT316-E01/ROUTING_MAP.md` §6 G-1 + `REPORT.md`（wt316 缺口账）
- 性质：以 G-1 修复为主线的定向代码卡，**纯新增 44 行 + 测试 113 行**（含测试文件既有 I001 import 排序修复）

## G-1 修复（本卡主线）

### 机制（修前）

`generation_node` tier 决策分支序中，phase_d 强制档分支（修前 :1546）**无条件**先于深度词否决执行——深度词否决只存在于 balanced fast path 分支（修前 :1566→:292）内部。冲刺会话 cost_band=low → `capability_selection_policy._COST_BAND_TO_TIERS["low"]=[FAST, STANDARD]` → `session_state_mixin.py:292/:385` 写 `phase_d_forced_model_tier="fast"` → 会话内**所有**轮（含显式深度请求轮）被短路到 FAST thinking-off（L1）。lane 遥测当时已如实报 `deliberate/deep_marker_text`，但实际 tier 落 FAST——遥测与行为系统性错位。

### 语义（修后）

**显式深度信号（深度词 / 用户显式 deep 元请求）> phase 默认档 > 基础默认**——phase 门是默认不是枷锁：

- 新增 `_deep_signal_overrides_phase_default`（standard_workflow.py:141-173）：仅当 phase 偏好本身是 **FAST**（唯一低于 deliberate 能力带的 tier）且轮次携带深度信号时否决。深度词与 balanced fast path 共享同一真源 `DEEP_ANALYSIS_TEXT_MARKERS`（capability_lane.py:104，不另抄清单）；`reasoning_mode=deep` 视为用户显式元请求。
- 否决轮回落**既有默认选择链** `get_configured_llm_service`（reasoning_mode 偏好链 + 复杂度 delta + 健康秩）——不新建真源，llm_router 权威不变。
- 边界守卫：① phase 偏好 STANDARD 及以上不否决（同属 deliberate 带，防止把高成本带深度轮反向降档到默认链首选层）；② 用户显式快档（`reasoning_mode=fast`）不否决（该轮即便无 phase_d 也经 fast first touch 落 FAST，语义不变）；③ `phase_d_default_overridden="deep_signal"` 写入 context_data 供下游透传观测。
- 工具流不受影响：`planned_tool_sequence` 在场时 generation 在节点入口即改道 tool_execution（:1460-1468），本修复只改标准聊天轮的 LLM tier 选择，不触工具暴露面。

### 红测 → 绿证据

**红（修前基线，分支序现状复现 G-1）**：

```
DATABASE_URL=sqlite+aiosqlite:///:memory: pytest tests/unit/test_standard_workflow_generation_routing.py \
  -k "phase_d or deep_marker or user_deep_mode"
→ 2 failed, 2 passed
  FAILED test_generation_node_deep_marker_overrides_phase_d_fast_default
    （get_configured_llm_service 0 次调用——深度轮被 phase_d FAST 抢走）
  FAILED test_generation_node_user_deep_mode_overrides_phase_d_fast_default
  passed：test_generation_node_respects_phase_d_forced_model_tier（存量契约）
  passed：test_generation_node_phase_d_non_fast_tier_survives_deep_marker（守卫）
```

**绿（修后同批）**：`30 passed`（27 存量全绿，含 phase_d 尊重契约与 F-1 deep_analysis MAX 强制）。

**dev DB 行为面复核（只读 SELECT，wt316 探针法）**：

修前真实落点（`token_usage` 实证，非读码推断）：

| 真实轮次 | 修前落点 |
|---|---|
| 09-22 16:05「帮我系统讲解一下二部图的判定定理，包括充要条件和证明思路。」（冲刺会话） | `dashscope_fast/fast/balanced` |
| 09-23 04:34「帮我深入分析欧拉回路和哈密顿回路的判定条件差异，给出详细对比和例题，要全面」 | `dashscope_fast/fast/balanced` |

零 LLM 判定探针（worktree 修复代码，输入=上述真实 trace 消息 + 冲刺会话判定上下文）：**7/7 PASS**——2 条真实深词轮 lane=deliberate/deep_marker_text + deep_veto=True + balanced_fast=False；2 条冲刺轻量轮 phase_d FAST 强制保持（fast track 不回退）；phase_d=STANDARD 深词轮不否决；reasoning_mode=deep 元请求否决生效。

## 卡面范围内 / 外分界

**范围内（已修）**：G-1 phase_d 强制 FAST 先于深度词否决——E-02 能力路由核心错位（简单交互真正快 + 复杂决策保留能力的交集缺陷）。

**范围外（精确缺口留痕，挂钩点已按 final SHA 复核）**：

| # | 缺口 | 挂钩点（final SHA） | 不修理由 |
|---|---|---|---|
| G-2 | TRIVIAL 问候/确认 L0 直答缺失（W-2/C2 沿袭） | standard_workflow.py:1505（memory_answer 短路旁无 greeting 模板分支）；complexity_analyzer.py:85-92（TRIVIAL 判定已有） | 需产品文案权威（模板回复语），属 C2 收口卡，非能力路由分支序问题 |
| G-3 | default 配置 0/0 token 调用仍计账（W-3/C3 沿袭） | llm_router.py:842（default ModelConfig）；:1118/:1217/:1450/:1514/:1789 兜底点 | 计账基础设施，越 ai-routing 锁面 |
| G-4 | 证据抽取器默认开且模型 `claude-haiku-4-5` 不在 provider 注册表（必败调用+静默规则回退+不计账） | config/settings.py:947/:965；chat_signal_collector.py:216-228 | evidence stream 配置权威，动默认值需证据线会话裁决 |
| G-5 | 隐藏调用（Layer3/sufficiency/HyDE/planning/aurora_modeling/evidence extractor）不进 token_usage（C5 沿袭） | 同 wt316 ROUTING_MAP §5.2 | 观测债专项 |
| G-6 | E-06 batch 车道 dev 零调用记录（W-4 收口验证缺样本） | batch_worklane.py 调度入口；BATCH_LANE_DISPATCH_TOTAL | 上线后样本问题，非代码缺陷 |
| G-7 | dev `LLM_TIER_PRO=dashscope_standard_thinking,glm_4_7_pro` PRO 层语义错位；TOP glm_5.1 死配置 | llm_router.py:_override_tier_mapping_from_env :1048 起；dev .env | worker 对主仓 .env 只读（AGENTS.md 纪律），属部署配置项 |

**卡面 Acceptance 对账（诚实口径）**：

- 「简单 intent 不走 L2」：✅ 保持并经探针实证（冲刺轻量轮 balanced_fast=True、phase_d FAST 保持；L1 主路径 44/44 FAST 结论沿袭 wt316 行为面）。
- 「fallback 不把需要 tools 的任务降成 text-only 假完成」：✅ 未回退——`planned_tool_sequence`→DELIBERATE（capability_lane 工具流保护，61 测全绿）+ 节点入口工具改道逻辑未触碰；本修复不改工具暴露面。
- 「L1/L2 latency/quality 真实 A/B」：❌ 本卡未做——真实 A/B 需活体 LLM 流量与压测，越 LIGHT/零 LLM 纪律；沿用 B-05 SLO 基线（fast TTFT p50 440ms）为 L1 参照。此验收项建议由专门 perf 卡收口（卡面早期 ACCEPT 690541e3 已建 lane 基础设施，A/B 仍欠）。

## 测试证据（命令 + 数字）

```bash
cd <worktree>/backend
set -a && source /Users/brsama/code/GitHub/Sparkle-project/backend/.env && set +a   # 只读注入；worktree 无 .env 属预期

# 1) 红测（修前）-k "phase_d or deep_marker or user_deep_mode" → 2 failed, 2 passed
# 2) 修复后全文件：
DATABASE_URL="sqlite+aiosqlite:///:memory:" <venv-python> -m pytest \
  tests/unit/test_standard_workflow_generation_routing.py -q
  # → 30 passed in 0.99s（27 存量 + 3 新增）

# 3) 定向批（能力路由全邻域）：
DATABASE_URL="sqlite+aiosqlite:///:memory:" <venv-python> -m pytest \
  tests/unit/test_capability_lane.py \
  tests/unit/test_unified_intent_router_fast_path.py \
  tests/unit/test_unified_intent_router_fast_path_first_message.py \
  tests/unit/test_standard_workflow_generation_routing.py \
  tests/unit/test_deep_analysis_tier_routing.py \
  tests/unit/test_llm_router_free_tier.py \
  tests/unit/test_retrieval_intent_classifier.py \
  tests/unit/test_capability_selection_policy.py \
  tests/unit/test_situation_brief.py -q
  # → 166 passed, 3 warnings in 7.54s

# 4) 邻域回归（dual_core / phase_d 写侧管线）：
DATABASE_URL="sqlite+aiosqlite:///:memory:" <venv-python> -m pytest \
  tests/unit/test_dual_core_router.py tests/unit/test_phase_d_discovery_pipeline.py -q
  # → 20 passed in 4.28s

# 5) mypy 棘轮（backend/pyproject 口径，同 CI 脚本）：
mypy app --ignore-missing-imports --no-error-summary | grep -c 'error:'
  # → 1795 / baseline 1795（未推高）

# 6) ruff（两改动文件）：All checks passed（顺手修测试文件存量 I001）
# 7) 零 LLM 行为探针（真实 trace 输入）：/tmp/wt319_e02_probe.py → 7/7 PASS（收工自清）
# 8) rule guards：bash scripts/run_all_rule_guards.sh → exit 0，all rule guards passed (83 rules)
#    （注：worktree 需按协议 cp -RL 拷入 app/gen + gateway/gen + mobile/lib/gen，否则 BG 规则环境红）
```

## 风险

1. **冲刺会话时延体验**：深词轮从 FAST（thinking-off）改为默认链落点（balanced 偏好 STANDARD，复杂度可升档）——首 token 延迟会升。这是本修复的产品意图（深度请求保留 deliberate 能力），但 sprint 会话内连续深词轮的成本/延迟需上线后观察；`phase_d_default_overridden="deep_signal"` 已落 context_data 可透传观测。
2. **复杂度 delta 依赖**：否决轮最终 tier 由 llm_router 默认链决定（非显式 DELIBERATE 强制）——若 `COMPLEXITY_ROUTING_ENABLED` 关闭且 reasoning_mode=balanced，深词轮首选层为 STANDARD（thinking-off 直出层，DashScope 口径）。语义上 STANDARD 属 lane 定义的 L2 带（L1=FAST），故与 lane 遥测一致；但"深度词→思考开"的更强保证需要 PRO/MAX 层判定，属后续卡裁量。
3. **env 依赖用例**：5 个 tier 断言用例依赖 dev env inline 注入（沿袭 wt316 同结论），裸环境呈环境性失败，非本卡回归。
4. **`phase_d_default_overridden` 为新增 context_data 键**：run_ledger/billing 若有封闭枚举校验需透传登记（已查 generation 短路键 `generation_shortcut` 同为自由字符串口径，风险低）。
5. min reclaim：无进程/模拟器残留；探针脚本 `/tmp/wt319_e02_probe.py` 收工自清。
