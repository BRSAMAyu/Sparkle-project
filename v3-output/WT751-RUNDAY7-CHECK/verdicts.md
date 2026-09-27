# WT751 — day7 升栈手册执行前安全核验（verdicts）

- 核验人：wt751（独立核验，未参与 wt746 手册编写）｜核验时间：2026-09-28 凌晨（执行日 07:35 前）
- 对象：`/tmp/runday7.md` ≡ 主仓 `v3-output/WT746-REHEARSAL/runday7.md`（diff 逐字节一致，已证）
- 方式：静态对照（手册命令 ↔ 真实环境观察）。真实栈只观察不触碰；未运行手册任何变更性命令；未改手册。
- 观察基线快照：gRPC=PID 20028 `Python grpc_server.py`（:50051 LISTEN）｜uvicorn=PID 20029 `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --env-file .env`（:8000）｜gateway=PID 20130 `/tmp/sparkle_gateway`（:8080）｜容器 3 只 Up(healthy)：sparkle_db/redis/minio（仅发布 127.0.0.1:5432/6379/9000-9001）

## 总裁定：**GO —— 七项全 PASS，0 BLOCKER，1 WARN，6 INFO。手册可按原文执行。**

---

## 1. kill 面收敛 — PASS（附 1 WARN）

- 手册全部终止手段 = 第 2 步 `lsof -ti :50051/:8000/:8080 | xargs kill`（及 kill -9 同形态）。**全文无 pkill/killall/模式匹配杀**（grep 0 命中），按端口定靶。
- 三端口与真实进程一一对应且恰为目标：:50051→20028（gRPC）、:8000→20029（uvicorn）、:8080→20130（gateway）；当前 lsof 三端口输出仅此 3 PID，无第二进程。
- 不误伤 docker：3 容器仅发布 127.0.0.1:5432/6379/9000-9001，与三端口零交集；三端口 lsof 中无 docker-proxy。
- 不误伤其他会话：openclaw gateway 在 :18789（不匹配）；Docker Desktop agent 无端口监听。
- **WARN-1**：`lsof -ti :PORT` 未加 `-sTCP:LISTEN`，会把持有**ESTABLISHED 客户端连接**的本地进程一并杀掉。当前快照三端口零 ESTABLISHED（干净），但 07:40 执行时刻若有别的会话探针/浏览器 SSE 等连着 :8000/:8080，会被误杀。缓解已内置：第 2 步先打印并 tee before-kill 清单——但 kill 与打印在同一粘贴块顺序执行，无人审间隙。建议（下一版手册，本次不改）：执行者粘贴第 2 步前先单独跑一次 `lsof -nP -i :50051 -i :8000 -i :8080` 目视，或命令加 `-sTCP:LISTEN`。day6（轮#163）同机制无事故，不构成 BLOCKER。
- INFO-1：若某端口此刻无进程（如 gateway 已自灭），`xargs kill` 空参执行 `kill` 打 usage 报错、exit≠0——无害噪音，勿误判为失败。

## 2. 状态文件不可触 — PASS

- `/tmp/northstar_ns001_real_drive_state.json` 在手册中恰出现 3 处：铁律声明（只读）、第 0 步 `ls -la`（只看元数据，明示不 cat）、第 7 步 JOURNEY 探针 `json.load`（纯读）。**全文 rm/mv/cp/重定向对它零触及**（全文 `rm|mv|docker stop/rm/restart|pkill` grep 0 命中）。
- 唯一写者是第 8 步 gate_day7.py——铁律钦定"gate 脚本自己写"。已读 gate 源码证实：仅写 `day7_done/day7_task_id/day7_completed_at` 三键并备份至 `Sparkle-sysrev/.journey_ns001_state_backup.json`（该备份文件在位，2589B）；备份是 gate 自带动作，非手册命令。
- 第 5 步 gateway 备份是 `cp` 非 `mv`，目标 `/tmp/sparkle_gateway.day6.bak` 当前不存在（无覆盖风险）。
- STATE 现状与 gate 预期吻合（仅检元数据/键位，未回显任何值）：day6_done=True、day7_done 未置、gate 所需 4 键（gateway_url/run_id/main_username/main_password）齐。
- INFO-2：gate 对 STATE 的写入非原子（`open("w")` 截断后写，先 STATE 后 BACKUP）；极端情况（写一半进程死）STATE 可损、备份仍留 day6 旧态可恢复。gate 内部属性，非手册缺陷，day6 同形已实录跑通，无需行动。

## 3. docker 安全 — PASS

- 手册直接 docker 命令仅第 0 步 `docker ps`（观察）。无 stop/rm/restart/kill/down/compose（grep 0 命中）。
- proto-gen 内部 `docker run --rm sparkle/proto-toolchain:latest`（proto_toolchain.sh:28）：镜像本机缺失 → 创建即失败、`--rm` 无残留，回落宿主工具链（:33 WARN 文案与手册预期逐字一致）。对运行中 3 容器零影响。
- gateway 重建 = 宿主 `go build -o /tmp/sparkle_gateway ./cmd/server`，产物在 /tmp，sparkle_db/redis/minio 全程不被触碰。

## 4. 命令真实性 — PASS

- `backend/scripts/run_grpc_with_env.sh`：存在、可执行（776B）；darwin 分支打印 `✓ Set DYLD_LIBRARY_PATH for WeasyPrint` 与手册预期一致；从 backend 解析 `.venv/bin/python` 后 exec `grpc_server.py`（该文件在位 10022B）。
- **Makefile :338 原文**：`cd backend && $(BACKEND_PYTHON_ABS) -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --env-file .env` ——手册第 4 步即其后台化形态，且在跑 PID 20029 命令行与之逐字吻合。
- `/tmp/sparkle_gateway`：在位（58.5MB，09-27 08:26），即当前运行二进制；`go build -o` 目标路径钉死成立。
- `/tmp/gate_day7.py`：在位 **3542 字节（与手册第 0 步预期分毫不差）**；纯 stdlib（json/sys/datetime/pathlib/urllib）；M1d6→M4d6 步 id、打印行（`[M1d6] login main user: 200`、`day7 task: ...`、`state 已更新并备份；day7 门 PASS`）与手册预期序列逐条对得上；非 200 即打 STOP 并 exit 1；证据落 `/tmp/ns001_journey_out/evidence/steps/`（目录在位）。
- proto-gen 预期输出三段均找到原文出处：Makefile:239 `✅ Protobuf code generated successfully.`；proto_toolchain.sh:33 docker 回落 WARN；backend/scripts/sync_buf_python_stubs.py:74 `Synced ... stubs, converted ... re-exports.`。
- gen 三目录 = backend/gateway/gen、backend/app/gen、mobile/lib/gen，均入 .gitignore:244-246；当前 `git status --porcelain | grep gen/` 为空（手册判据成立）。
- alembic 单头：对 172 个版本文件做 AST 解析，**恰一头 `wt598_20260927`**（down_revision=wt539_20260926），与手册预期一致。注：核验首版正则曾误报 9 头（漏多行 tuple 型 down_revision），AST 复核后定谳——手册预演结论无误。
- venv：uvicorn 0.42.0 / grpcio 1.80.0 在位（与附 A d 一致）；宿主 buf、go 均在 /opt/homebrew/bin（回落路径可用）；backend/.env 在位（6721B，SECRET_KEY 经 settings 消费，app/core/security.py:57）。
- smoke 端点真实：gateway `/healthz` 路由注册于 gateway/internal/handler/health.go:79；引擎 `docs_url="/docs"` 显式开启于 app/main.py:893。

## 5. 回退路径完整性 — PASS（附 2 INFO）

- 附 C 回退 = 按第 3—5 步原命令重启三进程：三条命令全部对照现树证可执行（脚本/venv uvicorn/go build/二进制均在）。gateway 保险成立：先 `cp` 留 `.day6.bak`（此刻二进制未被运行进程占用——第 2 步已先杀，无 ETXTBSY），build 失败可 `cp` 回退 + nohup 重启。
- 回退零不可逆：无 alembic upgrade、无手工 STATE 写、gen 可再生——与附 C 自述一致。
- 留证指令可跑：全部 tee/tail 目标在 /tmp；grpc/uvicorn/gateway 日志由 nohup 重定向自动创建，`tail -50 | tee` 必有所指。
- INFO-3：第 5 步 `go build` 本身**未内联 tee**，失败留证行要求"build 输出 tee /tmp/day7_step5_build.log"——实际需失败后带 tee 重跑一次（构建无副作用，重跑安全可采）。与第 3/4 步的自动落证略不对称，注意即可。
- INFO-4：磁盘现状 `df -h /` 可用 **2.7Gi**，过手册 ≥2G 门槛但低于 day6 先例的 3G；若凌晨至 07:35 间续跌，第 0 步会依规 STOP——这正是该步设计意图，执行者勿强行放行。

## 6. 时间盒合理性 — PASS（附 1 WARN）

- 名义算术：07:35 段（自检 2min + proto-gen 实测 16.9s，cap 5min）✅；07:40 段名义 = kill 30s + gRPC 等待 30—90s + uvicorn 20—60s + build 7.6s + gateway 起 Await ≤60s ≈ 3.5—4.5min ≤ 10min ✅；07:50 段（alembic ~8s + smoke ~1min）✅；至 08:00 门留有 ≥8min 缓冲。
- WARN-2：若各步都打到各自超时上限，第 2—5 步最坏 = 0.5+3+3+5+1 = **12.5min > 10min 时段**，将侵占 07:50 段。单次 cap-out 可被 07:50 段 ~8.8min 空闲吸收；两步以上 cap-out 已属多重重叠失败，按手册 STOP 纪律本就应停——不结构性威胁 08:00 门，但执行者应把"单步逼近 cap"视为黄灯而非继续硬推的许可。
- INFO-5：uvicorn 就绪循环 24×5s=120s，而该步自述 cap 3min——循环先于 cap 2min 结束；若 uvicorn 第 130—180s 才就绪，循环无 "UP" 输出但进程可能仍在起。循环耗尽≠死亡，应先 tail 日志再判 STOP（手册已给 tail 指令，补此判读心智即可）。

## 7. 顺序依赖 — PASS

- gRPC 严格先于 uvicorn：第 3→4 步写死，时间盒表同样固化（07:40 段内序）。alembic 先于 smoke：第 6→7 步写死（同 07:50 段）。旧 gateway 死透再重编：第 2 步注释 + 第 5 步"路径钉死"双处固化（day6 事故教训在位）。
- 引擎探针贯彻轮#177 定谳：第 7 步探 :8000 用 **`/docs`**（并明示"引擎 /healthz 404 是路径差异"勿误读）；:8080 用 `/healthz`（路由实存）；gRPC 就绪用端口 LISTEN 轮询（不对 50051 发 HTTP，正确）。
- proto-gen（第 1 步）先于 kill（第 2 步）对在跑进程无影响：Python/Go 生成物落盘不回灌已加载内存，安全。

---

## 问题分级清单（汇总）

| 级别 | 编号 | 内容 | 行动 |
|---|---|---|---|
| BLOCKER | 无 | —— | 无需改手册；台账 485/486 已复核空闲（grep 0 命中）但**无需占用**，未建 worktree、未登记 DYNAMIC_ISSUES |
| WARN | WARN-1 | `lsof -ti` 未限 LISTEN，07:40 若有本地进程持 ESTABLISHED 连接三端口会被连带 SIGTERM（当前快照干净；day6 同机制无事故） | 执行者粘贴第 2 步前先目视一次三端口 lsof；下版手册可加 `-sTCP:LISTEN` |
| WARN | WARN-2 | 第 2—5 步全员打满上限 = 12.5min > 10min 时段 | 单步逼近 cap 视为黄灯；两步以上失败即 STOP，勿硬推挤 08:00 门 |
| INFO | INFO-1 | 空端口时 `xargs kill` 打 usage 错（无害噪音） | 勿误判为失败 |
| INFO | INFO-2 | gate 对 STATE 写入非原子（gate 内部属性，day6 同形已实录） | 无行动 |
| INFO | INFO-3 | 第 5 步 build 输出未内联 tee，失败留证需带 tee 重跑（安全无副作用） | 注意即可 |
| INFO | INFO-4 | 磁盘 2.7Gi 过 ≥2G 门槛但低于 day6 先例 3G | 第 0 步自会裁决，勿强推 |
| INFO | INFO-5 | uvicorn 循环 120s < 自述 cap 3min；循环耗尽≠进程死亡 | 先 tail 日志再判 STOP |

## 附：核验中自我纠正记录（存档备查）

- alembic 头判定：首版正则解析误报 9 头（lane_k/lane_d 等文件 down_revision 为多行 tuple，单行正则漏采），改 AST 解析 172 文件后定谳单头 wt598_20260927。此为核验工具缺陷，非手册/仓库问题。
