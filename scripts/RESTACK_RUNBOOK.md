# 本地数据面重建 Runbook（RESTACK）— sparkle_db 属主铁律

> 适用面：本机 dev 栈（`docker-compose.yml`，容器 sparkle_db / redis / minio）因 Docker Desktop 重启、容器灭失后的重建。
> 不覆盖云端生产部署——那条路走 `scripts/deploy/bootstrap.sh` 与 `deploy/ROLLBACK.md`。
> 来源：FIX-557（2026-09-28 事故复盘，wt815 落册）；登记见 `scripts/README.md`。

## 铁律（任何重建前必读）

- **本地数据面属主 = sparkle-cosmos 仓 compose**。两仓（`sparkle-cosmos` / `Sparkle-project`）的 compose 都定义 `container_name: sparkle_db`，但真数据卷只挂在 sparkle-cosmos 项目名下——容器名同名，**卷前缀不同**（`sparkle-cosmos_` vs `sparkle-project_`）。
- **跨仓/任何重建前必查卷属主**：

  ```bash
  docker inspect sparkle_db --format "{{range .Mounts}}{{.Name}}{{end}}"
  ```

  期望输出：`sparkle-cosmos_sparkle_postgres_data`。若看到 `sparkle-project_` 前缀 = 静默挂了空卷，立即停手，走下文纠偏步骤。
- 根因机制：容器名全局唯一且先到先得。容器灭失窗口内从错误仓 `up`，会以错误仓的项目前缀**静默抢注同名容器并挂空卷**（名字不冲突，因为旧容器已灭）。长期修法 = 两仓 compose 容器名分化（未实施，台账 FIX-557 存续注记）。
- 判属主也可不经容器：`docker volume ls` 看前缀，或 `docker compose ls` 看哪个项目 `running`——2026-09-28 实测本机只有 `sparkle-cosmos` 项目在跑、真数据卷 `sparkle-cosmos_sparkle_{postgres,redis,minio}_data`。

## 09-28 事故复盘（5 行）

1. Docker Desktop 用户重启 → 3 容器（sparkle_db/redis/minio）尽灭，daemon CLI 一度僵死。
2. 幸存进程浅探针绿（gRPC :50051 / uvicorn :8000 尚在）造成"栈还健康"假象；DB 路由实际 500。
3. 从错误仓（Sparkle-project）重建 sparkle_db：旧容器已灭故名字无冲突，静默挂上 `sparkle-project_` 前缀空卷。
4. 空库引发 role/auth 迷宫（`role "postgres" does not exist` 等假象故障），形似"数据丢失"。
5. 顺藤纠偏：inspect 查出挂载卷前缀错误 → 改从 sparkle-cosmos 仓重建 → 全链恢复（guest JWT 实证）；全程真数据卷零写入零损失，垃圾空卷已删。

## 纠偏步骤（发现挂错卷时）

1. **停写**：不在被误挂的空库上做任何迁移 / seed / 修数据——先止血，别把两套库都弄脏。
2. **取证**：`docker inspect sparkle_db --format "{{range .Mounts}}{{.Name}}{{end}}"`，记下错误的 `sparkle-project_` 前缀输出。
3. **摘除误建容器**：在错误仓目录 `docker compose down`。**任何场景绝不带 `-v`**（真数据卷在另一项目名下虽不受影响，禁 `-v` 是纪律不是侥幸）。
4. **正属主重建**：`cd /Users/brsama/code/GitHub/sparkle-cosmos && make dev-up`（等价 `docker compose up -d sparkle_db redis minio`）。
5. **复核属主**：重跑第 2 步命令，确认输出 `sparkle-cosmos_sparkle_postgres_data`；`docker exec sparkle_db psql -U postgres -c '\dt'` 见真实表 = 挂对。
6. **闭环 smoke**：health 探针 + guest 登录换 JWT 成功 = 恢复闭环；事故时间线补记台账/接力日志。
7. （可选）确认无误后清垃圾空卷：`docker volume rm sparkle-project_sparkle_postgres_data`——删前必须先 `docker volume inspect` 确认它不是任何在跑容器的挂载。
