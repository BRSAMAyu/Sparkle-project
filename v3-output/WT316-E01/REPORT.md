# E-01（重跑）任务报告：Cognition Ladder 当前路由映射 v2

- 任务卡：E-01（Stream AI/EVIDENCE-COGNITION / Risk medium / Resource LIGHT / Depends B-05,B-06 均已合入 / Locks ai-routing）
- worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt316-e01-cog-ladder-map`（branch 同名）
- **base SHA：`101c19b9`**（main HEAD，含 E-02/E-06/E-07/B-05b/XIAOMI/BATCH_LLM_PROVIDER）｜ **final SHA：见 git log -1（本 commit）**
- 日期：2026-09-22 采样窗口至 09-24 ｜ 性质：「映射+对齐」LIGHT 卡，**零代码改动**（交付物全部为文档与证据）
- 交付物（本目录）：
  - `ROUTING_MAP.md` — v2 映射文档（路由栈现状 file:line、前后对照采样、L0-L3 判据表、metrics 对账、缺口/错位 G-1~G-7、v1 收敛项 C1-C6 对账）
  - `trace_classification.csv` — 132 行逐调用分类（E-02 合入后 98 条生成调用 + 34 条 default 0/0；含 lane/ladder/分类/rationale）
  - `changes.patch`、本报告
- 接续声明：E-01 曾于 09-19 由 wt6 执行并 ACCEPT（v3-output/E-01/），其后 E-02 依据该报告 C1 结论合入根修。本卡为 B-05/B-06 合入后的**当前态刷新**：不重建前版真源，只对账"哪些缺口已关、哪些仍开、哪些是新错位"。

## 做了什么

1. **差异审计**：逐文件核对前版 ROUTING_MAP 引用的每个机制在当前 HEAD 的落点与语义（unified_intent_router 三层级联、dual_core+Aurora 切流、generation_node 五分支 tier 决策序、llm_router 候选链/健康三相/batch 开关、capability_lane 与 memory_class 根修的消费面）。
2. **真实 trace 采样（dev DB 只读，`docker exec sparkle_db psql` SELECT-only）**：以 E-02 ACCEPT merge（09-19 21:20, 690541e3）为界做前后对照。合并后窗口 98 条生成调用按 session/request 前缀分车道（uuid_chat 44 / ns_canary 46 / aurora_modeling 8）+ 34 条 default 0/0，逐行分类入 CSV。核心行为结论：**真实聊天生成 44/44 落 dashscope_fast**（合并前 54/54 落 plus）——v1 W-1 覆盖面缺口行为面已关。
3. **L0-L3 判据刷新**：每级 entry 判据全部落到当前 file:line（v2 §3 表），新增 E-02 lane、E-06 batch 车道、E-07 健康滞回、Aurora 切流投影的现状映射；证据/认知链（services/evidence 贝叶斯融合 → BeliefState → dual_core）确认为 L0 主导、唯一 LLM 点为 conversational_extractor（G-4）。
4. **fast path 不退化验证**：当前 HEAD 实跑定向测试 142 passed（命令见下）+ 零 LLM 判据探针 5 条（v2 §4 表），证明记忆类轮次 slim/balanced_fast 判据已翻转（W-1 破点关闭）、深度词否决与 F-1 MAX 强制完好。

## 测试证据（命令 + 数字）

```bash
# worktree backend 内；主仓 .env 只读 source 注入（worktree 无 .env 属预期），TEST-DBGUARD 用 sqlite 内存
cd <worktree>/backend
set -a && source /Users/brsama/code/GitHub/Sparkle-project/backend/.env && set +a
DATABASE_URL="sqlite+aiosqlite:///:memory:" <main-venv-python> -m pytest \
  tests/unit/test_capability_lane.py \
  tests/unit/test_unified_intent_router_fast_path.py \
  tests/unit/test_unified_intent_router_fast_path_first_message.py -q
  # → 68 passed in 1.17s
DATABASE_URL="sqlite+aiosqlite:///:memory:" <main-venv-python> -m pytest \
  tests/unit/test_standard_workflow_generation_routing.py \
  tests/unit/test_deep_analysis_tier_routing.py \
  tests/unit/test_llm_router_free_tier.py \
  tests/unit/test_retrieval_intent_classifier.py -q
  # → 74 passed, 3 warnings in 4.42s
```

合计 **142 passed / 0 failed**。判据探针（同环境，零 LLM）：记忆指令/记忆检索两条消息 lane=fast、slim=True、balanced_fast=True；深词消息 lane=deliberate、balanced_fast=False（v2 §4）。

DB 采样命令族（只读）：`SELECT ... FROM token_usage LEFT JOIN LATERAL (SELECT ... FROM chat_messages ...)` 按日×model×tier 聚合 + lateral join 最近 user 消息 + session/request 前缀分车道；`routing_decision_log` 按日 decision_type 聚合。

## 缺口清单（详见 ROUTING_MAP v2 §6，按影响排序）

- **G-1 错位**：sprint 会话 phase_d 强制 tier（cost_band=low）先于深度词否决 → 深词轮落 L1 thinking-off（09-22 冲刺会话 7/7 轮 FAST 含"证明思路"轮）。挂钩点 standard_workflow.py:1546-1582 分支序 + capability_selection_policy.py:46-51。
- **G-2**：TRIVIAL 问候/确认仍走生成链（W-2 未关，C2 未实施）。
- **G-3**：default 0/0 token 调用仍计账，34 条/窗口（W-3 未关，C3 未实施）。
- **G-4**：证据链每 turn 隐藏 LLM 抽取默认开启且模型 `claude-haiku-4-5` 不在 provider 注册表（必败调用+静默规则回退+不计账；config/settings.py:947/:965）。
- **G-5**：隐藏调用不进 token_usage（C5 未关），新增 aurora_modeling 8 条无消息对应实证。
- **G-6**：E-06 batch 车道 dev 零调用记录，W-4/C4 收口验证缺样本。
- **G-7**：dev `LLM_TIER_PRO` 指向 standard 档模型——PRO 计费/能力语义错位；TOP glm_5.1 死配置仍注册。

## 风险

- 本卡零代码改动，无行为回归面；`changes.patch` 仅含 v3-output 文档。
- G-1 若由后续卡修复：改 generation_node 分支序或 cost_band 判定都可能影响考试冲刺时延体验（fast track 是有产品意图的），修复卡须先复现 sprint 会话判据输入再动，且保护 exam_preparation planned_tool_sequence 工具流（v1 C1 约束继续有效）。
- 观测类缺口（G-5/G-6）使"无隐藏无必要深模型"只能对聊天主链路下硬结论（已下：44/44 FAST、探针+142 测试）；aurora_modeling/batch/intent Layer3 等旁路的必要性与量级在埋点补齐前不可完全证伪。
- 5 个 tier 断言用例依赖 dev env inline 注入（worktree 无 .env），在无 env 的裸环境会以环境性失败呈现——非本卡回归（E-02 报告 §1 同结论）。
- min reclaim：无进程/模拟器残留；探针与 pytest 均已结束，`/tmp/wt316_post_e02_calls*.csv` 收工自清。
