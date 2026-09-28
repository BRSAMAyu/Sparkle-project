# WT813 — O-01 公网 Staging 部署弹药盘点 + GJ01 探针 + 回滚文档

> 状态：**PARTIAL**（O-01 全卡验收还需凭据在途的远端执行；本 worker 交付可先行部分）
> Worktree：`wt813`，分支 `agent/wt813/o01smoke`（基于 main @ `5c288841`）
> 日期：2026-09-28 ｜ 卡：`v3/07_tasks/cards/O-01.md` ｜ 风险：high ｜ Reviewers: 2

## 交付物

| 文件 | 内容 |
|---|---|
| `deploy/smoke_gj01.sh` | GJ01 远端设备视角验收探针（新增，可执行，`bash -n` 通过） |
| `deploy/ROLLBACK.md` | 生产/Staging 回滚程序（新增） |
| `deploy/README.md` | 登记上两项（更新） |
| 本报告 | 盘点结论 + 缺口清单 |

不改产品码；无 proto/DB 变更；未 push。

## 1. 部署弹药盘点（现状 vs 任务面）

**勘误**：任务面说「`deploy/` 六脚本」——实际 `deploy/` 目录只有 `README.md` + `landing/`（落地页，非部署脚本）。真实部署弹药在 `scripts/` 与仓库根：

| 弹药 | 位置 | 对 O-01 的覆盖 |
|---|---|---|
| 一键部署总入口 | `scripts/deploy/bootstrap.sh`（831 行） | preflight（docker/磁盘/内存/80-443 端口/证书/DNS）→ .env 云端装配+占位符门禁（18 必填+LLM key+4 安全钉死）→ 镜像 → DB → 迁移 → AGE/pgvector → MinIO 桶 → 全栈 → readiness（内网+公网）→ smoke（health+guest→WS chat 端到端）→ 备份 cron → 摘要。幂等、`--plan` 干跑 |
| 蓝绿发版/回滚 | `scripts/deploy-prod.sh` | `IMAGE_TAG=<tag>` 重跑即回滚：健康门→upstream.conf 切色→nginx reload→smoke→观察 180s→失败自动切回原色→drain |
| HTTPS/WSS 终止 | `nginx/nginx.conf` + `nginx/upstream.conf` | TLSv1.2/1.3、80→443 强跳、HSTS+CSP 安全头、WS upgrade map、`proxy_read_timeout 3600s`（长连 WS）、限速区；upstream 蓝绿双色 |
| 证书 | `scripts/ssl/setup_certs.sh`（certbot 产物拷贝）+ `generate_dev_certs.sh`（自签） | Let's Encrypt 路径存在，需域名先行 |
| 编排 | `docker-compose.prod.yml`（931 行） | nginx edge(80/443)、gateway_blue/green、backend、agent、celery×2+beat、db(pgvector+AGE)、redis(ACL 三账号)、minio+RBAC、观测全家桶；`app` 网络 `internal:true`（FastAPI 8000 不公网裸露——符合 DEPLOYMENT.md）；数据 bind mount `./postgres_data`/`./redis_data`/`./minio_data` |
| 备份/恢复 | `scripts/backup_prod_data.sh` / `restore_prod_data.sh` / `install_backup_cron.sh` | PG 快照语义转储+Redis RDB+MinIO 归档+sha256sums+manifest（含 alembic_head）+ .env 捕获；restore 校验和+schema 代差门（STRICT_SCHEMA）；cron `15 3 * * *` 幂等安装 |
| 环境注入面 | `.env.production.example`(601 行) + `.env.cloud.example`(overlay) + bootstrap 门禁 | 密钥只进服务端 .env；compose 钉死 `ALLOW_WS_QUERY_TOKEN=false`；移动端经 `--dart-define=API_BASE_URL/WS_BASE_URL` 注入端点（`mobile/lib/core/constants/api_constants.dart`），不编译环境配置 |
| 干跑/验收入口 | `make cloud-plan` / `make cloud-up ARGS=...`；`scripts/verify_deployment.sh`（薄：health+延迟） | |

### 缺口清单（弹药 vs O-01 验收，按验收条目）

**验收「GJ01 远端设备通过；密钥不在 client bundle」**：

1. **GJ01 远端执行未发生（阻塞在凭据，非弹药）**：ECS `i-2ze439t934c2gsdqm778`(cn-beijing) 的 AK 在途 → 无法做：安全组放行 22/80/443、DNS A 记录、certbot 签证书、ghcr 私仓 `docker login`。bootstrap.sh 把这些当作人工前置而非自动步骤。
2. **镜像产物未证实**：`GATEWAY_IMAGE/BACKEND_IMAGE` 模板指向 `ghcr.io/__CHANGE_ME__/...`——没有已发布的 CI 镜像 tag 可拉。O-01 执行前需 CI 出镜像或自建 push。
3. **JWT RS256 面疑似断层（盘点发现，需上游核验）**：`.env.cloud.example` 推荐 RS256 并要求 `JWT_PRIVATE_KEY/JWT_PUBLIC_KEY`（`__CHANGE_ME__`），但 `docker-compose.prod.yml` 只注入 `JWT_SECRET/JWT_ALGORITHM`，未注入这对密钥变量。若 `JWT_ALGORITHM=RS256` 而应用读不到私钥，行为未定义。本卡不改产品码，只登记。
4. **本机 dev 栈 guest 链路当前是红的**（探针实录）：`POST /api/v1/auth/guest` 返回 `INTERNAL_ERROR`——本地 dev 环境问题（非脚本误报），意味着 GJ01 的 fresh-device 登录第一跳在本机尚不通；staging 部署时需关注（大概率是 dev 栈 Redis/DB 种子状态）。
5. **备份异地化未实现**（bootstrap 摘要已登记待办）：单机磁盘损坏=备份同损，影响 ROLLBACK.md §5 整机重建的前提。
6. **verify_deployment.sh 过薄**：只有 health+延迟，无 TLS/WSS/401/bundle 面 → 本卡 `deploy/smoke_gj01.sh` 补位。

**验收「部署/rollback 文档和 smoke 脚本」**：本卡交付后即闭环（见 §2/§3）。

## 2. `deploy/smoke_gj01.sh`（GJ01 探针）

远端 fresh-device 视角、无内网依赖的黑盒探针。用法：`bash deploy/smoke_gj01.sh --base-url https://<域名> [--bundle-dir <APK/目录>] [--mode http] [--json]`。退出码 0/1/2（全过/有 FAIL/用法错）。

断言面：

- **A TLS**：openssl 链校验（verify return code 0；自签需 `--allow-selfsigned` 且仅 rc 18-21 放行为 SKIP）+ notAfter 余量（<`--cert-min-days` 天报 SKIP 转 human）
- **B 健康面**：`/healthz`、`/api/v1/health` 期望 200；**`/docs` 按架构事实落地为负断言**（任务面把 /docs 列为探针，但 FastAPI 8000 在 internal 网内、网关生产模式无 /docs 路由——`setup.go` 仅 `IsDevelopment()` 挂 swagger——公网正确形态=非 200，依据 `v3/08_operations/DEPLOYMENT.md`「FastAPI 不公网裸露」；有意公开时用 `--expect-docs-public` 反转）
- **C WSS**：无凭据升级 `/ws/chat` → 401；guest 登录换 token 后 Bearer 升级 → 101（只握手不发消息，**零 LLM 调用**；WS_TICKET_REQUIRED=true 的 ticket-only 形态会给出明确诊断）
- **D 401 形态**：`/api/v1/health/cqrs` 未鉴权 → 401 且 body 含 JSON `error` 字段（对齐网关 `apiErrorResponse` 形态）
- **E 泄露扫描**：client bundle 产物 `grep -aE 'LTAI[0-9A-Za-z]+'` 断言零命中；APK/zip 自动解包后扫；缺 `--bundle-dir` 时降级扫 `deploy/landing` 并明示 SKIP 语义

验证实录（本次证据，非宣称）：

| 验证 | 结果 |
|---|---|
| `bash -n` | 通过 |
| 本地真栈干跑 `--base-url http://localhost:8080 --mode http` | PASS=6 FAIL=1 SKIP=2，EXIT=1——FAIL 是真信号：本地 dev 栈 guest 登录 INTERNAL_ERROR（见缺口 4）；健康/401 形态/docs 负断言/AK 扫描全部按预期工作 |
| fixture 全路径（临时 python 假网关，已清理） | guest→101 正向握手 PASS、AK 脏 bundle 命中 1 处 FAIL、干净 bundle 全绿 EXIT=0、`--json` 结构正确 |
| TLS 路径对公网真站（github.com） | 链校验 PASS + 余量天数解析正确（62 天）；非 Sparkle 站点 4 个端点 FAIL 属预期 |

## 3. `deploy/ROLLBACK.md`（回滚文档）

以现有脚本**真实接口**为准（无虚构命令）：

- **应用层单命令回滚**：`IMAGE_TAG=<旧tag> bash scripts/deploy-prod.sh`（蓝绿自动落健康侧；含六步语义说明与「不用 latest、blue_green_switch.sh 已废弃」警示）
- **配置层**：`.env.bak.*`（bootstrap 自动备份）回放 + 证书 reload（明确标注证书无历史版本管理=未实现）
- **数据面**：卷保留策略表（bind mount `./postgres_data` 等，**任何回滚不带 `-v`**）；`bash scripts/restore_prod_data.sh backups/<时间戳>`（快照语义+STRICT_SCHEMA）；停写→restore→回配 tag→恢复入口四步序；Alembic 向后兼容一版纪律 + `alembic downgrade -1` 非常规路径；操作后补备份锚点
- **边缘层**：upstream.conf 手工指色 + `nginx -t` 预检（git 为 nginx.conf 真源）
- **整机重建**：ECS 人工前置（安全组/DNS/docker）→ clone → certbot/`setup_certs.sh` → 从备份包 `config/env` 恢复 .env → `make cloud-up` → restore → 完整 GJ01 探针
- **回滚后验证清单**：6 项（含 smoke_gj01 两档复跑与 Grafana 复核）
- **已知缺口诚实登记**：备份异地化、证书版本管理、蓝绿只覆盖 gateway、阿里云侧全人工

## 4. O-01 全卡收口还差什么（给下一棒）

1. AK 到位后：安全组/DNS/certbot/ghcr 登录（HUMAN_INBOX 项）→ `make cloud-plan` 干跑 → `make cloud-up` 真实部署 → `bash deploy/smoke_gj01.sh --base-url https://<域名> --bundle-dir <APK>` 全绿 = GJ01 远端证据
2. 出一份真 client bundle（`flutter build apk --dart-define=...`，命令在 bootstrap 摘要里）跑 E 项扫描
3. 核验缺口 3（JWT RS256 密钥注入面）——建议开独立 fix 卡
4. 本地 dev 栈 guest INTERNAL_ERROR 根因（缺口 4）——独立排障，不属本卡
5. Reviewer 独立复跑：`bash -n deploy/smoke_gj01.sh` + 对任一可达网关跑一档

## 5. 自检声明

- 未改产品码（backend/gateway/mobile/proto 零改动）；仅新增 `deploy/smoke_gj01.sh`、`deploy/ROLLBACK.md`、本报告 + 更新 `deploy/README.md`
- 脚本 `bash -n` 通过；未 push；worktree 保留
- 文档中全部命令/路径均有仓库真实文件背书：`scripts/deploy-prod.sh`、`scripts/deploy/bootstrap.sh`、`scripts/{backup_prod_data,restore_prod_data,install_backup_cron}.sh`、`scripts/ssl/*.sh`、`nginx/*.conf`、`docker-compose.prod.yml`、`Makefile`(cloud-plan/cloud-up)、`deploy/smoke_gj01.sh`
