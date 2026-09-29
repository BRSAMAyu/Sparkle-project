# FIX-577 grep 扫描与豁免清单（2026-09-28，wtF577）

## 扫描 A：`sparkle-flutter_default` 残留（全仓，排除 .git）

命中 12 行，归因三类：

| 类别 | 命中 | 裁定 |
|---|---|---|
| **弃用正文（by design）** | `scripts/devtools/start_celery.sh:8,47,58,70` | 裁决 (b) 标弃用：头部 DEPRECATED 块明示勿用、正文按「史录保留」不动；:8 为弃由叙述，:47/58/70 为保留的死债正文 |
| **弃用叙述/指向文档** | `scripts/devtools/README.md:8`、`docs/03_功能实现指南/QUICK_START_CELERY.md:74` | 本卡新增的弃用注记自身（描述死因，非教唆使用） |
| **史录/台账（合法保留）** | `v4/evidence/FIX-563/review_r1.md:13`、`v4/evidence/FIX-563/verification.md:40`、`v3/06_agent_fleet/DYNAMIC_ISSUES.md:458` | 评审/验证实录与台账登记原文，一律不改写 |
| **⚠ 活文档残留（不豁免，登记 limitations）** | `docs/03_功能实现指南/QUICK_START_CELERY.md:181`（故障排查节 `docker run --network sparkle-flutter_default` 教例） | 活功能指南教死命令，属 577 同族死债但超本卡声明修复面（卡面仅 start_celery.sh 本体+方式 B 指向），已登记 limitations 待后续文档债清扫 |

**可执行脚本面 `sparkle-flutter_default` 残留**：start_celery.sh（弃用封存）之外 **0 行**。

## 扫描 B：COMPOSE_PROJECT_NAME 钉死覆盖面

`Makefile`、`scripts/dev/up.sh`、`scripts/ops/service_supervisor.py`、`scripts/RESTACK_RUNBOOK.md` 四件在位（grep -l 实录见 verification.md 引用的命令输出）。Makefile 顶部 `export ?=` 使全部 make 目标（dev-up/dev-up-all/celery-up 及经 make 拉起的 supervisor restart_cmd）继承钉死；up.sh 自带同值导出覆盖独立直调路径。

## 扫描 C：裸 `docker compose` 未钉死残余面（scope 外，登记不修）

`scripts/chaos_drill.sh`(14 处)、`scripts/blue_green_switch.sh`(3)、`scripts/deploy-prod.sh`(7)、`scripts/dev_local_stack.sh`(3)、`scripts/production_readiness_check.sh`(3)、`scripts/run_e2e_smoke.sh`(1)、`scripts/dev/{down,logs,reset}.sh`(5) ——均无 `COMPOSE_PROJECT_NAME` 引用。方向性评估：drill/logs 类在 worktree 裸调时命中本目录 project（无容器→no-op，fail-safe）；down/reset 类同理作用于错误 project 时为 no-op，不会误伤 `sparkle-project` 栈（compose 动词按 project 隔离）。详见 limitations.md。
