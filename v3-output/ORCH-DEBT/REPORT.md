# ORCH-DEBT · BP-3B 施工中申报的两个编排层缺陷修复报告

- 基线：main@06f63e0c（wt114）
- 交付：`v3-output/ORCH-DEBT/changes.patch`（在 HEAD 干净克隆上 `git apply --check` 通过）+ 本报告
- 测试：`backend/tests/orchestration/test_sufficiency_preflight_resilience.py`（新增，5 例）
- 改动面：`backend/app/orchestration/validation_engine.py`（+72/−9）+ 新测试文件；**零 commit / 零 push**

## 1. 根因与修法

### P2 · preflight `contradiction_map=None` 崩溃静默杀死 sufficiency 检查

**根因**：`validation_engine.py::_check_phase_a_planning_preflight` 中
`contradiction_map = insight_state.get("contradiction_map")`——当 `insight_state` 为 dict 但该键
**缺省或显式 None** 时得到 None，随后 `for item in contradiction_map` 推导抛
`TypeError: 'NoneType' object is not iterable`，被 `_check_sufficiency` 的兜底
`except Exception → "Sufficiency check failed, continuing"` 吞掉，**整个 sufficiency 检查链
（含澄清与 Phase A 硬停）无声跳过**，用户无感知失去充分性校验。
生产触发形状：`situation_brief.py` profile-missing 回退分支构建的 insight_state 无
`contradiction_map` 键（`insight_state` 缺省时反而是安全的——`None → []` 分支已覆盖，
唯独「insight_state 存在但键缺失/None」崩）。

**修法**（最小侵入，语义＝None=无矛盾数据）：非 list 一律按空表降级（跳过 contradiction
比对），sufficiency 链照常执行。原 `contradiction_map[:3] if isinstance(...)` 两处守卫保留不动。

**连带发现**：该崩溃不仅吞澄清，还会吞 Phase A ask 硬停本身（见红测试
`test_fresh_unsurfaced_ask_still_hard_stops_and_marks_surfaced` 修复前在硬停断言上失败）——
充分性校验与规划护栏同时失效，比 BP-3B 申报时评估的影响更重。

### P3 · 会话态残留 ask 硬停的 Phase A 路径

**根因**：Phase A ask-before-plan 硬停走 `_emit_fast_interaction` 早退，**不经过执行引擎的
response_metadata 回写**——上一回合问出的问题以 `planning_readiness_action=ask` 残留在
situation_brief.decision_context 中（经客户端 extra_context 回传）。下一回合（用户的回答）
`detect_planning_like_turn` 的 decision_context 分支判 planning_like → preflight 见 ask 再次
硬停 → 同一问题无限复读，用户回答永远送不到规划链路（会话死锁，即 BP-3B 报告「新发现 2」）。

**修法**（残留检测+清理，ask 一次性消费）：
1. **放行**：preflight 入口处，`planning_readiness_action == "ask"` 且
   `phase_a_ask_surfaced == "true"`（上一回合已问出）→ 清理残留
   （`planning_readiness_action`/`phase_a_guardrail` 清零）+ 落
   `phase_a_evaluation.ask_residual_consumed="true"` + observability 记录（`hard_stop=False`）→
   `return False` 放行，回答照常走 sufficiency → 规划链路。
2. **源头标记**：硬停问出时即在 decision_context 落
   `phase_a_ask_surfaced="true"` + `phase_a_ask_surfaced_at`（UTC ISO）并清零 pending ask；
   同时把消费后的 brief 按执行引擎同一约定（`ENABLE_CONTEXT_FOCUS_METADATA` 门控）随快响帧
   metadata 回传（`situation_brief` / `residual_decision_context` JSON）——修复残留态的传播通道，
   下一回合客户端不再回放残留 ask。
3. **红线不回退**：未问出（无 surfaced 标记）的新鲜 ask 硬停原样保留（BP-3B
   `test_phase_a_hard_stop_still_fires_for_genuine_planning_turn` 照旧绿）。

## 2. 红→绿统计

红测试：`tests/orchestration/test_sufficiency_preflight_resilience.py`（5 例；真实
`_check_sufficiency` 判定链 + 确定性 LLM 桩 + 启发式意图预测 + 生产形状残留 brief payload，
DB/网络零依赖，跟随 BP-3B 测试家族模式）。

| 测试 | 修复前（红） | 修复后（绿） |
|---|---|---|
| contradiction_map 缺省键 → sufficiency 澄清照常（P2 核心） | **FAIL**（TypeError 被吞，澄清无声消失） | PASS |
| contradiction_map 显式 None → 同上（P2 变体） | **FAIL** | PASS |
| 已 surfaced 残留 ask + 纯回答 → 放行+清理+消费落盘（P3 核心） | **FAIL**（再次硬停、残留未清） | PASS |
| 残留 ask 会话中带规划词的回答 → 不被 Phase A 硬停（P3 事故主形状） | PASS*（被 P2 崩溃掩盖而假绿） | PASS（真实恢复语义） |
| 新鲜未问出 ask → 硬停不回退 + surfaced 标记 + 快响帧回传清理后 brief | **FAIL**（硬停反被 P2 崩溃吞掉） | PASS |
| **合计** | **3 failed / 1 passed / 1 假绿** | **5 passed** |

\* 注：修复前 P2 崩溃会把进入 preflight 的所有回合（含 P3 场景）全部吞掉，因此部分断言呈现
假绿——P2 单独修复后（P3 未修时）该测试转为真红，最终双修后全绿。红→绿为「红→P2 中间态→双修绿」
三段验证，过程留痕于 git 无、以本行为证。

回归（`SECRET_KEY=test python3.11 -m pytest`，绝对路径，哑值 env）：

| 套件 | HEAD 基线（/tmp 干净克隆） | 修复后 | 判定 |
|---|---|---|---|
| `tests/orchestration/` 全目录 | 36 failed, 153 passed, 26 errors | 36 failed, **158 passed**, 26 errors | FAILED/ERROR 集**逐项 diff 为空**；+5 passed 即本卡新测试 |
| BP-3B 红线 `test_correction_priority_over_planning.py` | 7 passed | **7 passed** | 纠正优先序零回退 |
| unit/orchestrator + process_stream_integration + circuit_breaker 组合 | 6 failed, 149 passed | 6 failed, 149 passed | 失败集逐项一致（process_stream 6F 为存量债） |
| `tests/integration/test_phase5_orchestrator_north_star_acceptance.py` | 1 passed, 1 skipped | 1 passed, 1 skipped | Phase A 硬停帧元数据契约（clarification_source=phase_a / ask_before_plan）保持 |
| `tests/context_eval/` | 17 passed | 17 passed | 全绿 |
| ruff / black(120) | validation_engine 存量 7 处 black 历史 hunks | ruff 全过；black hunks 仍恰 7 处（全在未触碰区域） | 零新增违规 |

## 3. 基线对照结论（克隆基线法）

按 AGENTS.md 并发安全规程以 `git clone wt114 /tmp/orchdebt-baseline`（只含 HEAD@06f63e0c）
取基线，与本卡修复后同一选择集逐项 diff：

- `tests/orchestration/` 全目录 FAILED/ERROR 集 **62 行逐项一致（diff 为空）**——存量 36F/26E
  环境债零新增、零掩盖；passed 153→158，增量恰为本卡 5 个新测试。
- unit+process_stream+circuit_breaker 组合失败集 **逐项一致**。
- `backend/app/gen` 为 worktree 预置缺口，已从主仓拷贝补齐（gitignored 构建产物，不入 patch）。

## 4. 红线面核查

- **BP-3B 纠正优先级**：7 例全绿，`planning_intent.py` / `_normalize_sufficiency_intent_type`
  未动一字。
- **sufficiency 通道语义零重构**：仅两处缺陷修复——P2 是 4 行防御性归一化；P3 只动
  `_check_phase_a_planning_preflight` 内部（新增放行分支 + 硬停分支标记/清理 + 快响帧
  metadata），澄清/确认帧协议、`_emit_fast_interaction` 本体、sufficiency_checker 零改动。
- **冲突面**：wt109-113 并行卡均不触碰 orchestration/validation（树内改动仅本卡 2 文件）。

## 5. 收工核查声明

- 自起进程：无（全程未起引擎/网关/模拟器/浏览器/Gradle；仅 pytest）。
- `/tmp` 产物已清：`orchdebt-baseline/`、`orchdebt-applytest/`、
  `orchdebt_baseline_summary.txt`、`orchdebt_baseline_failures.txt`、`orchdebt_postfix_*`、
  `orchdebt_extra_*`、`orchdebt_final*_summary/failures.txt`。
- 主仓（Sparkle-project）只读（仅拷贝 gitignored 的 `backend/app/gen` 构建产物到本 worktree
  与 /tmp 克隆）；改动全部在 wt114 树内；未 commit / 未 push / 未动 index。
- 测试态说明：pytest 全程 `SECRET_KEY=test` + `SHADOW_PREDICTION_MODE=heuristic`（哑值 env，
  经 monkeypatch 自动回收）；无 DB/Redis 依赖（orchestrator_factory 内存桩）。
- 套件级注记（顺手修的自保缺陷，不入 patch 主张）：`test_orchestrator_process_stream_integration.py`
  多个用例向 `sys.modules` 注入假 `shadow_prediction_service` 且不回收，字母序靠后的测试文件
  全部被污染——本卡测试文件内置钉回真实模块的防御；存量污染治理建议另立卡。
