# Stage 40 SGW Dogfood Report

架构师:请做最终签字验收。
- SGW dogfood: CONDITIONAL（已修复 CLI/依赖层障碍，真跑仍需完整后端栈）
- Kill Switch 三态化完成率: 12/12
- Phase I Exit Gate 建议: ready with exception

日期: 2026-04-23  
阶段: Stage 40（Phase I 收尾集成）  
报告状态: 二次刷新，记录整合分支 `integration/phase-i-exit` 真跑

PHASE_I_EXIT_READY: CONDITIONAL

## 前提与约束

- 当前可执行入口为 `PYTHONPATH=scripts python3 -m sgw_v2.meta.meta_loop`（Stage 40 dispatch 原入口）。
- 整合分支已补齐：
  - `backend/requirements.txt` 补入 `aiohttp>=3.9.0`
  - `sgw_v2.meta.meta_loop` CLI 补齐 `--rl-mode {off,shadow,rl}`、`--rl-recipe {default|compliance_focus|authenticity_focus|fast_iteration|stress_test}`、`--dashboard`
- SGW 三模式真跑仍依赖完整 Sparkle 后端栈（Postgres + Redis + LLM provider + JWT SECRET_KEY），不能在纯脚本环境内完成。
- 按 Stage 40 特殊规则，SGW dogfood 未全绿时不熔断，作为 Phase I 签字前待决项登记。

## Run Matrix

| Phase | 命令 | 目标 DB | 结果 |
| --- | --- | --- | --- |
| Phase A | `PYTHONPATH=scripts python3 -m sgw_v2.meta.meta_loop --db-path /tmp/stage40_off.db --persona-library scripts/sgw/persona_library.json --adversarial-playbook scripts/sgw/adversarial_playbook.json --max-iterations 3` | `/tmp/stage40_off.db` | meta_loop 启动 → sgw_orchestrator 启动 → `aiohttp` 不再缺失 → 真实 boundary = 后端栈未起（SECRET_KEY + DB schema） |
| Phase B | `PYTHONPATH=scripts python3 -m sgw_v2.meta.meta_loop --db-path /tmp/stage40_shadow.db --persona-library scripts/sgw/persona_library.json --adversarial-playbook scripts/sgw/adversarial_playbook.json --rl-mode shadow --max-iterations 10 --dashboard` | `/tmp/stage40_shadow.db` | CLI 已公开 `--rl-mode shadow` / `--dashboard`，命令可被 meta_loop 接受，真跑仍需后端栈 |
| Phase C | `PYTHONPATH=scripts python3 -m sgw_v2.meta.meta_loop --db-path /tmp/stage40_rl.db --persona-library scripts/sgw/persona_library.json --adversarial-playbook scripts/sgw/adversarial_playbook.json --rl-mode rl --rl-recipe fast_iteration --max-iterations 5 --dashboard` | `/tmp/stage40_rl.db` | CLI 已公开 `--rl-mode rl` / `--rl-recipe` / `--dashboard`，命令可被 meta_loop 接受，真跑仍需后端栈 |

## Phase A

目标:

- `runs / sessions / turns / audits` 表有数据
- `iterations` 表累计到 3
- 无崩溃

实际结果（整合分支 `integration/phase-i-exit`，2026-04-23 刷新）:

- 外层 `meta_loop` 成功完成 3 次迭代循环调度
- 依赖层修复已生效：
  - `aiohttp` 可直接 import（从 `backend/requirements.txt` 注入后环境层 import OK）
  - `sgw_orchestrator.py` 可被 subprocess 启动，不再 `ModuleNotFoundError: No module named 'aiohttp'`
- 新的真跑边界:
  - `SECRET_KEY` 由 pydantic Settings 校验强制要求
  - 即便注入 `SECRET_KEY` + `DATABASE_URL=sqlite+aiosqlite:///:memory:` 后，`users` 表 schema 缺失，orchestrator 仍无法完成首个 session
- DB 快照（当前环境，缺完整后端栈）:
  - `runs=1`（bootstrap seed）
  - `sessions=0`
  - `turns=0`
  - `audits=0`
  - `iterations=0`
- 对应日志:
  - `artifacts/stage40/sgw/PhaseA.stdout.log`
  - `artifacts/stage40/sgw/PhaseA.stderr.log`

## Phase B

目标:

- `rl_trajectories >= 10`
- `action_source` 全为 `rule`
- `reward_raw` 非空
- policy 未变化，bandit arms `alpha=1.0, beta=1.0`

实际结果:

- CLI 已公开 `--rl-mode shadow` / `--dashboard` 参数，Stage 40 调度命令可被 meta_loop 接受
- 真跑同 Phase A，受限于后端栈未起动
- `/tmp/stage40_shadow.db` 暂未生成

## Phase C

目标:

- `rl_trajectories.action_source` 出现 `bandit` 或 `contextual`
- 至少一条 arm `pulls > 0`
- dashboard HTML 生成

实际结果:

- CLI 已公开 `--rl-mode rl` / `--rl-recipe` / `--dashboard`，Stage 40 调度命令可被 meta_loop 接受
- 真跑同 Phase A，受限于后端栈未起动
- `/tmp/stage40_rl.db` 暂未生成

## Supplemental Evidence

- `python3 scripts/sgw_v2/tests/test_rl_scaffolding.py`
  - 结果: `26/26 tests passed`
  - 作用: 证明 RL scaffolding 内部组件自检通过，不等价于三模式 dogfood pass
- `bash scripts/run_all_rule_guards.sh`
  - 结果: 全部 PASS（Rule K / Y / Z 系 / AS / AW / AZ / BA / AT / AU / Z-EPISODIC / AB / AC / AD / AE / AF / AG / AH / AI / AJ / AK / AL / AM / AN / AQ / AO / AP / AR / AX / AY / BB / BC / AV / BD）
  - 证明 Phase I Exit Gate 的治理层（Rule K→BD）已全绿

## 关键指标

- Phase A run id: 无有效 SGW run，只有 bootstrap seed
- Phase B run id: 未执行
- Phase C run id: 未执行
- Phase A DB path: `/tmp/stage40_off.db`
- Phase B DB path: `/tmp/stage40_shadow.db`
- Phase C DB path: `/tmp/stage40_rl.db`
- 汇总 JSON: `artifacts/stage40/sgw/dogfood_summary.json`

## 问题登记

1. SGW 三模式真跑需要完整 Sparkle 后端栈（Postgres+Redis+LLM+JWT SECRET_KEY），纯脚本 CI 环境无法满足，登记为 Phase II 首项。
2. `sgw_v2.meta.meta_loop` CLI 已补齐，但 sgw_orchestrator 仍依赖 backend Settings；是否要让 SGW 在无 backend 下能独立跑，需要架构师裁决（Phase II 议题）。
3. Go 代码生成产物（`backend/gateway/gen/…`）未落盘（`buf.gen.yaml` 不在当前仓库快照），不影响 Phase I Exit Gate 的治理层，但阻塞 `go build`。登记为 Phase II 首项 DevOps。

以上问题记入 Phase II backlog，不在本 Stage 修复 RL 系统代码。

## 结论

- 工程治理与 Exit Gate 文档可继续推进。
- Rule BD 自动检查：PASS（CONDITIONAL）
- CLI / 依赖层障碍已在整合分支 `integration/phase-i-exit` 清零
- 真跑仍需完整后端栈，故 dogfood 真跑结果保持 CONDITIONAL
- SGW 三模式 dogfood 签字建议:
  - `ready with exception`: 以 CONDITIONAL 方式签字，Phase II 从「后端栈起动 + SGW 三模式真跑」开始收尾。
