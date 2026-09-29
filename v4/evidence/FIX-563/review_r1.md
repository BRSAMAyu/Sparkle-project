# FIX-563 独立审查 receipt — R1（未参与实现）

- 审查人：R1（独立会话，2026-09-29）
- 对象：`e32f9043`（61 文件 +541/−256），base `0949da60`，台账头 `3ce16fb7`
- 红线遵守：全程零 up/down/restart/run；对 Docker 仅 `config`（静态渲染，/tmp 沙箱）/`ps`/`inspect`/`volume ls`（只读）；门逻辑四象限用 PATH shim + 只读 replay 实证，未触碰现役栈

## VERDICT: PASS_WITH_CHALLENGES

核心交付（数据面 db/redis/minio 单侧分化 + 三数据面预检门 + supervisor 语义反转 + RUNBOOK 权威对照表）全部实证成立，FIX-557 事故形态在本仓 compose 路径结构性根除；但发现 1 处豁免清单外、且在修复声明范围内的可执行旧名残留，直接证伪 verification.md 的「可执行容器操作+旧名残留 0」头条声称，需补修后方可闭卡。

## 编号发现

1. **HIGH — `scripts/devtools/start_celery.sh:23,34,46`**：三处 `docker run --name sparkle_celery_worker / sparkle_celery_beat / sparkle_flower` 仍创建旧名容器。复现：`grep -n -- '--name sparkle_' scripts/devtools/start_celery.sh`（3 行命中；多行续行形态，修复方单行扫描漏检，其 `--name sparkle_<旧名>` 归零声称不成立）。该三名为 sparkle-cosmos 仓 `docker-compose.celery.yml:13/36/53` 的 compose 容器名——正是本卡要根除的跨仓碰撞面，且本文件在 run_manifest 声明的修复清单内（同文件只修了 docker ps 探测与两行 echo 提示，`--name` 未同步；Makefile 平行的手工 celery 栈已改 `sparkle_proj_*`，两入口现不一致）。缓解面：容器冲突时 `docker run` fail-loud（不静默抢注）、脚本只 bind-mount `./backend` 不挂他仓卷、主文档路径（Makefile）已正确——故降为挑战级而非 FAIL 级。**要求：补修三处 `--name` + `--network`（`sparkle-flutter_default` 系更早旧债，Makefile 用 `sparkle-project_default`），并以多行感知正则重跑「可执行容器操作+旧名」扫描后修正 verification.md §2。**
2. **MEDIUM-LOW — project 名未钉死，门/RUNBOOK 前缀假设只在主 checkout 成立**：`scripts/dev/up.sh:44` 门与 `scripts/ops/service_supervisor.py` owner 检查硬编码卷前缀 `sparkle-project_`，该前缀=compose 默认 project（目录名小写化），仅主 checkout `/Users/brsama/code/GitHub/Sparkle-project` 成立；从任务 worktree（如 wtF563）起栈则卷为 `wtf563_*`，合法自有栈会触发门 `*` 分支 die（up.sh:58）与 supervisor 误报 RED。两向均 fail-loud（安全向），无数据风险，但 RUNBOOK「永远先 -p」纪律在仓库自身入口（Makefile:26/32 无 `-p`、无 `COMPOSE_PROJECT_NAME`）零落地，且 limitations 未披露。建议后续卡片统一 `-p sparkle-project` 或 `COMPOSE_PROJECT_NAME` 钉死。
3. **INFO — celery 单独渲染声称口径不严**：`docker compose -f docker-compose.celery.yml config`（exit 0）实际渲染 `services: {}`——5 个服务全部 `profiles: [celery]` 门控，空集校验。`--profile '*'` 渲染后 5/5 全新名，实质成立；verification.md 括注「services 单独缺 redis 服务属既有结构」的解释不准确。
4. **INFO — `make dev-up`（Makefile:26）绕过 up.sh 门**：直接 compose up，无预检。分化后结构性安全（卷键 project 前缀隔离+容器名唯一），门降级为手工操作防线，与修复前同形，非回归。另 supervisor minio 探活打 127.0.0.1:9000，端口被 cosmos 栈占据时会绿灯他仓 minio——属 limitations #2 已披露的端口面不分化范围。
5. **INFO — dev-stage3 双仓接受分支无新洞**：仅读 `docker ps`（零创建/零杀灭），接受 cosmos 栈时打印 NOTE；残余歧义（双栈并存/错端口时引擎按默认端口搭车）为 limitations #2 已披露面。不反向放过错栈到数据损坏路径。

## 各靶核验结论（全打）

1. **compose 渲染亲验**：/tmp 沙箱哑值 env，四场景 `docker compose config` 全 exit 0；渲染 container_name main 14 / pair 17 / celery 5（`--profile '*'`）/ prod 22 = 44 全 `sparkle_proj_*`，container_name 字段旧名 0。`git diff 0949da60..e32f9043 -- docker-compose*.yml` 逐行核对：**全部改动行均为 container_name 行**，服务键/depends_on/volumes 节零改动（数据面零迁移红线成立）；卷键 `sparkle_{postgres,redis,minio}_data` 未动，宿主现存卷全为 `sparkle-cosmos_*`（零触碰实证）。
2. **零残留独立 grep**：自跑 mandate grep + 多行感知 `--name` 猎杀（python 扫描含续行上下文）——除发现 1 的 3 行外，可执行上下文旧名命中全部归因豁免 A/B/C 且逐条属实（compose 服务名 up/ps/unpause/logs、`@sparkle_db:5432` DNS、dev-stage3 故意接受分支=C、注释史录=B）。「可执行容器操作+旧名=0」**不成立**（见发现 1）。
3. **预检门语义（最重）**：up.sh 门四象限全部实证——Q1 本仓容器挂 cosmos 卷=die（shim 仿真 exit 1）、Q2 本仓卷=OK（shim exit 0）、Q3 absent+cosmos 卷存在=WARNING 放行（**真机只读 replay 实证**，NOTE×1+WARNING×3）、Q4 absent 无 legacy 卷=静默放行（shim）。supervisor `DATA_CONTAINER/PREFIX` 反转正确、absent="no such object"→绿+注记、误挂→红+RUNBOOK 指引；17 测试复跑 passed。FIX-557 形态（他仓发起重建静默挂空卷）在分化后本仓 compose 路径结构性不可能再现：本仓只能创建唯一名容器、只能挂 `sparkle-project_*` 卷键。测试重写非删断言凑绿（基线测试 253-259 行「sparkle-project_=红」系分化前误挂形态，反转有据；他仓卷→红负例保留加强）。
4. **红线核验**：diff 全量扫——新增行的 docker 动词均为 Makefile recipe 文本且全部新名；`docker compose up|down|restart|run` 零命中；cosmos 仓路径写入零（31 处 `sparkle-cosmos` 字样全为注记/对照表文本）。`docker ps/inspect`：三现役容器 `sparkle_db/redis/minio` StartedAt=2026-09-28T07:21–07:31Z（+0800 15:21–15:31），早于修复会话（09-29 10:20–11:10 +0800）约 19h，Up 19-20h healthy——全程零触碰实证。
5. **监控一致性**：`sparkle_agent_grpc` static→file_sd、job_name 未动（告警/面板零连锁前提成立）；dev/prod agent.yml 目标（服务名 sparkle_agent vs 容器名 sparkle_proj_agent）与「挂载面即形制开关」教义一致，两 compose 均 mount `./monitoring/targets/{dev,prod}:/etc/prometheus/targets`，file_sd 路径可达；promtail 两 selector 改 `sparkle_proj_{backend,gateway}`（prod 形制容器名，与改前同构）；面板正则并列新旧名=兼容未重建窗口（limitations #4 对应）；7 YAML + 面板 JSON 亲验 valid；`prometheus-celery.yml:53 sparkle_backend:8000` 断靶确系既有（limitations #5 属实）。
6. **RUNBOOK 对照表抽验 6 项**：sparkle_proj_db/redis/minio（compose.yml:9 等）+cosmos 侧旧名（cosmos 仓 grep 实证）、卷名 `sparkle-project_sparkle_postgres_data`（卷键+project 前缀推演一致）、`sparkle_proj_api/agent/gateway/celery_*`（渲染输出）——6/6 全对；「宿主现役属主」注记与 `docker volume ls` 实况（全 cosmos 前缀）一致；「下次（重）创建生效」注记在位。
7. **limitations 8 条诚实性**：逐条对基线核实——#1 属实（门未真跑，本次审查以 shim+replay 补证）；#2 属实（基线 up.sh 确有 SKIP_DB_UP 搭车，已移除）；#3 属实（backup_prod_data.sh:7-11 默认新名且 `POSTGRES_CONTAINER=` env 覆盖在位）；#4/#5 属实（正则并列/断靶保留亲验）；#6 属实（见靶 3）；#8 属实（宿主卷实况佐证）。无静默放弃项——发现 1 属扫描漏检缺口，非未披露的放弃。
8. **回归复跑**：`pytest test_service_supervisor.py test_supervisor_probe.py` → **17 passed**（1.82s）；`pytest test_o05_restore_consistency.py` → **14 passed**（0.18s）；bash -n ×5（up/healthcheck/smoke/logs/dev-stage3）全 OK；py_compile ×4 OK；`make -n dev-up` exit 0。

## 命令与 exit code 清单（关键项）

| 命令 | exit |
|---|---|
| `docker compose -f docker-compose.yml config`（/tmp 沙箱+哑值 env） | 0 |
| `docker compose -f docker-compose.yml -f docker-compose.services.yml config` | 0 |
| `docker compose -f docker-compose.celery.yml --profile '*' config` | 0 |
| `docker compose -f docker-compose.prod.yml config` | 0 |
| `grep -rn 'sparkle_db\|sparkle_redis\|sparkle_minio\|sparkle-db\|sparkle-redis' --include='*.sh' --include='Makefile' --include='*.yml' --include='*.py' …` | 0（命中已逐条归类） |
| 多行感知 `--name sparkle_*` 猎杀（python os.walk+续行上下文） | 3 命中=发现 1 |
| `git diff 0949da60..e32f9043` 全量扫容器操作/cosmos 写入 | 零命中 |
| `docker ps` / `docker inspect sparkle_{db,redis,minio}` / `docker volume ls`（只读） | 0 |
| up.sh 门 Q3 真机只读 replay（sed 24-61 行） | 0 |
| 门 Q1/Q2/Q4 shim 仿真 | 1 / 0 / 0 |
| `pytest scripts/tests/test_service_supervisor.py scripts/tests/test_supervisor_probe.py -q`（主仓 venv） | 0，17 passed |
| `pytest scripts/tests/test_o05_restore_consistency.py -q` | 0，14 passed |
| `bash -n` ×5 / `py_compile` ×4 / `make -n dev-up` | 0 / 0 / 0 |

## 处置建议

发现 1 由后续修复卡收口（三处 `--name` + network 旧债 + verification.md §2 口径修正）；发现 2 建议立小卡（`-p`/`COMPOSE_PROJECT_NAME` 钉死或门支持 project 前缀可配置）；发现 3-5 记录即可。核心分化交付与四象限门可保持 CLOSED 判定不回退。
