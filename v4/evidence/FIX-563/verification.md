# FIX-563 verification — 命令与 exit code 实录（2026-09-29，wtF563）

## 1. compose 静态校验（红线要求：config 不 up）

```
docker compose -f docker-compose.yml config                     # exit 0（临时哑值 .env 注入后；env_file 指令要求 .env 存在，校验后已删）
docker compose -f docker-compose.yml -f docker-compose.services.yml config   # exit 0（overlay 成对校验；services 单独缺 redis 服务属既有结构）
docker compose -f docker-compose.celery.yml config              # exit 0
docker compose -f docker-compose.prod.yml config                # exit 0（哑值注入 IMAGE_TAG/JWT_*/MINIO_*/ALERTMANAGER_* 等 required 变量）
```
渲染输出核对（四场景合并去重）：`container_name` 全部 `sparkle_proj_*`（54 条渲染含 overlay 重复），旧名（非 proj）计数 **0**；`sparkle_proj_db`/`sparkle_proj_redis`/`sparkle_proj_minio` 三个数据面新名均在 main/celery/prod 渲染中出现。

## 2. grep 零残留（分母与口径）

- 全仓 grep（排除 .git）旧名家族 → 1073 行，逐类归因见 `grep_exemptions.md`（服务名/DNS 与历史记录合计，**合法保留**）。
- 专项扫描「可执行容器操作 + 旧容器名」（`docker exec|inspect|logs|stop|start|restart|rm|run|kill|pause|unpause … sparkle_<旧名>` 与 `--name sparkle_<旧名>`，排除 v3-output/v4-evidence/docs/v3/mobile-docs 史录域）→ **0 行**（修复 start_celery.sh 提示 ×2、celery_alerts.yml runbook 提示 ×1 后复扫归零）。
- dash 形旧债（`sparkle-db`/`sparkle-redis`/`sparkle-gateway`…）代码面归零；残余命中均为 k8s 资源名 / JWT issuer / 镜像名 / 本卡注记，非 compose 容器名。

## 3. 语法与测试

| 项 | 命令 | 结果 |
|---|---|---|
| bash -n ×13 | `bash -n scripts/dev/{up,healthcheck,smoke,logs}.sh scripts/dev_local_stack.sh scripts/run_e2e_smoke.sh scripts/dev-stage3.sh scripts/devtools/{run_j01_first3_measurement,setup_env,start_celery}.sh scripts/{backup_prod_data,restore_prod_data,install_backup_cron,deploy/bootstrap}.sh` | 全 OK |
| python 编译 ×10 | `python3 -m py_compile`（supervisor+test+devtools 7+celery_acceptance+collect_logs） | 全 OK |
| make 解析 | `make -n dev-up` | exit 0 |
| supervisor 门测试 | `pytest scripts/tests/test_service_supervisor.py scripts/tests/test_supervisor_probe.py -q` | **17 passed**（1.52s；owner 预检用例按新语义矩阵重写后全绿） |
| o05 恢复守卫 | `pytest scripts/tests/test_o05_restore_consistency.py -q` | **14 passed**（restore 脚本文本断言与新默认容器名兼容） |
| 监控 YAML ×7 | venv pyyaml safe_load（prometheus/promtail/prometheus-celery/targets 4+2 新增+2 backend） | 全 valid |
| Grafana JSON | `python3 -c json.load(sparkle-data-services.json)` | valid |
| ruff | 改动 py 两件 | All checks passed（exit 0）；scripts/devtools 21 条为基线既有（stash 对比同数） |
| black --check 120 | supervisor+test 两件 | would-reformat 2 件——**stash 基线同判**（P03-R2 已登记的仓库级 black 版本工件，零新增漂移） |
| 基线对照 | `git stash` 后复测 ruff/black → `git stash pop` | 恢复无损，diff 完整 |

## 4. 真机只读复核（红线：不触碰）

- `docker ps`（动手前基线与收尾复核一致）：`sparkle_db` / `sparkle_redis` / `sparkle_minio` 全程 `Up 19 hours (healthy)`，镜像 `sparkle-cosmos-sparkle_db` 等——现役栈属 sparkle-cosmos 项目，本卡全程零重启零重建零改名。
- `scripts/dev/up.sh` 新门未真跑（会 up 容器，踩红线）；门逻辑由 supervisor 同构预检（`check_data_plane_owner` 真机 absent 分支）+ 单测覆盖佐证。

## Errata (leader, 2026-09-30, R1 发现1 收口)
- 「可执行容器操作+旧名残留 0」声称被 R1 多行感知扫描证伪：start_celery.sh 三处 `docker run \` 续行后的 `--name sparkle_celery_worker/beat/flower` 漏检（单行 grep 局限）。已 leader 快修改名 sparkle_proj_*（bash -n 过+多行重扫全仓零残留）；同脚本 `--network sparkle-flutter_default` 与 env URL 旧引用系改项目名后不可达的死债（fail-loud），归 FIX-577。
