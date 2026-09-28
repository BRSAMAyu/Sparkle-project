# WT815 — FIX-556 compose.prod JWT RS256 注入断层 + FIX-557 数据面属主 runbook 注记

> 状态：**DONE**（两修均本地实证；远端 ECS 真跑不在本卡可验面，见残留注记）
> Worktree：`wt815`，分支 `agent/wt815/fix556`（基于 main @ `c202d92c`）
> 日期：2026-09-28 ｜ 台账：`v3/06_agent_fleet/DYNAMIC_ISSUES.md` FIX-556(P2)/FIX-557(P3)

## 交付物

| 文件 | 变更 |
|---|---|
| `docker-compose.prod.yml` | FIX-556：`backend` + `gateway_blue` + `gateway_green` 三服务 environment 补注入 `JWT_PRIVATE_KEY` / `JWT_PUBLIC_KEY`，`:?` 硬门形态（缺失或为空即 compose 拒起），与 GRAFANA_ADMIN_PASSWORD / TRUSTED_PROXIES 门同风格 |
| `scripts/deploy/bootstrap.sh` | FIX-556：`validate_env` required 数组补 `JWT_PRIVATE_KEY JWT_PUBLIC_KEY`（18→20 必填），占位符/空值在部署前置被拦（早于镜像拉取失败） |
| `.env.cloud.example` | FIX-556：节头 `[RECOMMENDED]`→`[compose.prod :? 硬门，缺了起不来]`；多行 PEM 粘贴约定落地为实证过的双引号块写法 |
| `scripts/RESTACK_RUNBOOK.md` | FIX-557：新建单页重建手册——sparkle_db 属主铁律 + 09-28 事故复盘 5 行 + 纠偏 7 步 |
| `scripts/README.md` | FIX-557：新建（scripts/ 原无 README），按 REPOSITORY_STANDARDS 登记 runbook 与目录用途索引 |
| 本报告 | 证据与残留注记 |

## FIX-556 修法依据（消费面 grep 实证）

- **网关侧确实消费**：`backend/gateway/internal/config/config.go:54-55` `JWTPrivateKeyPEM/JWTPublicKeyPEM`（mapstructure `JWT_PRIVATE_KEY`/`JWT_PUBLIC_KEY`）；`handler/auth.go:183/222` RS256 签发、`middleware/auth.go:498` 验签。→ 按卡指示同卡注入，双网关都补。
- **后端侧消费**：`backend/app/config/settings.py:306-307`、`core/security.py:54-68`（RS256 签发必需私钥，验签双轨）。
- **agent 服务不注入**：与 dev compose（`docker-compose.yml:485-489` 只给网关注入 JWT 密钥对）对齐；agent 为内网 gRPC（鉴权走 INTERNAL_API_KEY），不签发/验签用户 JWT。
- **传输方式与现有 SECRET_KEY 一致**：`environment:` 列表 + `${VAR}` 从 `.env` 插值（prod compose 全文件无 `env_file:` 路线），未引入第二套机制。

## 验证实录（compose 5.0.2 / Docker 29.2.1，假值干跑，未触真实远端）

| # | 验证 | 结果 |
|---|---|---|
| 1 | `docker compose -f docker-compose.prod.yml --env-file <假值> config`：假值单行 PEM 三变量齐 | exit 0；`backend/gateway_blue/gateway_green` 三服务 environment 均含两密钥（json 输出逐项核对） |
| 2 | 缺 `JWT_PRIVATE_KEY/JWT_PUBLIC_KEY` 干跑 | `error while interpolating services.backend.environment: required variable JWT_PRIVATE_KEY is missing a value: JWT_PRIVATE_KEY must be set (JWT RS256 私钥缺失)`——快报形态正确 |
| 3 | 空值形态（`JWT_PRIVATE_KEY=`）干跑 | 同样被 `:?` 拒（`:?` 语义=unset 或 empty 均报错），非空断言成立 |
| 4 | 多行 PEM 保真：`.env` 双引号块值 → `config --format json` | 私钥 3 个真实换行、公钥 2 个，`-----BEGIN/END-----` 边界原样到达容器 env——两侧应用均按原始 PEM 解析（pem.Decode / pydantic str 无 `\n` 还原逻辑），故约定=双引号块而非 `\n` 转义 |
| 5 | `bash -n scripts/deploy/bootstrap.sh` | 通过 |
| 6 | bootstrap `validate_env` 提取运行（fixture）：`JWT_PRIVATE_KEY=__CHANGE_ME__` | 门禁 FAIL 并点名该变量（exit 1）；换真实值后 PASS，计数消息自动为「20 个必填项」 |

证据文件（/tmp，会话产物不入库）：`/tmp/wt815_env_test.env`、`/tmp/wt815_cfg*.json`、`/tmp/wt815_gate_out*.txt`。

## FIX-557 实录与依据

- 活机只读取证（2026-09-28）：`docker volume ls` 仅存 `sparkle-cosmos_sparkle_{postgres,redis,minio}_data`（事故垃圾空卷已删，故无 `sparkle-project_` 项）；`docker compose ls` = `sparkle-cosmos running(3)`；`docker inspect sparkle_db --format '{{range .Mounts}}{{.Name}}{{end}}'` = `sparkle-cosmos_sparkle_postgres_data`——runbook 所写命令与期望输出即本机实录。
- 落点选择：现文排查过 `docs/engineering/`（无 ops runbook）、`v3/08_operations/RUNBOOK_DEMO.md`（演示脚本，非运维面）、`deploy/ROLLBACK.md`（生产/Staging 回滚，非本机数据面）、`v3-output/WT746-REHEARSAL/runday7.md`（wt751 已裁定「按原文执行」的冻结预演手册，改文即废其核验）——均不合适，按卡指示建 `scripts/RESTACK_RUNBOOK.md` 并新建所在目录 README 登记。
- runbook 内引用命令均为真实接口：`make dev-up`（sparkle-cosmos Makefile:23-26 = `docker compose up -d sparkle_db redis minio`）。

## 残留注记（不阻塞本卡闭账）

1. **backend RS256 签发未接线**：后端 `ALGORITHM` 字段（settings.py:305，无 JWT_ALGORITHM 别名）在 prod compose 未注入，当前生产 RS256 签发/验签实际发生在网关边缘（auth handler/middleware）；后端拿到密钥后如需切 RS256 签发，需另行补 `ALGORITHM` 注入——独立小卡，不属于「未注入」断层本体。
2. **轮换面变量未注入**：`JWT_KID`/`JWT_PREVIOUS_KID`/`JWT_PREVIOUS_PUBLIC_KEY(_FILE)` 网关支持但 compose 未注入（kid 可选，不注入不影响基线 RS256）；轮换执行时按 `docs/05_部署与运维/backend_JWT_RS256_KEY_ROTATION.md` 随卡补。
3. **`scripts/check_production_secrets.py` 的 CRITICAL_SECRETS 未扩**：该清单同样不含 GRAFANA_*/ALERTMANAGER_*（既有先例），维持现状不动；部署面已由 bootstrap 门禁覆盖。
4. **远端真跑未发生**：本地无 ECS 凭据，`:?` 快报与插值通路均为 compose 干跑证据；O-01 真实部署首跑即最终验证（bootstrap 门禁会先拦占位值）。
5. **长期修法未实施**：两仓 compose 容器名分化（FIX-557 台账行已存续注记），本卡只落 runbook 铁律。

## 自检声明

- 未 push；worktree `wt815` 保留；台账闭账走独立 `state(fleet)` commit（wt809/wt810 先例）。
- 零产品码改动（backend/gateway/mobile/proto 零触碰）；变更面 = compose 编排 1 文件、部署脚本 1 文件、env 模板 1 文件、scripts/ 新增 2 文件、本报告。
- 全部命令/行号引用均对 `c202d92c` 基线 + 本卡变更后实文核验。
