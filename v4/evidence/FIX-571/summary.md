# FIX-571 summary — 共享数据面三联事故修复（P1）

**结论：三事故全修复并验证；死信 230 条目（94 唯一）全清点回放，93 去向已在库（复验 dedup）、1 条不可解留档留队；零数据删除、零伪造、零他仓文件改动、凭据零回显。**

## 三事故逐项状态

| # | 事故 | 修法 | 状态 |
|---|---|---|---|
| ① | sparkle_db host 侧鉴权 09-28 起损坏（容器 env 与卷内 role hash 不匹配 + 本仓 .env 指向的 `brsama` 角色在真数据卷上不存在） | SQL 层 `ALTER ROLE postgres` 对齐容器 env 值 + `CREATE ROLE brsama LOGIN SUPERUSER` 对齐本仓两 .env；未动任何容器 env/他仓文件 | **FIXED**：host 侧 brsama/postgres 双路 + 容器 socket 三路全通；guest auth 200 且真实落库 |
| ② | 共享 queue:billing 坏凭据驻留 worker 竞争消费（152 行计量丢失 + 死信 230 条目堆积） | 旧栈停止（SIGTERM 全优雅退出）→ 新栈凭据修复后单消费方 → 先验证消费（5 条探针：队列排空/零新增死信/dedup 正确）→ 再回放 | **FIXED**：消费链路健康；152 行历史丢失不可逆（Q04 红项④既有事实，流内 usage 帧+58 行恢复批已补偿），预防达成 |
| ③ | 驻留 gRPC/引擎栈早于 Q04 依赖合并，不可作验证目标 | 按重启时点当前 main（13814d3c）重启三进程；修复 dev-stage3.sh 三处启动命令缺陷（`python` 缺失 / `go run` 单文件 / `make dev-up` FIX-557 陷阱门） | **FIXED**：:50051 五服务 reflection 可见、:8000/:8080 health 200、WS 鉴权链 200 |

## 回放总账

- 留档：230 条 → `dead_letter_archive_230.jsonl`（sha256 前 16 位 `0defcc744c40977d`）
- 构成：94 唯一 request_id（单条最多 8 份重复死信），229 wtq04-*（坏凭据 worker 所致 password authentication failed for user "postgres"）+1 cb6aac13（FK 违约）
- 基线：93/94 已在 token_usage（Q04 期正常落库+58 行直插恢复批覆盖）
- 回放路径：产品自身队列（BillingWorker 消费），非脚本直插
- 结果：93 duplicate 跳过（复验 dedup 语义）、1 失败留档（cb6aac13，user 已删 → token_usage_user_id FK 违约，保留于队列+归档）、token_usage 零伪造行、终态 `queue:billing`=0 / `dead_letter`=1

## 交付物

- `v4/evidence/FIX-571/run_manifest.md`（每步命令+exit code+前后对照，凭据占位）
- `v4/evidence/FIX-571/dead_letter_archive_230.jsonl`（死信逐条留档）
- `scripts/dev-stage3.sh` 修复（本卡脚本面）
- 分支 `fix/v4/f571-dataplane`（基点 main@5f3aead4），不 push

## 遗留风险（详 run_manifest §7）

引擎进程由另一会话前台 `make grpc-server` 持有（收尾若终止，用同路径重启即可）；栈代码时点 13814d3c（其后 main 的 FIX-562 与数据面无关）；gateway/.env 凭据对齐系本机本地修正（git-ignored，其他检出需同法）；LLM chat roundtrip 未跑（避免真实支出，五面均已实测）。
