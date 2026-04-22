# Stage 40 SGW Dogfood Report

架构师:请做最终签字验收。
- SGW dogfood: CONDITIONAL
- Kill Switch 三态化完成率: 12/12
- Phase I Exit Gate 建议: patch

日期: 2026-04-22  
阶段: Stage 40  
报告状态: 已完成第一次真跑

PHASE_I_EXIT_READY: CONDITIONAL

## 前提与约束

- 目标文档 `docs/sgw/07_rl_system_handoff.md` 未出现在当前仓库快照中。
- 当前可执行入口为 `PYTHONPATH=scripts python3 -m sgw_v2.meta.meta_loop`。
- 该入口的 `--help` 仅公开 `db-path / persona-library / adversarial-playbook / max-iterations / exploration-every-n / convergence-window / seed`，未公开 Stage 40 调度文要求的 `--rl-mode`、`--rl-recipe`、`--dashboard`。
- 按 Stage 40 特殊规则，SGW dogfood 未全绿时不熔断，作为 Phase I 签字前待决项记录。

## Run Matrix

| Phase | 命令 | 目标 DB | 结果 |
| --- | --- | --- | --- |
| Phase A | `PYTHONPATH=scripts python3 -m sgw_v2.meta.meta_loop --db-path /tmp/stage40_off.db --persona-library scripts/sgw/persona_library.json --adversarial-playbook scripts/sgw/adversarial_playbook.json --max-iterations 3` | `/tmp/stage40_off.db` | `failed_assertion` |
| Phase B | `PYTHONPATH=scripts python3 -m sgw_v2.meta.meta_loop --db-path /tmp/stage40_shadow.db --persona-library scripts/sgw/persona_library.json --adversarial-playbook scripts/sgw/adversarial_playbook.json --rl-mode shadow --max-iterations 10 --dashboard` | `/tmp/stage40_shadow.db` | 当前 CLI 不支持 `--rl-mode` / `--dashboard` |
| Phase C | `PYTHONPATH=scripts python3 -m sgw_v2.meta.meta_loop --db-path /tmp/stage40_rl.db --persona-library scripts/sgw/persona_library.json --adversarial-playbook scripts/sgw/adversarial_playbook.json --rl-mode rl --rl-recipe fast_iteration --max-iterations 5 --dashboard` | `/tmp/stage40_rl.db` | 当前 CLI 不支持 `--rl-mode` / `--rl-recipe` / `--dashboard` |

## Phase A

目标:

- `runs / sessions / turns / audits` 表有数据
- `iterations` 表累计到 3
- 无崩溃

实际结果:

- 真跑时间: 2026-04-23
- 外层 `meta_loop` 完成了 3 次迭代循环，但每次都在启动 `scripts/sgw/sgw_orchestrator.py` 时失败
- 失败原因: `ModuleNotFoundError: No module named 'aiohttp'`
- DB 快照:
  - `runs=1`，且唯一 run 为 bootstrap seed
  - `sessions=0`
  - `turns=0`
  - `audits=0`
  - `iterations=0`
- 断言结果:
  - `non_bootstrap_runs=0 < 1`
  - `iterations=0 < 3`
- 对应日志:
  - `artifacts/stage40/sgw/Phase A.stdout.log`
  - `artifacts/stage40/sgw/Phase A.stderr.log`

## Phase B

目标:

- `rl_trajectories >= 10`
- `action_source` 全为 `rule`
- `reward_raw` 非空
- policy 未变化，bandit arms `alpha=1.0, beta=1.0`

实际结果:

- 当前 `meta_loop` CLI 不公开 shadow 模式参数，无法按调度文原命令执行
- 该缺口属于 Phase I Exit Gate 待决项，不在 Stage 40 中修改 RL 系统代码
- `/tmp/stage40_shadow.db` 未生成

## Phase C

目标:

- `rl_trajectories.action_source` 出现 `bandit` 或 `contextual`
- 至少一条 arm `pulls > 0`
- dashboard HTML 生成

实际结果:

- 当前 `meta_loop` CLI 不公开 RL 模式参数，无法按调度文原命令执行
- dashboard 入口未暴露为 CLI 能力
- `/tmp/stage40_rl.db` 未生成

## Supplemental Evidence

- `python3 scripts/sgw_v2/tests/test_rl_scaffolding.py`
  - 运行时间: 2026-04-23
  - 结果: `26/26 tests passed`
  - 作用: 证明 RL scaffolding 内部组件仍可自检通过，但不等价于三模式 dogfood pass

## 关键指标

- Phase A run id: 无有效 SGW run，只有 bootstrap seed
- Phase B run id: 未执行
- Phase C run id: 未执行
- Phase A DB path: `/tmp/stage40_off.db`
- Phase B DB path: `/tmp/stage40_shadow.db`
- Phase C DB path: `/tmp/stage40_rl.db`
- 汇总 JSON: `artifacts/stage40/sgw/dogfood_summary.json`

## 问题登记

1. `docs/sgw/07_rl_system_handoff.md` 在当前仓库快照缺失，Stage 40 调度引用无法直接对照。
2. `sgw_v2.meta.meta_loop` CLI 与 Stage 40 调度文不一致，缺少 `--rl-mode` / `--rl-recipe` / `--dashboard`。
3. Phase A 真跑卡在运行环境依赖缺失，当前 Python 3.14 解释器未安装 `aiohttp`，因此 `sgw_orchestrator.py` 无法启动。
4. SGW 真跑依赖 Sparkle backend、gateway、LLM provider，本机运行结果需以 `artifacts/stage40/sgw/*.log` 为准。

以上问题记入 Phase II backlog，不在本 Stage 修复 RL 系统代码。

## 结论

- 工程治理与 Exit Gate 文档可继续推进
- Phase A 已证明当前环境不满足最小 OFF regression 条件
- Phase B / C 已证明当前仓库入口还没有对外暴露 Stage 40 所需的 RL CLI
- SGW 三模式 dogfood 需要架构师决定:
  - `patch`: 暴露缺失的 CLI 能力或提供 Stage 40 认可的 wrapper
  - `revert`: 如认为 RL handoff 目标尚未到位
  - `ready with exception`: 以 CONDITIONAL 方式签字，允许 Phase II 从 CLI 能力补齐开始
