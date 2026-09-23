# D-DEPLOY-FIX 报告 — 部署链三缺口修复（G1+G7+G2）

> 轮次：D 纵队 · 云端部署线 ｜ 2026-09-23 ｜ worktree wt186（基线 b2f8bbd9）
> 缺陷依据：主仓 `v3-output/D-DEPLOY/REPORT.md` §2 G1 / G7 / G2（本轮为该报告建议合入顺序「G1+G5+G7 小卡 / G2 小卡」的落地，G5 未在本卡范围）
> 交付物：本报告 + `changes.patch`（4 个代码文件：3 改 1 增）。**零 commit 零 push，零凭据，未起 prod 栈。**

---

## ① 三项修法（对照 D-DEPLOY 报告验收）

### G1(P1) Prometheus 抓取目标对齐 prod 拓扑 — `monitoring/prometheus.yml`

对照报告最小解「prod 侧加 gateway_blue/gateway_green/backend 三个 target；sparkle_celery target 删除或标注待部署」：**照做并略强**。全部 job_name 保持不变（告警规则 `up{job="sparkle_gateway"}==0` 等 6 组规则文件与 Grafana 面板按 job 标签取数，改 job 名会连锁破坏），只换 targets：

- `sparkle_gateway` job → **`gateway_blue:8080` + `gateway_green:8080` 双 target**（蓝绿取名对齐在文件头注释块写明：**两个都要抓**，Docker user-defined 网络按服务名解析、prometheus 与网关同在 app 内网可达；任一实例掉线即有 `up==0` 序列——蓝绿冗余减半是应该知道的事；`deploy-prod.sh` 排空 ~90s < 告警 `for: 2m`，正常发版不误报）；
- `sparkle_backend` 及 counterfactual/simulation_lab/safe_experiments/community_privacy 四个模块 job → `backend:8000`（原 `sparkle_api` 在 prod 解析不到）；
- `sparkle_agent_grpc` 保持 `sparkle_agent:50051`（prod container_name 与 dev 服务名同名，两形制通吃，报告 G1 已认定它能抓到）；
- `sparkle_celery:9808` → **整段注释 + 「待部署」标注**（全仓无 9808 监听者；接入 prometheus-community/celery-exporter 后取消注释即可）；`celery_alerts.yml` 按 `job="celery_worker"/"celery_beat"` 取数本就从未有过对应 scrape job，no-data 空转为**既有债务**，随本卡登记（§④）；
- `alertmanager`/`node_exporter`/`cadvisor`（服务名 target）在 prod 本就可解析，保持不动。

**验证**：promtool check config（本机已有 `prom/prometheus:latest` 镜像，一次性 `--rm` 容器跑 `--entrypoint promtool`，非 prod 栈）→ config + 6 个规则文件（81 条规则）全部 SUCCESS；目标名 × `docker-compose.prod.yml` 服务名/container_name 全集逐项核对脚本 → 生效 targets 13 项全部可解析（唯一 MISS 是注释段里的 `sparkle_celery`，grep 连注释一起抓出，恰证它已不生效）。

### G7(P3) bootstrap AGE one-shot 探测正则识别 `db_age_init` — `scripts/deploy/bootstrap.sh:459`

对照报告最小解「正则放宽为 `'(sparkle_)?age_init|db_age_init'`，纯一行修正」：**照做**。探测正则改为 `grep -xE '(sparkle_)?age_init|db_age_init'`，注释写明卡上要求的事实：**即使探测落空，AGE 初始化仍由 backend/agent/celery 的 `depends_on(db_age_init: service_completed_successfully)` 兜底强制先行，功能无损**（dev 侧 `sparkle_age_init`、prod 侧 `db_age_init` 双名都认）。

**必要伴随改动（如实申报，超出「一行」的部分）**：正则修好后 compose 路径首次真实可达，而原逻辑只在 fallback 分支起 backend——步骤 5 末尾共享的 RAG 初始化 `compose exec -T backend python scripts/init_redis_index.py` 在 compose 路径下会因 backend 未运行而 WARN 失败。故在 compose 分支 `wait_exit0` 后补 `compose up -d backend`（backend 的 depends_on 只有 db/redis/db_migrate/db_age_init，此时全部已满足，不会连带拉起 minio 面的组件；与 fallback 分支同款动作，语义一致）。另把 step5 的 `--plan` 文案与 fallback 失败提示中「等 D-AGE 卡合入」的过时表述改为 D-AGE 已合入后的实情。

**验证**：`bash -n` 通过；正则单测——prod compose 22 个服务名全集喂入，旧正则对 `db_age_init` 零命中（复现「永远走 fallback」根因），新正则恰命中 `db_age_init` 1 个、零误命中；`bootstrap.sh --plan` 干跑全流程通过（plan 文案含 depends_on 兜底事实）。

### G2(P1) 备份 cron 化 — `scripts/install_backup_cron.sh`（新增）+ bootstrap 步骤 9.5 + `backup_prod_data.sh` 密码兜底

对照报告最小解①「bootstrap 加一步『安装 cron 条目 + 校验首次备份』」：**照做**，三件套落地：

1. **`scripts/install_backup_cron.sh`（新增，175 行）**：幂等安装宿主 crontab 条目 `15 3 * * * cd <repo> && bash scripts/backup_prod_data.sh >> <repo>/backups/backup.log 2>&1`，marker 注释块管理（重装先摘旧块再写新块，**不碰用户其它 crontab 条目**）；`--print` 干跑 / `--run-now` 首次备份校验 / `--remove` 卸载；退出码契约 0=装好且备份过、2=装好但备份未过、1=安装失败（备份校验失败不阻塞上线）。
2. **bootstrap 步骤 9.5（readiness/smoke 之后、摘要之前）**：调安装器 `--run-now`，按退出码三态呈现 ok/warn，失败仅 WARN 不阻塞上线；新旗标 `--skip-backup-check` 可整步跳过；摘要「备份 cron」行从「建议人工去配」改为**状态申报**（已装/未装/未过，就地更新），并新增「备份·异地：登记待办（未实现）」行。
3. **`backup_prod_data.sh` REDIS_PASSWORD 兜底**：报告 G2 缺口段指出的陷阱（prod 三账号 ACL 下 default 账号带密码，脚本默认空 → RDB 必败，且 cron 环境没有 shell profile）——未显式提供时从仓库根 `.env` 提取 `REDIS_PASSWORD`（`grep|tail|cut` 只取值不 source，防执行 .env 内容；去引号语义与 bootstrap `env_get` 一致）；显式环境变量优先；无 `.env` 保持空态不硬造。

**验证**：`bash -n` ×2 通过（本机无 shellcheck）；沙箱行为测试 9 项全过（/tmp 假 crontab + 假 docker shim，**不触真实 crontab/容器**）：`--print` 零变更、安装、幂等重装（管理块恒 1 个）、外来条目共存保留、`--run-now` 失败路径退出码 2、摘块保外来条目、仅管理块时整体移除、`REDIS_PASSWORD` 带引号/无引号提取、显式变量优先、无 .env 保持空；`bootstrap.sh --plan` 与 `--plan --skip-backup-check` 干跑通过；`changes.patch` 在基线克隆上 `git apply --check` 完整可应用。

---

## ② 实现清单

| # | 文件 | 变更 | 对应 |
|---|---|---|---|
| 1 | `monitoring/prometheus.yml` | targets 对齐 prod（gateway_blue+green 双抓 / backend:8000 ×5 / celery 注释待部署）+ 命名对齐头注 | G1 |
| 2 | `scripts/deploy/bootstrap.sh` | L459 正则 `(sparkle_)?age_init\|db_age_init` + depends_on 兜底注释；compose 分支补 `up -d backend`（RAG exec 前置保障）；step5 plan/fallback 文案去陈旧；新增步骤 9.5 + `--skip-backup-check` + `BACKUP_CRON_STATUS` 摘要状态面；摘要备份两行改写 | G7 + G2 |
| 3 | `scripts/backup_prod_data.sh` | REDIS_PASSWORD 空值时从仓库根 .env 提取（只取值不 source） | G2 |
| 4 | `scripts/install_backup_cron.sh`（新增，755） | 宿主 crontab 幂等安装器：marker 块管理 / `--print` / `--run-now` / `--remove` / 0-2-1 退出码契约 | G2 |
| 5 | `v3-output/D-DEPLOY-FIX/changes.patch` | 上表 4 文件的统一补丁（基线克隆 `git apply --check` 通过） | 交付 |

净改动：3 文件修改 + 1 文件新增，+178/−20 行量级。

## ③ 冲突面声明

本轮只动 `monitoring/prometheus.yml`、`scripts/deploy/bootstrap.sh`、`scripts/backup_prod_data.sh`、`scripts/install_backup_cron.sh`（新增）四个部署面文件，逐卡声明：

- **wt178（mobile galaxy/chat）**：mobile/ 域，零重叠；
- **wt180（event_bus + 网关 Go + outbox）**：backend/gateway 域，零重叠（G1 只改 prometheus 抓取配置，不碰网关代码）；
- **wt181（community + 迁移）**：社区域 + alembic 迁移，零重叠；
- **wt182（reviewer/checkpoint/lifespan/scheduler）**：引擎编排/调度域，零重叠（bootstrap 的步骤 9.5 是部署期一次性 crontab 安装，与 celery beat 的应用层调度是完全不同的两层）；
- **wt184（guards + SPEC 文档 + sprint 面）**：scripts/guards 与文档域，零重叠（未动任何 guard 脚本）。

基线 b2f8bbd9 之上 `git status` 申报：modified ×3（上表 1-3）+ untracked ×2（install_backup_cron.sh 与 v3-output/D-DEPLOY-FIX/ 交付物），无其他漂移。

## ④ 诚实申报

1. **G2 调度载体选择理由**：卡给三选一（prod compose cron 服务 / systemd timer 样例 / 宿主 crontab 安装片段），报告最小解①原文是「bootstrap 加一步安装 cron 条目 + 校验首次备份」——据此选**宿主 crontab**：零新容器（compose cron 服务形态必须把 docker.sock 挂进调度容器，攻击面与镜像依赖不划算）、零 systemd 单元放置/权限问题、每台 Linux VPS 自带 cron；与报告最小解字面吻合度最高。**systemd timer 为未选路径**，登记：如需迁移，安装器的 marker 块管理机制可直接平移到 timer 单元的安装/卸载。
2. **「校验首次备份」的实现口径**：实现为安装后 `--run-now` 真跑一次三件套备份（演示期数据量级 MB 级、KEEP_DAYS=7 滚动自清），失败退出码 2、bootstrap WARN 不阻塞上线；不给 bootstrap 加强制等待的真备份不可谓校验，故提供 `--skip-backup-check` 给想跳过的操作者。
3. **G1 的 dev 形制影响（关键坦白）**：`monitoring/prometheus.yml` 被 dev 与 prod compose **共用**。按卡「target 名对齐 prod 服务真实名」执行后，缺陷方向反转：dev 形制下 `sparkle_gateway`/`sparkle_backend` 两 job 的目标解析不到，dev 侧 `SparkleGatewayDown/BackendDown`（`for: 2m`）会常驻 firing（dev alertmanager webhook 多为占位，实际外送面有限）。修复前是「prod 全 no-data、dev 全绿」，现在是「prod 全绿、dev 网关/引擎两 job no-data」。两形制双绿的彻底解是 file_sd 按形制生成目标或 compose 网络别名，**登记债务未实现**（超出本卡「对齐 prod」的最小解范围）。同口径登记：node_exporter/cadvisor 两 job 在 dev 形制本就无对应服务（既有现状，未恶化）。
4. **登记未实现项**：① 备份异地化（mc mirror 到对象存储，~¥5-10/月）——摘要行 + 安装器头注 + 本报告三处登记；② celery-exporter 接入（9808 待部署注释，celery_alerts.yml 空转随之解除）；③ dev 形制 file_sd（见上条）。
5. **验证边界**：全部验证为解析级（promtool）、干跑级（`--plan`）、沙箱级（/tmp 假 shim），**未起 prod 栈、未装真实 crontab、未跑真实备份、未碰任何运行中容器**。真机 `cloud-up` 演练 + prometheus `up` 序列实抓 + 备份还原演练，属 D-DEPLOY 报告已申报同口径的「未真机部署项」，合入后必须经一次真机验证（其 §6 原话）。promtool 经本机已有镜像的一次性 `--rm` 容器执行（无端口、即退，不属 prod 栈）。
6. **零凭据**：测试夹具全用 fake 值（`fake-pass-quoted-123` 等）且全部在 /tmp，收工已清。

## ⑤ 收工核查

- [x] `/tmp` 自清：`/tmp/dfix-sandbox`、`/tmp/dfix-applytest`、`/tmp/dfix-*.txt/.patch` 全部删除（见收工命令）
- [x] 无 `git commit` / `git push`；交付物 = 本报告 + `changes.patch`
- [x] 未起 prod 栈、未碰运行中容器、未装真实 crontab
- [x] 零凭据入交付物
- [x] worktree 内无构建产物/临时文件残留（`git status` 干净度见 ③）
- [x] 蓝绿双网关取名对齐已写明（prometheus.yml 头注块 + 本报告 ①G1）
