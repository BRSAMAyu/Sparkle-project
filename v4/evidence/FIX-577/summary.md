# FIX-577 summary — compose project 名钉死 + start_celery.sh 死债收口（2026-09-28，wtF577）

## 修了什么

1. **COMPOSE_PROJECT_NAME 钉死（FIX-563R1 发现2）**：`Makefile:13` `export COMPOSE_PROJECT_NAME ?= sparkle-project`（顶部、`.env` include 前，显式覆盖仍可穿透）；`scripts/dev/up.sh:17-18` 自带同值导出并派生 `COMPOSE_VOLUME_PREFIX`，门第二分支（`:53`）改读变量——worktree 起栈卷前缀不再漂移，门/supervisor 与实际 project 恒一致；`scripts/ops/service_supervisor.py:57` 预检前缀改读 env（默认 `sparkle-project_`，与原硬编码逐字节同值）。**红线达成：主 checkout 行为逐字节不变**——修复前后 `docker compose config` 渲染卷名 `cmp` 零差异，数据面零迁移延续。
2. **start_celery.sh 死债裁决 = (b) 标弃用**：裁决依据=该脚本无唯一价值面——能力面（worker concurrency=2/beat/flower）是 `make celery-up`（多 glm_batch worker、.env 真凭据、FLOWER_ENABLE、钉死网络）的严格子集，声明式路径 `docker-compose.celery.yml` 已在；修复反而养第三个分叉入口（即 F563R1 点名的 Makefile/脚本漂移形态）。文件头 DEPRECATED 块（死因+替代路径），正文不修不删，leader 改的三个 `sparkle_proj_* --name` 未回退；`scripts/devtools/README.md`、`QUICK_START_CELERY.md` 方式 B 同步弃用指向。
3. **RUNBOOK -p 纪律落地**：`scripts/RESTACK_RUNBOOK.md` 铁律节新增 FIX-577 注记——「直接 make 目标即安全；手工 compose 命令仍须 `-p` 或先 export」，来源行补 577。

## 怎么证明的

- 漂移复现：修复前 wtF577 裸 `compose config` 渲染 `wtf577_*` 7 卷 vs 主 checkout `sparkle-project_*`。
- 钉死生效：修复后 wtF577 经 Makefile 导出环境渲染 `sparkle-project_*`，`cmp` 对修复前 pin 基线 **BYTE-IDENTICAL**；卷名集与主 checkout 基线零差异；make recipe 实收 `COMPOSE_PROJECT_NAME=sparkle-project`。
- 门模式隔离验证：变量前缀匹配 `OK(ours)` / 漂移前缀落 die 分支。
- `make -n dev-up` exit 0；bash -n ×2、py_compile、ruff 全过；pytest supervisor 族 **17 passed**（断言零改动，env 默认值与原硬编码语义等价）+ o05 restore **14 passed**。

## 发现登记（不修，见 limitations.md）

- **高价值发现**：全仓 celery env URL `sparkle_redis:6379` 自 FIX-563 容器名分化后 DNS 悬空（服务名是 `redis`、容器名是 `sparkle_proj_redis`）——`make celery-up`/compose celery 路径的 worker 连不上 redis，宜独立小卡收口（四 compose+Makefile+文档同扫）。
- QUICK_START_CELERY.md 故障排查节活文档旧引用残留；其余 9 个脚本裸 `docker compose` 未钉死（fail-safe 向）。
