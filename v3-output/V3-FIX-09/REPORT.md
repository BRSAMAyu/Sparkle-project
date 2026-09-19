# REPORT · V3-FIX-09（P2）：C-01 契约硬化 follow-ups

- 执行: V3 Fleet Worker（wt2，general 路线）
- 日期: 2026-09-19
- worktree: `/Users/brsama/code/GitHub/Sparkle-sysrev/wt2`（基线 origin/main @ **820c0203**，与任务简报一致，开工时 working tree clean）
- 上游依据: 主仓 `v3/06_agent_fleet/DYNAMIC_ISSUES.md` V3-FIX-09 行 + `v3-output/C-01/REVIEW_RECEIPT_2.md` F1–F7
- 约束遵守: 主仓与 dev DB 全程只读；无模拟器/Gradle/flutter/浏览器（LIGHT 任务）；真实 LLM 调用 0 次；无 git commit/push/stash/reset/clean/切分支；预存在失败核验用 `/tmp` 单文件粒度还原（改动先 cp 备份，收工已清 `/tmp`）

---

## 0. 处置总表（逐项）

| # | 级 | 位置 | 基线核对（@820c0203） | 处置 | 修法 |
|---|---|---|---|---|---|
| F1 | P2 | `backend/app/core/context_pack.py` `_collect_decision_signals` + `backend/app/core/decision_context.py` | **成立**：kill-switch `aggregator_enabled`=off 时 `_get_field` 直接返回 None；=shadow 时算完丢弃返回 None；两态在 collector 全部落 `degraded`，与真降级不可区分，且仅异常路径有日志、零指标 | **已修**（回执双路线都做了：原因编码 + 日志/metric） | ① 契约新增**可选尾字段** `DecisionContext.degraded_reasons: Mapping[str, str]`（appended after `built_at`，构造时 MappingProxyType 冻结，`to_dict` 流出普通 dict，`validate()` 对封闭词表 `DECISION_DEGRADED_REASONS` 校验）；② collector 先读治理模式：off/shadow → 跳过无效取数并编码 `governance_off`/`governance_shadow`；live 下 envelope 缺失/取数异常 → `unavailable`；③ 降级发生时聚合输出一条结构化 warning（user_id+mode+逐字段原因）并按原因码递增新计数器 `sparkle_decision_context_signal_degraded_total{reason}`。**shadow 测试**：`test_builder_signals_governance_shadow_mode_observable`（signals 空 + 三字段 degraded_reasons=governance_shadow + validate()==() + to_dict 可见 + 计数器 +3 + pack 其余面不受影响）；另加 off 测试（哨兵断言取数零发生）并强化既有异常降级测试（reasons==unavailable + 计数器断言） |
| F3 | P2 | `backend/app/core/decision_context.py` `DecisionStateSignal` | **成立**：`value: dict[str, Any]` 可变，消费者可进程内突变投影面（omitted_counts 自 C-01 起已有 MappingProxyType，value 漏保护） | **已修** | `__post_init__` 把 value 固化为 `MappingProxyType`（快照语义：冻结后再改源 dict 不影响投影）；注解 `dict[str, Any]` → `Mapping[str, Any]`（如实反映只读面，冻结快照清单同步更新，见 §3）；`validate()` 的 `isinstance(value, dict)` → `isinstance(value, Mapping)`；`to_dict()` 还原 `dict(self.value)`（序列化面不泄漏 proxy，非法非 Mapping 输入行为与基线一致——透传并交给 validate 报违规）。**mutation 必红测试**：`test_signal_value_is_immutable_projection`（赋值/新增键均 TypeError + to_dict 仍 plain dict + 快照语义断言） |
| F4 | P2 | `DecisionContext` docstring（omitted_counts 语义） | **成立**：omitted_counts = ranked 候选 − 注入 的差额；M-03 预筛/语义门控/多样性/冲突剔除发生在候选池形成前，不可见；语义未写入契约文档 | **已修**（文档化路线——实现简单的那个，测试钉住） | 候选集边界写入 `DecisionContext` 契约 docstring：计数只覆盖「已进入 rank/预算裁剪池候选 − 实际注入」（preferences/goals/episodic 三 section）；上游门控剔除**不计入**，该部分在 orchestrator 侧 context_sources manifest（memory_prefilter metadata、section note）观测——与 C-02 现状一致（manifest 已透传 prefilter rejected 计数）。**钉住测试**：`test_omitted_counts_candidate_boundary_documented`（docstring 关键词断言防文档回退 + omitted_counts 只读面保持）。不新增 `gate_excluded` 计数：上游剔除发生在 rank 层，builder 处无统一逐源剔除计数可取，硬造会引入假精度 |
| F6 | P3 | `decision_context.py` `_default_signal_projection` | **成立**：`_convert` 只处理 datetime/date/dict/list/dataclass，UUID/Decimal 原样穿透 | **已修** | `_convert` 增加 `UUID → str(item)`、`Decimal → str(item)`（含嵌套 dict/list/tuple 与 dataclass 字段递归路径）；docstring 同步声明。**契约形状断言**：`test_default_projection_is_json_safe_for_uuid_decimal`（dataclass 路径递归产物 `json.dumps` 不炸且 UUID/Decimal 均为 str；非 dataclass 标量路径 `{"value": "1.25"}`） |
| F7 | P3 | `orchestration/situation_brief.py` `SituationBrief.decision_context` | **成立**：SituationBrief.decision_context 是 prompt 侧 dict（residual diagnosis + decision policy + Phase A 守门合成物），与 ContextPack.decision_context（冻结契约对象）同名异义；`format_situation_brief_section` 同链路取用 | **已修**（文档化登记——回执建议即「命名冲突登记」，未改名） | 双向登记：`SituationBrief.decision_context` 字段上方 + `decision_context.py` 模块 docstring「命名消歧」节，显式声明二者同名异义、禁止互相替换/混用。**不改名**的依据：该字段经 `to_dict()` 的 `"decision_context"` key 流入持久化 session state（`session_state_mixin.py` 多处 `existing_brief.get("decision_context")` 从历史 state 读回），改名会孤儿化已持久化 brief，破坏面远超本卡收益 |
| F2 | P2 | — | 已随 C-01 合入（契约测试 R2-F2 三路 value 形状断言在位，本次回归通过） | 无需处理 | — |
| F5 | P2/P3 | plan_context↔prompts 循环 import | M-01 域，本卡不做 | 不做（按任务书） | — |

## 1. extend-only 纪律符合性（decision_context.v1 冻结契约）

- **版本不 bump**：按任务书 extend-only 纪律，`DECISION_CONTEXT_SCHEMA_VERSION` 保持 `"decision_context.v1"`；新增 `degraded_reasons` 为**可选尾字段**（带默认值、追加在 `built_at` 之后），旧构造签名完全兼容（`DecisionContext(user_id, intent)` 仍成立，专有断言在 `test_degraded_reasons_closed_vocabulary_and_readonly`）。
- **既有字段/枚举零语义变更**：封闭词表（scope/ref scheme/why_included/item type）逐字未动 → **C-02 消费面安全**（`context_sources.py` 只投影 `DECISION_ITEM_TYPES`，回归全绿）。唯一既有字段注解变更是 F3 的 `value` dict→Mapping（只读化），即回执点名的修复本身，runtime 语义只增不减（新增只读保证）。
- **契约快照更新（有意识、需合并评审确认）**：parity guard 的 `_DECLARED_SIGNAL_FIELDS`（value 注解）与 `_DECLARED_CONTEXT_FIELDS`（追加 degraded_reasons）同步更新，冻结哈希两侧一致；按 C-01 冻结声明这属「过两位 reviewer」的变更，随本 patch 送审即为流程。
- **降级原因词表新增**：`DECISION_DEGRADED_REASONS = {governance_off, governance_shadow, unavailable}`，封闭、有 docstring、有 validate 钉住。

## 2. 回归证据（全部本机实跑，`SECRET_KEY=test python3.11 -m pytest`）

| 套件 | 项数 | 结果 |
|---|---|---|
| C-01 契约测试 `tests/contract/test_decision_context_contract.py`（原 15 + 新增 6） | 21 | **全绿** |
| C-02 消费面 `tests/unit/test_context_sources.py` + `test_situation_brief.py` | 47 | **全绿**（本卡最大风险面，重点盯） |
| Context 家族（test_context_pack / test_context_focusing / test_context_pack_sources / test_context_source_contract / test_context_pack_rollout / test_router_context_reader） | 43 | **全绿** |
| 消费方与聚合器（test_memory_eval_service / test_prompt_signal_closure / test_insight_baseline_audit / test_phase_a_durability_pack / test_state_aggregator_service） | 35 | **全绿** |
| SituationBrief 消费方九件（ai_strategy_renderer / planning_strategy_compiler / capability_requirement_compiler / action_plan_contract / stage9_utilization_metrics / plan_quality_contract / plan_quality_gate / experience_actuator / behavioral_outcome_tracker） | 71 | 70 绿 + 1 预存在失败（见 §4） |

风格：ruff（5 个改动文件）All checks passed；black(120) 仅对新增块负责（见 §4 说明）。

## 3. 变更足迹（`changes.patch`，5 文件 +314/−30）

| 文件 | 变更 |
|---|---|
| `backend/app/core/decision_context.py` | F1 尾字段+词表+validate/to_dict；F3 value 只读化；F4 契约 docstring；F6 UUID/Decimal；F7 命名消歧节；extend-only 纪律入 docstring |
| `backend/app/core/context_pack.py` | `_collect_decision_signals` 治理模式分类 + 结构化日志 + metric（返回值 2 元组→3 元组，唯一调用点同步）；constructor 传 `degraded_reasons`；import 新计数器 |
| `backend/app/core/business_metrics.py` | 新增 `DECISION_CONTEXT_SIGNAL_DEGRADED_TOTAL`（+8 行，沿用邻居块风格） |
| `backend/app/orchestration/situation_brief.py` | F7 字段登记注释（+5 行，零行为变更） |
| `backend/tests/contract/test_decision_context_contract.py` | 冻结快照同步（2 行）+ 新增 4 个 Part A 契约测试 + 2 个 builder 治理测试 + 既有降级测试强化 |

行为面变更仅两处，均为回执点名的修复本体：① shadow/off 下 collector 不再发起注定为 None 的取数（原实现在 shadow 模式每次 build 白算 3 次聚合取数）；② 降级路径多一条聚合 warning 与计数器递增。其余全部为纯新增观测面。

## 4. 风险与备注

1. **预存在失败（与本卡无关，已单文件还原实锤）**：`tests/unit/test_experience_actuator.py::test_experience_actuator_auto_retrieves_user_material_grounding` 在干净 HEAD @820c0203 上同样失败（`_resolve_scoped_files` 抛异常 → `file_resolution_failed`，galaxy/file 域，与本卡 5 个文件零 import 交集）。该测试文件在同族九件套里单独跑亦失败，建议开卡排查（可能与 galax_service 的 gen 依赖或路由解析有关）。
2. **预存在失败（基线即挂，未触碰）**：`tests/unit/test_stage18_kill_switch.py` 两个用例在基线上失败——`resolve_settings_mode` 的 legacy bool `SPARKLE_AGGREGATOR_ENABLED`（settings 默认 True）会把 configured=="off"（fallback）劫持回 "live"，与测试预期相悖。本卡的治理测试通过**显式 monkeypatch 该 legacy bool = False** 规避（测试内注释已说明劫持机制）；kill_switch 解析逻辑本身本卡未动，建议另开卡澄清 legacy bool 语义。
3. **black 说明**：`business_metrics.py` 存在全文件级预存在风格漂移（当前 black 版本会对 349 行产生重排），为避免格式化噪音，本卡只手工新增 +8 行（与邻居块同风格），未对该文件跑全文件格式化；其余 4 个文件 ruff+black 全过。
4. **F4 语义边界**：`why_included` 词表中的 `semantic_gate`/`diversity` 描述的是「入选原因」，与 omitted_counts 的「剔除计数」分属两面；本卡把剔除侧边界写死为「rank 池后差额」，M-03 预筛剔除的可见性已由 C-02 manifest 承接（`context_sources.py` 现状，本卡回归覆盖）。
5. **asdict/缓存面核查**：pack/decision context 无 `cache_service` JSON 序列化路径（`context_pack.py`/`dual_core_router.py` 无 `cache_service.set`），`cache.py._json_default` 的 dataclass-asdict 分支不会触达 MappingProxyType；且该风险类别自 C-01（omitted_counts proxy）即预存在，本卡未扩大类别。

## 5. STATUS

**READY_FOR_REVIEW** — 交付物：本 REPORT + `changes.patch`（基线 820c0203 上可直接 `git apply`）。
