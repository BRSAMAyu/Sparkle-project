# FIX-577 limitations — 边界、残余与发现登记（2026-09-28，wtF577）

## 1. 本卡未修（scope 外残余，建议后续派卡/清扫）

1. **全仓 celery env URL `sparkle_redis:6379` DNS 死引用（本卡执行中发现，重要）**：FIX-563 后本仓 compose 网络上 redis 的可解析名=服务名 `redis` + 容器名 `sparkle_proj_redis`；`sparkle_redis` 与两者皆不匹配（FIX-563 前它靠旧容器名 `sparkle_redis` 解析，改名后悬空）。受影响面：`Makefile` celery-up 三处 env、`docker-compose.yml` celery_worker/celery_glm_batch_worker/celery_beat 的 REDIS_URL/CELERY_*/REDIS_HOST、`docker-compose.celery.yml` 同族——即 `make celery-up`/compose celery 路径的 worker 会起但连不上 redis（日志 fail-loud）。FIX-563 曾显式决定「URL 内 DNS 全部保留」，但该决定只核对了服务名面（sparkle_db/minio 仍成立），redis 的容器名/服务名分叉被漏掉。本卡不修：卡面仅 start_celery.sh；且该债需 config+运行期双验证，宜独立小卡（改 `sparkle_proj_redis` 或服务名 `redis`，四 compose+Makefile+文档同扫）。**本卡弃用裁决的「改用 make celery-up」指向在redis URL 债修复前，celery worker 实际不可用**——已在上游 README/QUICK_START 注记中如实陈述能力面对比，未声称该路径立即可用。
2. **QUICK_START_CELERY.md 故障排查节残排**（:181 `--network sparkle-flutter_default` 教例、`docker exec sparkle_redis`（现打 cosmos 侧容器，跨仓误击面）、`docker logs sparkle_flower`、预期输出块 `sparkle_celery_worker` 旧名）——活文档债，同上待文档清扫卡。方式 B 弃用注记本卡已落。
3. **其余裸 `docker compose` 脚本面未钉死**（清单见 grep_exemptions.md 扫描 C）：chaos_drill/blue_green_switch/deploy-prod/dev_local_stack/production_readiness_check/run_e2e_smoke/dev/{down,logs,reset}.sh。风险方向评估为 fail-safe（worktree 裸调命中本目录空 project→no-op），但若在这些目录显式设过同名 project 则行为待审；建议随下一次 ops 脚本卡统一收口。

## 2. 本卡验证边界

- 钉死生效证明为**静态渲染面**（compose config + make 导出环境实录）；`make dev-up`/`make celery-up` 真实 up 因「零容器操作」红线未跑（与 FIX-563 同口径：up.sh 新门未真跑，由 supervisor 同构预检真机 absent 分支+单测佐证）。
- supervisor `DATA_VOLUME_OWNER_PREFIX` 改为 import 时读 env：若未来在 `COMPOSE_PROJECT_NAME` 设为异值的环境跑 supervisor 测试，`test_fix557_owner_precheck_real_and_negative` 的 FakeOut「ours」断言（字面 `sparkle-project_`）会红——当前环境未设该变量，17 passed 实测无此问题；如遇之属测试环境卫生而非产品缺陷（设值者本就应预期预检跟随该值）。
- `make --eval` 在 Apple Xcode make 不可用，make 导出环境证明改用 `-f Makefile -f extra.mk` 双 makefile 法（等价：第二 makefile 的 recipe 在完整解析主 Makefile 后的导出环境中执行）。

## 3. 红线遵守

零 up/down/restart/run；docker 只读面仅 config 渲染与 pytest 内 docker inspect；主 checkout 零改动、零 .env 残留；不 push；临时哑值 .env 用后即删未入库。
