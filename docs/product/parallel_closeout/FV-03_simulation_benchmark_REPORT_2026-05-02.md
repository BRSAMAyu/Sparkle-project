# FV-03 · SimulationLab/SparkleGoalBench CI 门禁 · 完成报告

**Agent**: codex-agent-03
**Branch**: codex/FV-03-simulation-benchmark
**Date**: 2026-05-02
**Status**: COMPLETED

## 1. 5/5 标准达成情况

| # | 标准 | 状态 | 证据 |
|---|------|------|------|
| 1 | `run_benchmark_suite(suite_name)` 调用 SparkleGoalBench、写 `simulation_runs`、产生 BenchmarkReport | Done | `backend/app/services/simulation_runner.py:71` 定义 `BenchmarkReport`；`:405` 实现 runner；`:313` 用 Core insert 写 `simulation_runs` |
| 2 | CLI `python -m backend.scripts.run_simulation_benchmark --suite=full` | Done | `backend/scripts/run_simulation_benchmark.py:16` 参数入口；`:27` async main；`:36` 默认 DB 写入，`:29` 支持 no-DB 验证 |
| 3 | CI 门禁 job `simulation-benchmark` | Done | `.github/workflows/ci.yml:285` 新 job；`:309` 检测敏感文件；`:347` 执行 SparkleGoalBench gate |
| 4 | 失败规则：高风险阻断、中等警告、趋势退化 >10% 阻断 | Done | `backend/app/services/simulation_runner.py:237` gate decision；`:243-264` risk/trend 分级 |
| 5 | 报告产出 `docs/benchmarks/<date>_<commit>.md` | Done | `backend/app/services/simulation_runner.py:343` markdown renderer；验证产物 `docs/benchmarks/2026-05-02_local-fv03-final.md` |
| 6 | Celery 周任务 `run_weekly_benchmark` 周日 03:00 | Done | `backend/app/core/celery_tasks.py:2790` task；`backend/app/celery_schedule.py:94` 周日 03:00 schedule |
| 7 | Prometheus 指标 + Grafana | Done | `backend/app/services/simulation_runner.py:33` metrics；`monitoring/prometheus.yml:35` scrape job；`monitoring/grafana/dashboards/simulation_lab.json` dashboard |
| 8 | 单测 + 集成测 | Done | `backend/tests/services/test_simulation_runner.py:16` DB persistence；`:43` high-risk block；`:84` CLI |

## 2. 文件变更清单

```text
.github/workflows/ci.yml
backend/app/celery_schedule.py
backend/app/core/celery_tasks.py
backend/app/services/simulation_runner.py
backend/app/signals/simulation_lab.py
backend/scripts/run_simulation_benchmark.py
backend/tests/services/test_simulation_runner.py
docs/benchmarks/2026-05-02_local-fv03-final.md
monitoring/grafana/dashboards/simulation_lab.json
monitoring/prometheus.yml
```

## 3. 测试证据

### 单测 / 集成测

```text
cd backend && pytest tests/services/test_simulation_runner.py -q
3 passed in 0.79s
```

```text
cd backend && pytest tests/unit/test_signal_spine.py -q -k "p4_3"
18 passed, 942 deselected in 1.18s
```

### CLI / Benchmark

```text
PYTHONPATH=backend backend/.venv/bin/python -m backend.scripts.run_simulation_benchmark --suite=full --skip-db --reports-dir docs/benchmarks --commit local-fv03-final
status=passed total=24 passed=24 failed=0 pass_rate=1.0 report=docs/benchmarks/2026-05-02_local-fv03-final.md
```

### Lint

```text
ruff check backend/app/services/simulation_runner.py backend/scripts/run_simulation_benchmark.py backend/tests/services/test_simulation_runner.py backend/app/signals/simulation_lab.py backend/app/celery_schedule.py backend/app/core/celery_tasks.py
All checks passed!
```

## 4. 用户视角变化

在策略、Aurora、Marketplace、Skill 相关改动进入 PR 时，Sparkle 现在会自动跑 24 个固定目标系统回归场景；高风险场景失败会阻断合并，中等风险失败会给出警告，基准报告会沉淀为 markdown 与 `simulation_runs` 历史记录。

## 5. 与其他卡片的协调

- 共享文件 `backend/app/core/celery_tasks.py`：仅追加 FV-03 `run_weekly_benchmark`。
- 共享文件 `backend/app/celery_schedule.py`：仅追加 FV-03 周任务块。
- 共享文件 `monitoring/prometheus.yml`：仅追加 `sparkle_simulation_lab` scrape job。
- 留给 Architect：当前 worktree 同时含其他 FV agent 的大量未提交修改，本卡未尝试回滚或归并他人文件。

## 6. 已知限制 / 后续

- `run_simulation_benchmark` 的默认 DB 模式依赖 CI 先完成 Alembic migration；本地验证使用 SQLite fixture 覆盖了 `simulation_runs` 写入路径。
- `backend/app/celery_schedule.py` 是本任务卡指定的 schedule 文件；若生产只读取 `celery_app.conf.beat_schedule`，Architect 收尾时需要把该 schedule 接入统一 beat 装配。

## 7. 验收命令一键回放

```bash
cd /Users/brsama/code/GitHub/Sparkle-project
ruff check backend/app/services/simulation_runner.py backend/scripts/run_simulation_benchmark.py backend/tests/services/test_simulation_runner.py backend/app/signals/simulation_lab.py backend/app/celery_schedule.py backend/app/core/celery_tasks.py
cd backend && pytest tests/services/test_simulation_runner.py -q
cd backend && pytest tests/unit/test_signal_spine.py -q -k "p4_3"
cd /Users/brsama/code/GitHub/Sparkle-project
PYTHONPATH=backend backend/.venv/bin/python -m backend.scripts.run_simulation_benchmark --suite=full --skip-db --reports-dir docs/benchmarks --commit local-fv03-final
```
