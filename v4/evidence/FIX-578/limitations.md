# FIX-578 limitations — 边界、遗留与验证口径

## 1. 未修（scope 外，显式登记）

1. **prod 栈 db 服务键分叉**：docker-compose.prod.yml 服务键 `db`（≠主栈 `sparkle_db`），`sparkle_db:5432` 在 prod 栈网络悬空；`.env.production.example` 若用于 prod compose 面则 db URL 同族不可达。消费流未证实（Aliyun 单栈指南指向 `sparkle_db:5432`，那是主栈面、合法），未越面改动——见 grep_exemptions.md §D1，建议 prod 部署卡核。
2. **k8s base manifests 陈置嫌疑**：`@sparkle_db:5432` 在 k8s/base 无同名 Service 对应（§D2）。
3. **start_celery.sh 脚本体**：F577 裁决「标弃不修」，本卡仅回填三处弃用指引 caveat（F577R1-C2），体内旧 URL 维持史录。
4. **celery compose standalone OTEL 缺靶**：standalone 面无 tempo（§D4），非劣化。
5. **`grpc://sparkle_backend:50051` 文档示例**（11_Docker配置详解.md:36）：非本卡家族，未顺手修（§D3）。

## 2. 验证边界

- **DNS 断言为静态渲染 + 机制实证，未真起栈**：本机零容器生命周期红线内，`sparkle-project_default` 网络空置（sparkle-project 栈未跑），别名集由（a）现役 cosmos 栈 `docker inspect` 实证 compose 别名机制 {服务键, container_name}、（b）本仓 compose config 渲染服务键/容器名清单推证。`make celery-up`/compose up 真实连通性验证需授权窗口真起主栈后补（预期 fail-loud 消失、worker 注册成功）。
- **supervisor 套件本机仅收集 7 例**（F577 receipt 计 17）：环境相关收集差异（daemon 环境态），6 passed + 1 failed 项在 main 主 checkout 复测同败（`test_once_cli_green_on_healthy_decoy`，daemon 环境态 base 同败，F577R1 同口径归因）；本卡 diff 零触碰 supervisor/probe/ops 文件，无回归面。
- **prod/services standalone 渲染失败为既有 `:?` 必填门/overlay 语义**，base 同形；补哑值后六场景全 exit 0。
- 本地桥映射集新增 `redis`：host 直跑进程若显式配 `REDIS_HOST=redis` 会映射到 127.0.0.1（原 `sparkle_redis` 同语义）；docker 内不受影响（原值返回走网络解析）。远程真名恰为 `redis` 的极端配置会被误映射——与既有 `sparkle_db` 映射同风险面，语义未扩大。

## 3. 红线遵守

零 up/down/restart/run；docker 只读面仅 `docker ps`/`docker inspect`/`docker network inspect`/`compose config` 渲染与 pytest 内部既有 inspect；主 checkout 零改动（base 对账测试在主 checkout 只读跑 pytest，无写面）；临时哑值 `.env` 用后即删未入库（.gitignore:61 覆盖，`git status` 零 .env 残留）；不 push；服务键/container_name/volume 名逐字节未动。
