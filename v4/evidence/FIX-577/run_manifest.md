# FIX-577 run manifest — compose project 名钉死 + start_celery.sh 死债收口

- **日期**：2026-09-28（wtF577）
- **分支**：`fix/v4/f577-project-name-pinning`（自 main@48190526 开出，不 push）
- **worktree**：`/Users/brsama/code/GitHub/wtF577`
- **来源**：v3/06_agent_fleet/DYNAMIC_ISSUES.md V3-FIX-577（FIX-563R1 发现2 + 死债）；证据基础 v4/evidence/FIX-563/review_r1.md 发现1/发现2 节
- **红线**：零容器生命周期操作（无 up/down/restart/run）；只读面仅 `docker compose … config` 渲染、`docker inspect`（经 pytest owner 预检真机用例）、`make -n` 干跑；主 checkout 全程零改动（收尾 `git status` 0 dirty）；不 push；临时哑值 `.env` 校验后即删，未入库。

## 修复面（3 项）

1. **COMPOSE_PROJECT_NAME 钉死**
   - `Makefile:13`：`export COMPOSE_PROJECT_NAME ?= sparkle-project`（顶部、`-include .env` 之前——`.env` 显式值与外部环境覆盖仍生效，`?=` 只兜底）。
   - `scripts/dev/up.sh:17-18`：脚本自带 `export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-sparkle-project}"` + 派生 `COMPOSE_VOLUME_PREFIX`；`:53-54` 门第二分支由硬编码 `*sparkle-project_*` 改 `*"$COMPOSE_VOLUME_PREFIX"*`（`sparkle-cosmos_*` die 分支保持字面硬编码——他仓前缀与本项目名无关）。
   - `scripts/ops/service_supervisor.py:57`：`DATA_VOLUME_OWNER_PREFIX = os.environ.get("COMPOSE_PROJECT_NAME", "sparkle-project") + "_"`（默认值与原硬编码逐字节同）。
2. **start_celery.sh 死债裁决 = (b) 标弃用**
   - 文件头 DEPRECATED 块（死因：`--network sparkle-flutter_default` 为已消亡项目名 + env URL `sparkle_redis:6379` 在本仓网络不可解析）；正文不改不删。
   - 指向文档同步：`scripts/devtools/README.md:8` 表行、`docs/03_功能实现指南/QUICK_START_CELERY.md` 方式 B 节改弃用注记并指向 `make celery-up` / `docker-compose.celery.yml`。
3. **RUNBOOK -p 纪律落地**：`scripts/RESTACK_RUNBOOK.md:28` 铁律节新增「FIX-577 注记（钉死已落地）」；来源行补 FIX-577。

## 明确不做（scope 外）

- 其余裸 `docker compose` 脚本面（chaos_drill/blue_green_switch/deploy-prod/dev_local_stack/production_readiness_check/run_e2e_smoke/dev/{down,logs,reset}.sh）不动，登记 limitations。
- 全仓 celery env URL 的 `sparkle_redis:6379` DNS 死引用（Makefile celery-up、docker-compose*.yml）不动，登记 limitations（发现登记，待派卡）。
- QUICK_START_CELERY.md 故障排查节残排旧引用不动，登记 limitations。
