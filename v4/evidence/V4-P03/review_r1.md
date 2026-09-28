# V4-P03 一审 receipt（独立审查 wtP03R1）

> 2026-09-28 · 审查会话未参与实现 · 分支 `agent/v4/p03` · 被审对象：feat `f14937de` + 证据 `ac5097b7`（本 receipt 在其后追加）
> 方法：只读审查 + 独立复跑全部可失败面 + 独立构造反例（未复用实现会话产物作为判据来源）。

## 总裁决：PASS_WITH_CHALLENGES

验收三条全部独立复证成立（失联可检、CWD 不决定资源路径、恢复/迁移/主题/selector 各有可执行证据）；C-1..C-6 逐一独立下判（详下），其中 C-4 判「部分覆盖、残缺口如实登记」；另发现两个挑战点 **R-1（up.sh 步骤4 `sparkle-redis` 漏修——附带修复宣称未完成）** 与 **R-2（`artifacts/ops/` 未入 .gitignore）**。均不阻断本卡验收，R-1 建议登记 FIX 后续。高风险卡仍需第二位独立审查。

## 1. 独立复跑（审查会话亲跑，非转抄）

| 面 | 结果 | 判 |
|---|---|---|
| Go i18n `go test ./internal/i18n/ -v -count=1` | 7/7 PASS | ✅ |
| `pytest test_supervisor_probe.py test_service_supervisor.py` | 17/17 PASS（1.42s） | ✅ |
| 独立 CWD 红绿对照（自建二进制，见 §2） | base 红=FIX-542 签名逐字 / fixed 绿=source-anchored / env 错配 fail-loud | ✅ |
| `--once --data-plane` 真实栈只读探测 | exit 1：gateway alive(healthz 200)/not-ready(readyz 503)、engine-api/grpc 绿、属主绿、redis NOAUTH 诚实标注 | ✅ 与 run_manifest 命令8 逐项一致 |
| 迁移契约门 `BASE_REF=4a5dc5f2` | exit 0（No changed migration files） | ✅ |
| 主题回滚 flutter 2 测 | 2/2 PASS | ✅ |
| selector `test_semantic_selector.py` | 77/77 PASS | ✅ |
| mypy / ruff / black / go vet / gofmt | 全绿零漂移 | ✅ |
| 26 新测构成核对 | 7+10+7=26，与 denominator 一致；计数为实测收集数非声明数 | ✅ |

## 2. 独立构造的 CWD 错配红例（不复用实现会话的二进制/日志）

审查自建基线：`git worktree add --detach /tmp/p03r1_base 4a5dc5f2`（精确基 commit，非主检出口头 SHA）+ 移入 gitignored `gen/`，与 wtP03 各建一 binaries；同一敌意 CWD、同一 env 面（同 JWT_SECRET throwaway、PORT=8081、POSTGRES_PORT=1 令 DB 即拒零栈接触）：

- **base@clean hostile CWD**：`"Failed to initialize i18n, falling back to defaults"` + `open locales: no such file or directory` —— FIX-542 原始失败签名逐字复现（红）。
- **fixed@同一 CWD**：`"i18n locales initialized","locales_dir":"…/wtP03/backend/gateway/locales","resolution":"source-anchored …"`（绿）。
- **fixed@bogus CWD（构造仅含 en.json 的伪 locales/）**：仍 source-anchored，伪目录不被采纳（CWD 存在性不决定路径）。
- **fixed + `GATEWAY_LOCALES_DIR=/nonexistent_p03r1`**：`"Failed to resolve locales dir"` + `is not a valid locales dir` —— 显式错配 fail-loud 不静默。

实现会话 /tmp 日志三件（p03_base_wrongcwd / p03_fixed_wrongcwd / p03_negative_env）签名称与证据一致；JWT_SECRET 是否同值日志不可证（网关不回显），但审查自身对照已同 env 面控制，结论不依赖该回溯。

## 3. C-1..C-6 逐判

### C-1 decoy 等价性 —— 成立（带边界，不削弱本卡验收结论）
语义面差异清算：探测接口是协议级（TCP connect / HTTP GET+状态码判定），对被测进程的语系（python http.server decoy vs uvicorn/gRPC/Go gateway）无假设——decoy 与真实服务在该接口上可区分的只有端口与进程身份，而这正是探测面抽象掉的维度。且真实路径红已额外在真实栈上单次实证：审查亲跑 `--once --data-plane` 捕获 gateway alive/not-ready 分离红（既有 readyz 503），即探测判据对真实栈的判红能力非仅 decoy 推定。**未等价面（如实登记）**：restart 动作的真实命令串（`make api-server` 等三条）未对真实服务演练（HEAVY 纪律，他人会话所有）——decoy 证明的是监督机制闭环（杀→红→restart 执行→绿→告警留痕），不证明真实 make 目标能在实机把死引擎拉回绿；该残面属 V4-Q07 混沌终验，绑定文件已显式指派（"P03 监督面是受测对象而非替代"）。判定：验收语句「进程失联能被检测」全证；「恢复」为机制级可执行证据——与本卡交付声明一致，无越级宣称。

### C-2 红绿对照混淆变量 —— 控制成立
审查以精确 base commit `4a5dc5f2` 独立构建基线（比实现会话"主检出 main@4a5dc5f2"更硬：后者 SHA 无法回溯验证，但审查从精确 commit 重放得到同签名，结论稳健）。diff 范围核：两二进制间编译面差异仅 main.go i18n 初始化块 + 新增 internal/i18n 包（`git diff 4a5dc5f2 f14937de --stat` 逐文件核过，其余为脚本/测试不入二进制）；两次启动同 CWD、同 env 面、同 DB-fatal 终点（两日志均止于 `Unable to initialize database`）。未发现其他混淆变量。

### C-3 readyz 503 既有态定性 —— 独立核成立
三重佐证：(1) 审查亲 curl：/healthz 200、/readyz 503 body `database unhealthy … failed SASL auth: FATAL: password authentication failed for user "postgres" (SQLSTATE 28P01)`——与证据记载一致；(2) 在跑网关进程 PID 77602 启动于 09:55:45，早于本卡证据时点（21:37）与提交（21:47）约 12 小时，且二进制为 `/tmp/sparkle_gateway`（本卡之前构建）——503 是该进程运行时凭据错配的属性，时间上先于本卡；(3) 本卡 diff 不触达 readyz/DB 凭据面（main.go 仅 i18n 块，且 i18n 失败非致命、位于 DB init 之前；handler/config 零改动）——结构上不可能由本卡引入。定性为既有态、归网关属主会话：成立。

### C-4 up.sh 预检穷尽性 —— 部分覆盖（case 分支对本仓状态空间穷尽且 fail-closed；FIX-557 事故触发路径本身不可及，残缺口须继续登记）
审查以 mock docker 干跑全部 case 分支（零真实容器改动）：S1 健康+真属主→SKIP 不重建；S2 在跑但挂 `sparkle-project_*` 错卷→die 指向 runbook；S3 容器灭失+真卷存在→无 `SPARKLE_ALLOW_RESTACK=1` 即 die；S4 显式越权→warning 后放行；S5 全新机（无真卷）→放行。分支对本仓"容器×卷"状态空间穷尽、方向全部 fail-closed。**残缺口（三条）**：(a) FIX-557 实际事故形态是「从 Sparkle-project 仓发起重建」——该动作在另一仓的脚本里，本仓 up.sh 结构上无法拦截；预检拦到的是事故前（本仓死窗，S3）与事故后（错属主在跑，S2）两个状态，台账长修「两仓容器名分化」仍 OPEN（绑定/limitation 如实登记，本审查确认该登记准确）；(b) 预检只门 sparkle_db——redis/minio 属主无门（事故中三容器同灭，错仓重建会三面同错）；(c) bash 预检本身无自动化测试（被测的是 Python 同构面），本审查干跑即补位证据，但回归无守卫。判：不阻断（预检声称的保护面实现了），但 C-4 挑战答案应如实保留 (a)(b) 为已知残缺口。

### C-5 redis NOAUTH 记活定性 —— 可接受（liveness 语义正确，无 fail-open 后果）
亲核真实栈：`redis-cli ping` → `NOAUTH Authentication required.` 且 exit 0（redis-cli 服务器错误不回传退出码——实现会话首版按 exit code 判活确实是假绿，纠偏方向正确）。现判据按应答体：NOAUTH=alive-but-auth-gated。审查裁定其成立的三点：应答本身即证明服务器在跑（死服务无法产生协议应答，死 redis=连接异常=红，fail-closed 在真正要紧处成立）；该结果不入 `all_green`/exit code（代码核过 `report["all_green"] = all_green and owner["ok"]`，data_plane 仅展示），也不驱动任何重启（observe-only）；备选「无凭据=红」会在任何带 AUTH 的部署上恒红，告警疲劳反而有害。小疵：`"AUTH" in detail` 子串匹配偏宽（如 `ERR Client sent AUTH, but no password is set` 也会被标 auth-gated）——liveness 语义仍真，仅标签可能不精确，不要求改判据。

### C-6 外部门绑定语义泄漏 —— 无泄漏
源核：`v3/07_tasks/tasks.json` 中 O-01/Q-07/Q-08 三门 status 均为 TODO（审查亲读 JSON）；绑定文件 `original_status` 三门逐字沿用 TODO、`does_not_replace_authorization=true` ×3；`candidate_readiness_snapshot` 标注的是 V4 候选面（BLOCKED_EXTERNAL / NOT_RUN_BY_DESIGN ×2），非门状态改写；Q-07 绑定明文「不以 P03 证据替代终验」。tasks.json 增量仅 P03 自身 PENDING→in_progress/REVIEW_READY。无任何「以 V4 证据翻转原门状态」语义。

## 4. 红线亲核（审查会话首尾各一轮）

- 3 监听进程 PID 全程不变：:8000 Python 70080 / :50051 Python 77460 / :8080 sparkle_g 77602（lsof 前后比对一致）。
- sparkle_db/sparkle_redis/sparkle_minio 全程 Up 7 hours (healthy)，零重启；`docker inspect sparkle_db` 卷属主 `sparkle-cosmos_sparkle_postgres_data` 不变。
- 审查与实现会话的真实二进制探针均为「i18n 解析后即 DB-fatal 退出」设计（POSTGRES_PORT=1），不绑端口（8081 无残留监听）、不触 Redis/worker/agent。
- 零凭据、零 TCC、零云调用；JWT_SECRET 为 throwaway 非仓库密钥；审查未读取任何 .env 密钥值。
- 实现会话 `--once` 模式代码路径为 observe=True（run_one_cycle(services, states, observe=True)），结构上不可能对真实栈执行重启；测试告警面 monkeypatch 进 tmp，repo 无测试写入。
- worktree 干净：本审查期间零非预期文件落入（alert 日志未触发，artifacts/ops/ 无新增）。

## 5. 新发现（非 C-1..C-6 预登记面）

### R-1【CHALLENGED·建议登记 FIX】up.sh 步骤4 容器名漏修——「容器名漂移修复」宣称未完成
`scripts/dev/up.sh:73` 仍为 `docker exec sparkle-redis redis-cli ping`（真名 `sparkle_redis`）。亲测（对在跑健康栈只读）：步骤3 `sparkle_db` pg_isready exit 0 通过 → 步骤4 `sparkle-redis` exit 1 ×15 → `die "Redis not ready after 15s."`——**up.sh 在正常路径永远死于步骤4，步骤5-8（AGE init / knowledge index / Alembic 迁移 / seed）不可达**。基线核（`git show 4a5dc5f2:scripts/dev/up.sh`）：漏修行系既有（base 两处全错，修前死于步骤3、修后死于步骤4——非本卡引入的回归，但 commit message 与 diff_or_evidence_only.md 宣称「up.sh 容器名漂移修复（sparkle_db/sparkle_redis）」为未完成宣称）。修复成本一行；在修前应视为 up.sh 端到端仍不可用（预检面本身有效，已干跑证实）。
### R-2【低】`artifacts/ops/` 未入 .gitignore
监督器告警日志写 `artifacts/ops/supervisor_alerts.jsonl`，而 .gitignore 仅忽略 `artifacts/e2e/`、`artifacts/sgw*/`——真实守护运行后会产生未跟踪文件，违「会话产物/运行时数据永不入库」的防呆缺口（测试面已 monkeypatch 不受影响）。建议一行补 .gitignore。

## 6. 二审关注点建议

1. R-1 一行修复或 FIX 登记落账后再销账（本审不强制先修：属附带修复宣称面的诚实性问题，非卡验收判据面）。
2. C-4 残缺口 (a)(b) 是否随 V4-Q07 或独立 ops 卡收口（长修=两仓容器名分化）需属主裁决。
3. 真实 make 重启串的实战演练归属 V4-Q07，勿以本卡 decoy 恢复闭环替代宣称。

—— wtP03R1（未参与 P03 实现）· 2026-09-28
