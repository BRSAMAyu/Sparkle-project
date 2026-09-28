# ROLLBACK.md — Sparkle 生产/Staging 回滚程序（O-01 验收面）

> 适用形制：单机 docker compose 生产栈（`docker-compose.prod.yml`），即
> `scripts/deploy/bootstrap.sh` 部署、`scripts/deploy-prod.sh` 发版的形态。
> 所有命令引用的都是仓库内真实存在的脚本与 compose 服务名；没有的机制会明确标注「未实现」。
>
> 前置阅读：`v3/08_operations/DEPLOYMENT.md` ｜ 部署入口文档：`scripts/deploy/README.md`

## 0. 回滚决策速查

| 症状 | 判定位置 | 回滚类型 |
|---|---|---|
| 新版本上线后 smoke/health 变红 | `scripts/deploy-prod.sh` 已自动回切（观察窗口内） | 应用层（已自动，只需确认） |
| 观察窗口过后才发现问题 | 手动执行 §1 应用回滚 | 应用层 |
| nginx/证书/边缘问题 | 不动应用，查 §4 边缘面 | 边缘层 |
| 数据错误/迁移事故 | §3 数据回滚（restore） | 数据面 |
| 整机不可用 | §5 整机重建（bootstrap 重放 + restore） | 灾难恢复 |

先看当前状态（哪个 gateway 色在服务、各容器健康态）：

```bash
docker compose -f docker-compose.prod.yml --env-file .env ps
cat nginx/upstream.conf          # 当前服务色（gateway_blue / gateway_green）
docker compose -f docker-compose.prod.yml --env-file .env logs --tail 80 gateway_blue
```

## 1. 应用层回滚（最常用）

生产是蓝绿双网关 + nginx upstream 切换（`nginx/upstream.conf`），`scripts/deploy-prod.sh`
的 smoke/观察失败会自动切回旧色。观察窗口过后的人工回滚 = 用旧镜像 tag 重跑同一条发版命令
（蓝绿自动落到健康侧）：

```bash
# 单命令回滚：<旧tag> 是上一个已验证的 IMAGE_TAG（见 .env 或上次发版记录）
IMAGE_TAG=<旧tag> bash scripts/deploy-prod.sh
```

语义（与脚本实现一致）：

1. 拉取 `<旧tag>` 镜像，up -d 拉起 `backend`/`agent`/对侧 gateway；
2. 对新拉起的服务在 app 内网做 `/api/v1/health` 健康门（30 次轮询，不过直接中止，**不切流**）；
3. 重写 `nginx/upstream.conf` 指向目标色并 `nginx -s reload`（秒级切流，不断 443 监听）；
4. 切流后跑 smoke（`/api/v1/health`、`/api/v1/health/cqrs`），失败自动切回原色；
5. 观察 180s（`OBSERVE_SECONDS`），失败自动切回原色；
6. 通过后 drain 旧色 90s 并 stop。

回滚后确认：

```bash
cat nginx/upstream.conf          # 应指回目标色
docker compose -f docker-compose.prod.yml --env-file .env ps
bash deploy/smoke_gj01.sh --base-url https://<域名> --no-journey   # 边缘面快速确认
```

注意：

- `IMAGE_TAG` 是硬必填（compose `:?` 断言），不要用 `latest` 回滚——回滚必须落到**确定的旧版本**。
- `scripts/blue_green_switch.sh` 已标注 DEPRECATED（本地 slot 形制），**不要**用它做生产回滚。
- 蓝绿只回滚 gateway/backend/agent 无状态面；**它不回滚数据库**——发版包含 Alembic 迁移时，
  回滚应用前先读 §3 的迁移兼容纪律。

## 2. 配置层回滚（.env / 证书）

```bash
# .env 被 bootstrap 追加 overlay 前会自动备份（.env.bak.<时间戳>）
ls -la .env.bak.* 2>/dev/null
cp .env.bak.<时间戳> .env && chmod 600 .env
docker compose -f docker-compose.prod.yml --env-file .env up -d     # 使配置生效
```

证书回退（`./ssl/` 是 nginx 挂载源，`SSL_CERT_DIR` 可覆盖）：

```bash
ls -la ssl/                                   # 当前证书
# 上一张证书没有自动备份机制（未实现）；换回旧证书 = 用旧 pem 覆盖后 reload：
docker compose -f docker-compose.prod.yml exec -T nginx nginx -s reload
```

## 3. 数据面回滚（PostgreSQL / Redis / MinIO）

### 3.0 卷保留策略（先读这个，防误删）

数据都在**宿主机 bind mount**（不在 named volume）：

| 服务 | 宿主路径 | `down` 行为 |
|---|---|---|
| PostgreSQL | `./postgres_data` | 保留（`down` 不带 `-v` 也不删 bind mount；`down -v` 对 bind mount 同样无效，但**禁止**携带以防误删 named volume） |
| Redis | `./redis_data` | 保留 |
| MinIO | `./minio_data` | 保留 |
| 观测 | named volumes（`sparkle_*_data`） | `down -v` 会删，回滚用不到 |

结论：**任何回滚动作都不要带 `-v`**。数据面的唯一真源是备份包，不是卷本身。

### 3.1 回滚到备份点（restore）

备份包由 `scripts/backup_prod_data.sh` 产出（cron `15 3 * * *`，默认 `./backups/<时间戳>/`，
内含 `postgres.sql.gz` + `redis.rdb` + `minio-data.tar.gz` + `sha256sums.txt` + `manifest.json`
+ `config/env`，包内含密钥，权限 600 不要放宽）：

```bash
ls -lt backups/ | head                        # 选目标备份点
cat backups/<时间戳>/manifest.json             # 核对 alembic_head 与 PG 版本戳
bash scripts/restore_prod_data.sh backups/<时间戳>
# schema 代差要硬失败时：
STRICT_SCHEMA=1 bash scripts/restore_prod_data.sh backups/<时间戳>
```

restore 是**精确快照语义**（`--clean --if-exists` 转储重放 + MinIO 整树交换 + 任一 SQL 错误
即非零退出），会把库恢复到备份点当时状态——备份点之后的写入会丢。执行顺序：

```bash
# 1) 先停写（把入口摘掉，避免 restore 期间新写入被快照覆盖丢失）
docker compose -f docker-compose.prod.yml --env-file .env stop nginx gateway_blue gateway_green
# 2) restore（PG + Redis + MinIO 三件套按包内实际产物分派）
bash scripts/restore_prod_data.sh backups/<时间戳>
# 3) 回到与备份包 schema 匹配的应用版本，再恢复入口
IMAGE_TAG=<备份包时代的tag> bash scripts/deploy-prod.sh
```

### 3.2 Alembic 迁移回滚纪律

- schema 唯一入口是 Alembic（仓库硬规则）；**不要**手写 DDL 回滚。
- 发版纪律：迁移必须向后兼容一版（先加列后删列），使「应用回滚一版」不需要回滚 DDL。
  这是首选路径——§1 的应用回滚在兼容迁移前提下对 schema 无害。
- 确需回退迁移时（非常规，需双人复核）：

```bash
docker compose -f docker-compose.prod.yml --env-file .env run --rm db_migrate alembic downgrade -1
```

  并在之后立刻补一次备份（此时库状态是手工干预过的非常规点）。

### 3.3 回滚后补一次备份

任何数据面操作（restore/downgrade）之后立刻手动备份一次，形成新锚点：

```bash
bash scripts/backup_prod_data.sh
```

## 4. 边缘层（nginx / TLS / WSS）

nginx 只是无状态边缘，回滚 = 还原配置文件后 reload：

```bash
# upstream.conf 由 deploy-prod.sh 生成管理；手工指回指定色（应急用，常规走 §1）：
cat > nginx/upstream.conf <<'EOF'
upstream gateway_upstream {
  least_conn;
  server gateway_blue:8080;
  keepalive 64;
}
EOF
docker compose -f docker-compose.prod.yml exec -T nginx nginx -s reload
```

- nginx.conf 自身不在脚本管理面内，git 是它的版本真源：改坏了 `git checkout -- nginx/nginx.conf`
  后 reload。
- 配置语法预检：`docker compose -f docker-compose.prod.yml exec -T nginx nginx -t`。

## 5. 整机重建（灾难恢复）

ECS 实例（i-2ze439t934c2gsdqm778，cn-beijing）整机型灾难 = 新机/重装系统后重放部署 + 恢复数据：

```bash
# 0) 前置（人工）：安全组放行 22/80/443；DNS A 记录指向新机；docker 已安装
#    （bootstrap preflight 会给出缺项提示，不会自动改防火墙）
# 1) 代码与证书
git clone <repo> && cd Sparkle
sudo certbot certonly --standalone -d <域名>      # 或从旧机拷贝 ssl/
bash scripts/ssl/setup_certs.sh <域名> ./ssl
# 2) 一键部署（.env 从最近备份包 backups/<最新>/config/env 恢复，不要重填）
cp backups/<最新>/config/env .env && chmod 600 .env
make cloud-up ARGS="--skip-backup-check"
# 3) 数据恢复
bash scripts/restore_prod_data.sh backups/<最新>
# 4) 验证：完整 GJ01 探针（非降级）
bash deploy/smoke_gj01.sh --base-url https://<域名> --bundle-dir <client产物>
```

## 6. 回滚后验证清单（全绿才算回滚完成）

1. [ ] `docker compose -f docker-compose.prod.yml --env-file .env ps` —— 全部 healthy/up
2. [ ] `cat nginx/upstream.conf` —— 指向预期的 gateway 色
3. [ ] `bash deploy/smoke_gj01.sh --base-url https://<域名> --no-journey` —— 公开面 + 401 拒绝面全 PASS
4. [ ] `bash deploy/smoke_gj01.sh --base-url https://<域名> --bundle-dir <client产物>` —— 完整 GJ01（含 guest→WSS 正向握手）全 PASS、AK 扫描零命中
5. [ ]（数据面回滚时）`bash scripts/restore_prod_data.sh` 退出码 0 + `bash scripts/backup_prod_data.sh` 新锚点产出
6. [ ] 观测面复核：Grafana（`ssh -L 3000:127.0.0.1:3000 <user>@<vps>`）无新增告警

## 7. 已知缺口（诚实登记，不冒充已实现）

- **备份异地化未实现**：备份只在同机 `./backups/`（`scripts/deploy/bootstrap.sh` 摘要中的
  登记待办），单机磁盘损坏 = 备份同损。整机重建流程依赖能从外部拿到备份包（人工拷出）。
- **证书无历史版本管理**：`scripts/ssl/setup_certs.sh` 只做当前签发拷贝，无上一版回退机制。
- **蓝绿只覆盖 gateway**：backend/agent 是原地 `up -d` 替换（`deploy-prod.sh` 语义），
  回滚它们靠重跑旧 `IMAGE_TAG`，无容器级并行版本。
- **阿里云侧无自动化**：ECS/安全组/DNS/certbot 都是人工步骤（凭据在途，见
  `v3/08_operations/HUMAN_INBOX.md` 的 human 项）。
