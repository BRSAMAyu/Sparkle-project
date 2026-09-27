# WT727 · E-03 卡状态双证裁决（数据卫生卡）

> 2026-09-27 ｜ wt727（接替 wt726 同卡复航；wt726-e03 worktree 经查零产出——分支停旧 main 7dda7feb、无 commit、无未提交文件、salvage/backup 无遗留，按预案重做）
> 分支 `agent/node-b/wt727/e03`（base = main @ 300742af）｜ 主仓只读，零产品代码改动

## 1. 待裁决冲突

- `v3/07_tasks/tasks.json` E-03「实时 Stage Events 与首反馈体验」= **TODO**
- `v3/.sparkle_v3_fleet_state.json` done 列表 wt366 = 「E-03 实时 Stage Events(500ms 首反馈/去抖/CoT 不泄)」merged@**0e4087ec**（2026-09-25，注「含主会话 stabilizer 语义修正」）
- 同类先例 G-04（wt718）：双证=主链早已落地、仅 tasks.json 滞后 → 置 done。本卡结论不同，见 §4。

## 2. 证据链

### 2.1 集成事实（正证一）

- 0e4087ec 是 main 祖先（`git merge-base --is-ancestor` YES）。
- 交付 12 文件 +1477/-138：`stage_events.py`（新，canonical 词表单一真源）、`orchestrator.py`（stream_callback/RunLedger/早 ack 前移到服务可知点 + drain-yield；context/retrieval/decision 帧挂真实边界）、`standard_workflow.py`（DAG 观察者工厂 + tool stage + 确认门 waiting）、`execution_engine.py`（OpenClaw 帧挂 tool stage，诚实标注无 ledger 关联）、gateway `deriveUXProgress` 等待类不再误标 answering（zh/en 词条）、mobile `AiStageStabilizer` ≥300ms 稳定窗接入 `chat_provider`。
- 0e4087ec 之后 `stage_events.py`/`test_stage_events_e03.py`/`chat_stage_stabilizer.dart` 零后续提交；`orchestrator.py` 等被他卡动过但 HEAD 测试全绿（下）。

### 2.2 HEAD（300742af）独立复验（正证二，本会话亲跑）

| 套件 | 结果 |
|---|---|
| backend `tests/unit/test_stage_events_e03.py` | **6/6 绿**（7.68s） |
| backend 回归（stream_queue/execution_feedback_wiring/multi_agent_spine） | **16/16 绿**（6.25s） |
| gateway `go test ./internal/handler/ -count=1` | **全包 ok**（29.8s 未缓存） |
| flutter `chat_stage_stabilizer_test.dart` | **8/8 绿**（含 ChatRunPhaseIndicator×Stabilizer 真实渲染防闪烁 widget 证明） |
| flutter `chat_provider_test.dart`（wt366 当时 DEFERRED 两文件之一） | **55/55 绿**（DEFERRED 缺口由本裁决闭合） |

6 个 E-03 测试与验收逐条对应：`test_first_stage_frame_beats_slow_context_build`（0.8s 慢桩下断言首帧 <0.5s 且早于 context_build_finished）、`test_deep_path_stage_sequence_matches_ledger`（stage↔RunLedger timeline 匹配）、`test_early_ack_frame_is_ledger_correlated`、`test_reasoning_chunks_never_leak_into_frames`（CoT 标记原文喂入 reasoning 块，断言任何下发帧不含）、`test_dag_observer_emits_tool_stage_and_confirmation_waiting`、`test_stage_events_module_contract`。

注：worktree 缺 gitignored 生成物（backend/app/gen、gateway/gen、mobile/lib/gen），自主仓 cp 补齐后可跑（AGENTS 判例先例）；backend 需 `SECRET_KEY` env（同 CI 口径）。

### 2.3 真实运行反证（wt372 E-08 bench，独立会话，2026-09-25）

- 引擎=0e4087ec 常驻实例，104 条真模型 query（L0-L3×26），gRPC 直连（网关透传 0.02-0.35s 不在口径内），raw.jsonl 全字段、程序化复算无手填。
- **首个真实阶段帧**（`t_first_stage_s`，即 ux_progress.stage 帧到达时间，正是 E-03 验收 1 的度量）本裁决自 raw.jsonl 复算：
  - L0：p50=0.394s，p95=0.934s ｜ L1：p50=1.091s，p95=3.416s
  - **L2：p50=1.776s，p95=5.746s，max=34.6s**（free 车道 12/12 全部 0.55-5.24s >500ms）
  - **L3：p50=3.595s，p95=7.324s**
  - 全量 **21/103** 条首阶段帧 ≤500ms
- wt372 报告 §7-D 原文定性：「E-03 stage 前置的覆盖边界……编排/深档轮的首个用户可见反馈仍秒级，S18 有反馈无进度在深档仍存在」，并立案 E08-ISS-L2-FEEDBACK（high）/E08-ISS-L3-ACK/E08-ISS-L0-TTFT。
- 根因：首帧前移只覆盖「服务可知后」段；深路径的 goal_quality 澄清门辅助 LLM 调用（约 3s、12 条零流式模板直出）、chat_mode 判定、自适应路由都发生在服务可知点之前。
- 0e4087ec..main 无任何针对该残差的修复（后续提交=CI/l10n/mypy/台账卫生）。

### 2.4 证据面缺口

- **integration/simulator evidence**：wt366 交付时未产出（commit 证据=单测+组件测；flutter 两文件 DEFERRED——本裁决已在 HEAD 补跑闭合）。真实运行证据只有 wt372 bench，且指向未达（§2.3）。
- **review receipt**：接力日志无 wt366/E-03 条目，无独立审查签收产物；fleet state「含主会话 stabilizer 语义修正」= 集成时主会话改过语义，非独立评审。本裁决即补位的独立审查。

## 3. 逐条对照

| E-03 口径 | 结论 | 依据 |
|---|---|---|
| Work1 定义 context/retrieval/decision/tool/waiting stage events | **达成** | stage_events.py canonical 词表 7 阶段（含 intake/handoff）+ 各真实边界接线 + gateway waiting 兜底；HEAD 测试绿 |
| Work2 第一阶段 feedback <500ms（**服务可知后**） | **达成（按字面口径）** | 早 ack 前移服务可知点 + drain-yield；单测 0.8s 慢桩下 <0.5s（自称实测 1.8ms）；HEAD 绿 |
| Work3 UI 去抖避免状态闪烁 | **达成** | AiStageStabilizer ≥300ms（首帧/同类立即、回摆即吞、终态冲刷）；8/8 widget 测试含真实渲染防闪烁证明 |
| 验收1a 深路径 500ms 内有真实阶段反馈 | **未达（端到端读法）** | wt372 实测 L2-free 12/12 全部 0.55-5.24s、L2 p95=5.75s、L3 p95=7.32s、全量 21/103 ≤500ms（§2.3）；卡面验收行无「服务可知后」限定词 |
| 验收1b stage 与 trace 匹配 | **达成** | STAGE_TO_LEDGER_STAGE 映射 + ledger_event_id 随帧；`test_deep_path_stage_sequence_matches_ledger` HEAD 绿 |
| 验收2 不显示 reasoning_content 原文 | **达成** | 结构性（build_stage_frame 无 reasoning 入参面）+ 负测 HEAD 绿 + mobile/lib reasoning_content 零命中 |
| Forbidden「不得只通过静态代码阅读宣称用户体验通过」 | **约束生效** | 唯一真实运行证据（wt372）与验收 1a 端到端读法相悖 → 不得裁全达成 |
| Required evidence（base/final SHA、targeted tests、integration/simulator、review receipt） | **3/4** | SHA 有（75594442→0e4087ec）；targeted tests 有且 HEAD 绿；integration/simulator 交付时缺（本裁决部分补验）；review receipt 缺（本裁决补位） |

## 4. 裁决：部分达成

- **机制面**（stage events 词表+真实边界接线+trace 匹配+CoT 不泄+UI 去抖+服务可知后首帧）双证齐全，早已落主链且 HEAD 全绿。
- **验收 1a 端到端读法未达**：深路径首个真实阶段反馈 p95 秒级（5.7s/7.3s），独立真实运行实证，非推测。与 G-04「主链已落地仅台账滞后」不同形——这里是卡片核心验收度量本身未闭合，且卡面 Forbidden 明令禁止以静态/单测宣称体验通过。
- 处置：**tasks.json E-03 保持 TODO（零改动）**；残差登记 **V3-FIX-439**（OPEN）。置 done 与否则待 Leader 对 V3-FIX-439 口径二选一：（a）服务可知点再前移（模式判定/澄清门前发 intake 帧+goal_quality 流式化/并行化）后按端到端复验；（b）按 work item 2 字面口径「服务可知后 <500ms」收窄判达成，端到端目标移交 E-08 SLO 修卡（E08-ISS-L2-FEEDBACK/L3-ACK/L0-TTFT 已随 wt372 交付物在案）。

## 5. 本卡变更清单（分支 agent/node-b/wt727/e03）

- `v3/06_agent_fleet/DYNAMIC_ISSUES.md`：追加 V3-FIX-439 行（7 列 8 裸管；429/438/440 全仓 grep 亲证 0 行空闲）。
- `v3-output/WT727-E03/notes.md`：本文。
- `v3/07_tasks/tasks.json`：**未动**（E-03 保持 TODO 即裁决）。
- 零产品代码改动；未 push。
- `python3 scripts/devtools/ledger_union_merge.py --verify v3/06_agent_fleet/DYNAMIC_ISSUES.md` → **verify 通过：311 行，裸管 {8:311}，零冲突、ID 无重号、状态枚举合法**。
