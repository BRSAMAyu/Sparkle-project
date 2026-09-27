# day7 终门前升栈序列执行手册（2026-09-28 07:35）

> 预演卡 wt746（agent/node-b/wt746/rehearsal）产出。全部步骤已在 worktree 干跑实证（预演基线 main@5bc14640 与 c2881a4a 双基线复证），干跑结论见附 A。
> 明晨执行位置 = **主仓 `/Users/brsama/code/GitHub/Sparkle-project`**（预演 worktree 不参与执行）。
> 原序列出处：fleet state 轮#163（day6 实证：kill 三进程→gRPC 先起→uvicorn→网关重编译→双 200+JOURNEY login 200）+ 轮#178/#185（day7 增补：proto-gen 重生成、alembic 单头）+ 轮#208/#224 附近 day7 门纪律。
> 铁律：`/tmp/northstar_ns001_real_drive_state.json` 只读（gate 脚本自己写）；docker 容器只观察不操作；`.env` 只读；任何一步非预期 → STOP、留证、记账，不硬造。

## 时间盒

| 时刻 | 动作 |
|---|---|
| 07:35 | 第 0—1 步（自检 + proto-gen） |
| 07:40 | 第 2—5 步（kill 三进程 → gRPC → uvicorn → gateway 重编+起） |
| 07:50 | 第 6—7 步（alembic 单头 → 三端 smoke） |
| 07:55 | 就绪确认，等 08:00 |
| 08:00 | 第 8 步 `python3 /tmp/gate_day7.py` |

---

## 第 0 步：前置自检（约 2 min）

```bash
cd /Users/brsama/code/GitHub/Sparkle-project
git status --porcelain                      # 预期：空或仅 fleet state/v3-output 类已知脏文件
df -h / | tail -1                           # 预期：可用 ≥ 2G（day6 先例：门前清到 3G）
docker ps --format '{{.Names}} {{.Status}}' # 预期：3 容器 Up (healthy)
ls -la /tmp/gate_day7.py                    # 预期：存在（3542 字节）
ls -la /tmp/northstar_ns001_real_drive_state.json   # 预期：存在（只看元数据，不 cat）
```

**失败留证**：任一不满足 → `df -h` / `docker ps` 输出 tee `/tmp/day7_step0_preflight.log`，STOP 上报主会话。

## 第 1 步：proto-gen 重生成（实测 17s，超时上限 5 min）

```bash
cd /Users/brsama/code/GitHub/Sparkle-project
make proto-gen 2>&1 | tee /tmp/day7_step1_proto.log
```

**预期输出**（预演实录顺序）：
1. `Unable to find image 'sparkle/proto-toolchain:latest' locally` + pull denied（本机无该镜像，正常）
2. `WARN: dockerized proto toolchain failed, falling back to host toolchain (PROTO_USE_DOCKER=0).`
3. `Synced 13 Python protobuf runtime stubs, converted 4 structured to re-exports.`
4. `✅ Protobuf code generated successfully.`

**判读**：
- 全程应 < 30s（含 ~5s docker 拉取尝试）；宿主 buf 工具链回落是**设计内路径**，不是失败。
- 生成物不入库（gen 三目录 gitignored）→ `git status --porcelain | grep gen/` 应为空。
- 可选零漂移核验（预演已证当前树零漂移）：`PROTO_USE_DOCKER=0 scripts/proto_toolchain.sh check-generated`，预期 diff 无输出。

**失败留证**：log 已 tee；补 `buf --version; go version; which protoc` 进同文件；STOP 上报（勿手改 gen）。

## 第 2 步：kill 三进程（约 30s）

```bash
lsof -nP -i :50051 -i :8000 -i :8080 | tee /tmp/day7_step2_before_kill.log
lsof -ti :50051 | xargs kill; lsof -ti :8000 | xargs kill; lsof -ti :8080 | xargs kill
sleep 2
lsof -nP -i :50051 -i :8000 -i :8080        # 预期：三端口 LISTEN 全部消失
```

- day6 教训（轮#163）：旧网关进程必须死透再重编，否则 `go build -o` 覆盖运行中二进制会踩 "旧二进制短暂上线" 事故。
- 若 kill 后端口仍占：`lsof -ti :<port> | xargs kill -9`，并记入留证。

## 第 3 步：gRPC 先起（预期 30—90s 内端口就绪，超时上限 3 min）

```bash
cd /Users/brsama/code/GitHub/Sparkle-project/backend
nohup ./scripts/run_grpc_with_env.sh > /tmp/grpc_day7.log 2>&1 &
```

**等待就绪**：
```bash
for i in $(seq 1 36); do lsof -nP -i :50051 | grep -q LISTEN && echo "gRPC UP after ~$((i*5))s" && break; sleep 5; done
```

**预期日志特征**（预演实录 import 链）：
- `✓ Set DYLD_LIBRARY_PATH for WeasyPrint`（darwin 分支）
- `LLMRouter initialized with 27 model configs`
- gRPC server serving 于 :50051

**失败留证**：`tail -50 /tmp/grpc_day7.log | tee /tmp/day7_step3_grpc_fail.log`；STOP 上报。常见根因：gen 未先生成（回第 1 步）、`.env` 缺失（SECRET_KEY 硬校验，预演实证）。

## 第 4 步：uvicorn 起（预期 20—60s 内端口就绪，超时上限 3 min）

```bash
cd /Users/brsama/code/GitHub/Sparkle-project/backend
nohup ./.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --env-file .env > /tmp/uvicorn_day7.log 2>&1 &
for i in $(seq 1 24); do lsof -nP -i :8000 | grep -q LISTEN && echo "uvicorn UP after ~$((i*5))s" && break; sleep 5; done
```

（即 `make api-server` 的后台化形态，命令从 Makefile :338 抄录核验。）

**失败留证**：`tail -50 /tmp/uvicorn_day7.log | tee /tmp/day7_step4_uvicorn_fail.log`；STOP。

## 第 5 步：gateway 重编 + 起（实测重编 7.6s 热缓存，超时上限 5 min）

```bash
cp /tmp/sparkle_gateway /tmp/sparkle_gateway.day6.bak    # 回退保险（可选）
cd /Users/brsama/code/GitHub/Sparkle-project/backend/gateway
go build -o /tmp/sparkle_gateway ./cmd/server            # 路径钉死：构建产物=运行产物 /tmp/sparkle_gateway（day6 事故教训）
ls -la /tmp/sparkle_gateway                              # 预期：mtime=刚才（新鲜度核验，防旧二进制上线）
nohup /tmp/sparkle_gateway > /tmp/gateway_day7.log 2>&1 &
for i in $(seq 1 12); do lsof -nP -i :8080 | grep -q LISTEN && echo "gateway UP after ~$((i*5))s" && break; sleep 5; done
```

**失败留证**：build 输出 tee `/tmp/day7_step5_build.log`；起不动可回退 `cp /tmp/sparkle_gateway.day6.bak /tmp/sparkle_gateway` 后重启（旧二进制仅昨夜 head 差，不阻 gate 排障）。

## 第 6 步：alembic 单头检查（实测 ~8s，超时上限 1 min；**绝不 upgrade**）

```bash
cd /Users/brsama/code/GitHub/Sparkle-project/backend
./.venv/bin/python -m alembic heads 2>&1 | tee /tmp/day7_step6_alembic.log | tail -3
```

**预期输出**（预演双基线一致）：恰一行 `wt598_20260927 (head)`。

**判读**：
- `(head)` 出现次数 ≠ 1 → STOP 留证登记（多头/空均阻塞）。
- 可选加严（只读）：`./.venv/bin/python -m alembic current`——live 库版本应等于 head；若 `current < head` 说明有未应用迁移 → **STOP，升级决策交主会话**（day6 先例=授权后显式 upgrade，勿擅自）。
- 注意：heads 会经迁移模块 import 全量 settings——依赖 `backend/.env` 的 SECRET_KEY（预演实证：无 .env 的裸树即 ValidationError；主仓 .env 在位无碍，已核存在不回显）。

## 第 7 步：三端 smoke（07:5x，约 1 min）

```bash
curl -s -m 5 http://localhost:8080/healthz        # 预期：alive / 200
curl -s -m 5 -o /dev/null -w '%{http_code}\n' http://localhost:8000/docs   # 预期：200
```

- **勿误读**：引擎 `/healthz` 返回 404 是端点路径差异（轮#177 定谳），引擎活性探针用 `/docs`。
- 可选（day6 先例）JOURNEY login 探针：与 08:00 gate M1 同一调用、幂等；凭据从 STATE 读、**不回显不落盘**：
  ```bash
  python3 - <<'EOF'
  import json, urllib.request
  s = json.load(open("/tmp/northstar_ns001_real_drive_state.json"))
  req = urllib.request.Request(s["gateway_url"] + "/api/v1/auth/login", method="POST",
      data=json.dumps({"username": s["main_username"], "password": s["main_password"]}).encode(),
      headers={"Content-Type": "application/json"})
  with urllib.request.urlopen(req, timeout=30) as r: print("JOURNEY login:", r.status)
  EOF
  ```
  预期 `JOURNEY login: 200`。保守者可跳过，gate M1 会再验。

## 第 8 步：08:00 门 `python3 /tmp/gate_day7.py`

```bash
python3 /tmp/gate_day7.py
```

**预期输出序列**（预演静态核验 + day6 同构实录）：
```
[M1d6] login main user: 200
day7 task: <id前8位> <标题>
[M2d6] today surface day7: 200
[M3d6] start day7 task: 200
[M4d6] complete day7 task: 200
state 已更新并备份；day7 门 PASS
```

**判读与留证**：
- 任一步非 200：脚本自带 `STOP: 非 200，留证 <step_id>，不硬造` 并 exit 1；证据已自动落盘 `/tmp/ns001_journey_out/evidence/steps/<step_id>_day7--*.json`，人工接手读 `response.body._preview`。
- `day:7` 标签未命中：脚本打印候选 TODO 任务（day6 同款兜底），非失败。
- PASS 后 state 置 `day7_done=True` 并同步备份至 `/Users/brsama/code/GitHub/Sparkle-sysrev/.journey_ns001_state_backup.json`（gate 自带，勿手工改 STATE）。

## 第 9 步：收尾记账（主会话）

- fleet state notes 轮次 + 接力日志登记；day7 门 PASS = 7/7 收官。
- 若第 8 步 STOP：证据 json + 对应步骤 log 路径一并入账，修复卡另派。

---

## 附 A：预演实证汇总（2026-09-27 深夜干跑，worktree /Users/brsama/code/GitHub/Sparkle-sysrev/wt746-rehearsal）

| 步骤 | 干跑结果 | 实测 | 基线 |
|---|---|---|---|
| a. make proto-gen | PASS（docker 回落宿主工具链，设计内路径） | 16.9s | 5bc14640 |
| a2. 生成物零漂移 diff | PASS——三 gen 目录与主仓逐字节一致 | — | 5bc14640 vs 主仓 gen |
| b. go build gateway | PASS（新鲜 gen 上构建） | 7.6s | 5bc14640 + c2881a4a 双基线 |
| c. alembic heads | PASS——恰一头 `wt598_20260927 (head)`，未执行 upgrade | ~8s | 双基线一致 |
| d. run_grpc_with_env.sh | 存在、可执行、可读；grpc_server.py 在位；uvicorn 命令=Makefile :338 原样抄录；venv uvicorn 0.42.0/grpcio 1.80.0 在位 | — | 同 |
| e. gate_day7.py | py_compile 过；纯 stdlib（json/sys/datetime/pathlib/urllib.request）；day6→day7 参数化 diff 干净；STATE 四键齐（day6_done=True/day7_done 未置）；证据目录与备份路径全在位 | — | /tmp 实测 |

## 附 B：已知非阻塞发现（4 项，均已核不计 V3-FIX）

1. **proto 工具链 docker 镜像本机缺失**：`sparkle/proto-toolchain:latest` 不存在 → 每次 gen 浪费 ~5s 拉取尝试后自动回落宿主 buf。行为已实证可交付；如需省时可 `PROTO_USE_DOCKER=0`，但默认保持命令原样。
2. **主仓 gen 陈旧残留**：`backend/gateway/gen/gen/`（9-26 双层嵌套）与 `backend/app/gen/proto/`（5-16）非当前工具链产物（预演全新生成不含二者），仅 diff 噪声，不阻构建与运行。
3. **裸树跑 alembic 需 SECRET_KEY**：迁移模块 import 级联加载 settings；worktree 无 .env 时需 `SECRET_KEY=...` 前缀。明晨在主仓执行，.env 在位，无影响。
4. **主仓 main 在预演期间持续推进**（5bc14640→c2881a4a，wt741/742/743/744 依次集成）：proto/ 与 alembic/ 两基线间零变化，预演证据可继承；若 07:35 前 main 再推进，本手册各步与内容无关，照常执行即可。

## 附 C：回退路径

- 全序列无不可逆动作：不改 DB（无 upgrade）、不碰 STATE、gen 可再生、gateway 二进制有 .day6.bak 保险。
- 任一步 STOP 后恢复旧栈：按第 3—5 步原命令重启三进程（代码未变时 gen/binary 皆可复用现树产物），三端 smoke 过即恢复 day6 夜间形态。
