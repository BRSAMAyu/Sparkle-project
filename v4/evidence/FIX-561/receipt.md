# FIX-561 收据 — cancel×in-flight failed bucket 对账

2026-09-29 · wtF561 · 分支 `fix/v4/f561-cancel-inflight`（base `ce7ef08b`，未 push）

## 缺陷（台账 V3-FIX-561 / V4-I08 review_r2 靶5 C-2）

用户取消撞在飞写工具（竞窗 ≤ ~120s tool timeout）时，`build_evidence` 的 `else`
兜底把 `in_progress` 账本行吞进 **failed** 桶（诚实标签应为 X-09 自己的崩溃语义
**interrupted / outcome unknown**）；`_side_effect_reconciliation` first-wins
不重算，使误标投影终身驻留——恢复 pass 修正账本真值后 run 面仍 `failed=1`。

## 亲复现（修前，探针实测值）

RUNNING→AWAITING_USER run + 1 succeeded 写行 + 1 in_progress 写行 → `cancel()`：

```
succeeded_steps=1, failed_steps=1, interrupted_steps=0
failed_entries=[{tool: deep_task_write, finished_at: None, error_type: None}]
```

与靶5 亲测逐值一致；`finished_at=None` + `error_type=None` = 从未完成过的调用
被标失败——误标铁证。

## 修法与裁决

台账两选项：**(A)** `_side_effect_reconciliation` 物化前跑
`reconcile_stale_in_progress`；**(B)** X-09 owner 修 `build_evidence` 桶化。
**选 (B)**（台账明列的授权选项；owner 裁决由本派单 fix agent 代行，理由入
run_manifest 供复核）：

- (A) 关不了窗：安全陈旧阈值 ≥ max(300s, registry 最长超时×2+60) 恒大于竞窗
  （≤~120s），窗内行不陈旧、不收敛，误标照旧；强传 0 阈值则违反
  `reconcile_stale_in_progress` 自身不变量（"阈值永远大于最慢合法执行的 2 倍"）
  且全局改写**其他活跃 run** 的在飞账本行（真值外溢）。
- (B) 纯函数改桶（确定性不变）、账本行零改写、与 `TOOL_CALL_STATUSES` 词表语义
  对齐（interrupted = 执行中断且效果不可核实），并一致修正全部消费面
  （cancel/budget result_ref + GET tool-calls 的 partial_completion 读面——
  后者修前对活跃 run 的在飞工具同样误标 failed）。

## 改动

- `backend/app/services/tool_call_ledger_service.py::build_evidence`：
  `elif row.status in ("interrupted", "in_progress")` → interrupted/outcome-unknown；
  durable_progress / compensation_hints 不变（只由 succeeded 写行贡献）。
- 测试纯新增 86 行（`git diff` 删行数=0，契约测零削弱）：
  - `tests/unit/test_x09_failure_recovery.py`：build_evidence 三桶语义单测
    （in_progress→interrupted/unknown + 真 failed 照实 + 补偿提示只认 succeeded）；
  - `tests/unit/test_v4_i08_deep_task_return_control.py`：cancel×in-flight 场景测
    （投影 interrupted=1/failed=0 + 物化不改账本 + 恢复修正后误标不驻留）
    + 反例锚（真 failed 行照实落 failed 桶）。

## 验证

| 面 | 结果 |
| --- | --- |
| 修前红（3 新测） | 2 failed, 1 passed（正例红=复现；反例锚两态皆真） |
| mutation 自验（stash 修复→同三测） | 2 failed, 1 passed（变异必红）；pop 后 9 passed |
| 受影响面 12 文件（I08 同组） | **276 passed**（273 既有 + 3 新增，185.54s，零回归） |
| mypy 棘轮 | 59 ≤ baseline 77；改动文件零条（主检出/worktree ±1 差异经逐条 diff 核实为无关文件的环境噪声） |
| ruff / black | All checks passed / 3 files unchanged |
| API/OpenAPI 门 | 未触 api/；`to_result_ref` dict 键集不变，无 schema 形变 |

## 边界与残留

- first-wins 不重算契约保留：executor 事后 finalize 在飞行为 succeeded 时，
  账本权威面显示 succeeded、run 面投影保持 interrupted/unknown（物化时点诚实
  语义，账本恒可审计）——与靶5 "账本权威恒可审计" 口径一致。
- 语义分工未动：`reconcile_stale_in_progress` / executor 两阶段收敛 /
  PARTIAL 升格（durable_progress）零接触。
