# V3-FIX-09 REVIEW RECEIPT — R1 验收（wt2 独占）

- Reviewer: R1（独立重验，不信任 Worker 自报）
- 日期: 2026-09-19
- 对象: V3-FIX-09「C-01 契约硬化 follow-ups」（P2），wt2 @ **820c0203**，交付 `v3-output/V3-FIX-09/{REPORT.md, changes.patch}`
- 方法: patch↔树逐字节比对、diff 逐 hunk 静态审查、契约/消费面全量实跑、**三处变异必红实验**、loguru 探针、5 文件还原到 HEAD 的基线归因、主仓 2375694c 浅克隆 `apply --3way --check` 合入预演

## 总 Verdict: **ACCEPT**

无 P0/P1。1 项低危备注（N1，不阻塞）+ 1 项回执背书供 Leader 入台账的真治理缺陷（kill-switch legacy bool 劫持，属本卡范围外，已代码级实锤）。

## 逐断言裁决

| # | 断言 | Verdict | 证据 |
|---|---|---|---|
| A1 | 改动面与自报一致（5 文件 +314/−30；patch↔树一致） | **PASS** | `git diff --stat` = 5 files +314/−30；patch 与树 diff 去 index 行逐字节 identical；收工后 status 与开工一致（5 M + untracked v3-output，无杂物） |
| A2 | extend-only：`degraded_reasons` 为可选尾字段，旧构造不炸 | **PASS** | 字段定义在 `built_at` 之后且 `field(default_factory=dict)`（decision_context.py:261）；`DecisionContext(user_id, intent)` 位置构造兼容（新字段第 11 位，专有断言 `test_degraded_reasons_closed_vocabulary_and_readonly` 绿） |
| A3 | schema 版本仍 `decision_context.v1` | **PASS** | decision_context.py:49 常量未动；冻结哈希 parity 测试在 21 项内通过（`_DECLARED_SIGNAL_FIELDS` value→`Mapping[str, Any]`、`_DECLARED_CONTEXT_FIELDS` 追加 `degraded_reasons`，两侧一致） |
| A4 | 既有字段/枚举零语义改动 | **PASS（附注）** | 逐 hunk 过：封闭词表（scope/ref/why_included/item type）逐字未动；唯一既有语义面变化是 F3 本体（`validate` 的 `isinstance(value, dict)`→`Mapping`，只放宽不收紧；`to_dict` 对 plain dict 浅拷贝等值）——即回执点名的修复本身，非偷改 |
| A5 | F1：off/shadow 跳过取数但不冒充 | **PASS** | 变异实锤：把 off 路径 `degraded_reasons[field_name]="governance_off"` 删为 `pass` → `test_builder_signals_governance_off_mode_skips_fetch` **必红**（已还原复绿）；shadow 探针（loguru sink）抓到真实 WARNING：`aggregator_mode='shadow' reasons={'emotion_hint':'governance_shadow',...}` 含 user_id；off 哨兵测试断言 `get_user_state` 零调用且 `fetch_calls==[]` |
| A6 | F3：value 构造时只读、to_dict 还原 plain dict | **PASS** | 变异实锤：`__post_init__` 置 `pass` → `test_signal_value_is_immutable_projection` **必红**（TypeError 消失），还原后复绿；快照语义（构造后改源 dict 不影响投影）在测试内断言；`to_dict` 返回 `dict(self.value)` 序列化面无 proxy 泄漏 |
| A7 | F4：候选集边界文档化 + 钉住测试 | **PASS** | `DecisionContext` docstring 写明「rank/预算裁剪池候选 − 实际注入」差额、上游门控剔除不计入、由 C-02 manifest 承接；`test_omitted_counts_candidate_boundary_documented` 关键词断言在 21 项内绿；不新增 `gate_excluded` 的取舍合理（rank 层前无统一逐源计数，硬造即假精度） |
| A8 | F6：UUID/Decimal → str，JSON-safe | **PASS** | 变异实锤：删 `isinstance(item,(UUID,Decimal))` 分支 → `test_default_projection_is_json_safe_for_uuid_decimal` **必红**（json.dumps 炸），还原复绿；dataclass 递归 + 标量 `{"value":"1.25"}` 两路径均断言 |
| A9 | F7：双向登记不改名 | **PASS** | situation_brief.py:223-227 字段注释 + decision_context.py 模块 docstring「命名消歧」节；不改名依据核实成立——`session_state_mixin` 多处 `existing_brief.get("decision_context")` 从持久化 state 读回，改名即孤儿化历史 brief；零行为变更（+5 注释行） |
| A10 | 回归全绿（契约 21 / C-02 消费面 / context 家族 / 消费方聚合器 35） | **PASS** | 独立实跑：契约 **21 passed**；C-02 面（test_context_sources + test_context_source_contract + test_context_pack_sources + test_situation_brief）**63 passed**；context 家族 4 文件 **27 passed**；契约+消费方/聚合器 **56 passed**（=21+35，与自报吻合）；ruff 5 文件 **All checks passed** |
| A11 | test_experience_actuator 预存失败与本卡无关 | **PASS** | 5 文件 `git checkout --` 还原到 HEAD @820c0203 后仍失败：`_fake_resolve_scoped_files() got an unexpected keyword argument 'include_group_documents'`——测试桩签名落后于 experience_actuator 生产代码（file resolution 域），与本卡 5 文件零交集（已还原 patch） |
| A12 | test_stage18_kill_switch 预存失败 + legacy bool 劫持机制 | **PASS（机制代码级核实）** | 基线还原后同样 2 failed；机制核实：`kill_switch.py resolve_settings_mode` L71-75——`configured == fallback("off")` 且 legacy bool True（settings.py:710/717/718 三者默认均 True）→ 返回 `enabled_mode("live")`；失败用例甚至**显式**配 `AURORA_STAGE18_PUSH_DELIVERY_MODE="off"` 仍被劫持为 live。**详见 B1** |
| A13 | 合入预演：patch vs 主仓 2375694c（含 C-03）零冲突 | **PASS** | 浅克隆 main @2375694c（C-03 已在 HEAD），`git apply --3way --check` 五文件全部 cleanly applied，与 business_metrics/retrieval 面零交集（克隆即删） |

## B1. 回执背书（供 Leader 入 KNOWN_CODE_DEBT_LEDGER）

**kill-switch legacy bool 劫持（真治理缺陷，非测试问题）**：
- 位置：`backend/app/core/kill_switch.py::resolve_settings_mode`——只要 `configured == fallback`（含**显式配置为 off**）且 `SPARKLE_*_ENABLED` legacy bool 为 True（默认全 True），即静默返回 `"live"`；显式 `"off"` 配置无法生效。
- 加重项：`KillSwitchBinding.enabled_legacy_modes` 字段（push_delivery 绑定设了 `frozenset({"live"})`，显然意图是约束 legacy 劫持方向）**全仓无任何读取点（死代码）**——守卫字段存在但从未接线。
- 影响：治理 tri-state 的 "off" 语义在默认配置下不可达；本卡 F1 的 `governance_off` 原因码在真实部署（未关 legacy bool）下永远不会出现，会被劫持成 `live` 后走 `unavailable` 路径——观测语义被同一缺陷连带削弱。
- 建议：开独立 P2 卡，修法二选一（区分「未设置」vs「显式 off」；或真正消费 `enabled_legacy_modes`）+ 补 `SPARKLE_*` 默认值迁移说明。

## N1. 备注（不阻塞）

- 降级 warning 走 **loguru**（`from loguru import logger`），caplog（stdlib）抓不到；本验收用 loguru sink 探针证实已真实发出。若未来观测面统一到 stdlib/OpenTelemetry，需过 bridge。Worker 测试断言计数器（不依赖日志通道），无脆弱性。
- `business_metrics.py` 全文件级预存在 black 漂移，本卡仅手工 +8 行同风格，合理。

## 实跑命令清单

```
git diff --stat / git apply --stat / diff <tree.diff> <changes.patch>      # A1
SECRET_KEY=test python3.11 -m pytest tests/contract/test_decision_context_contract.py -q          # 21 passed
SECRET_KEY=test python3.11 -m pytest tests/unit/test_context_sources.py tests/unit/test_context_source_contract.py tests/unit/test_context_pack_sources.py tests/unit/test_situation_brief.py -q   # 63 passed
SECRET_KEY=test python3.11 -m pytest tests/unit/test_context_pack.py tests/unit/test_context_focusing.py tests/unit/test_context_pack_rollout.py tests/unit/test_router_context_reader.py -q       # 27 passed
SECRET_KEY=test python3.11 -m pytest tests/contract/test_decision_context_contract.py tests/unit/test_memory_eval_service.py tests/unit/test_prompt_signal_closure.py tests/unit/orchestrator/test_insight_baseline_audit.py tests/unit/orchestrator/test_phase_a_durability_pack.py tests/unit/test_state_aggregator_service.py -q  # 56 passed
# 变异（cp /tmp 备份法，均已还原并 diff --stat 比对复原）：
#   context_pack.py off 编码→pass      → off 哨兵测试 FAILED ✓
#   decision_context.py __post_init__→pass + 删 UUID/Decimal 分支 → F3/F6 两测试 FAILED ✓
# 探针：loguru sink 临时测试（已删）→ shadow WARNING 实发 ✓
# 基线归因：5 文件 git checkout -- 还原 → test_experience_actuator 1 failed / test_stage18_kill_switch 2 failed（与本卡无关，已还原 patch）
git clone --no-local <main> /tmp/r1_merge_check && git apply --3way --check <patch>   # 五文件 cleanly applied，克隆即删
ruff check <5 改动文件>   # All checks passed
```

## 收工声明

wt2 树状态与开工一致（5 M + untracked `v3-output/V3-FIX-09/`，无 stash/reset/clean/切分支/commit/push）；/tmp 探针、备份、克隆已清；主仓与 dev DB 全程只读；未跑任何 HEAVY 任务。
