# V4-P03 差量举证 — 运行韧性与 V3 外部依赖衔接

> 2026-09-28 · worktree wtP03 · branch agent/v4/p03 · base 4a5dc5f2 · HEAVY=True
> 一句话设计：**把 FIX-530/542 的临时看门狗与 CWD 隐患收编为仓库内正式监督面——Go 侧 locales 目录自锚定让 CWD 不再决定资源路径，Python 侧探测核心+监督器让进程失联可检、自愈有限、超限转告警；V4 候选以机器可读绑定挂原 O-01/Q-07/Q-08 外部门，不替代授权。**

## 1. 与台账原文的对齐（先读后动）

- **FIX-530**（`v3/06_agent_fleet/DYNAMIC_ISSUES.md` 行 402，FIXED@92179f4c）：billing 消费循环韧性壳已修；该行明言「进程守护正式化提案（launchd/supervisord）归 ops 卡」——**本卡即该 ops 卡**，交付 `scripts/ops/service_supervisor.py`（收编临时 `/tmp/engine_watchdog.sh` 的三连败+90s 防环+黑窗观察语义，加每小时上限与 JSONL 告警）。
- **FIX-542**（行 414，OPEN，ops 家族）：修法方向三条逐一落点——①守护统一（本监督器罩 engine-api/engine-grpc/gateway，探测判据与重启动作按服务配置）；②启动路径自锚定（Go `i18n.DefaultLocalesDir()` 源锚定链 + 监督器 restart 一律 `cwd=REPO_ROOT` 并导出 `GATEWAY_LOCALES_DIR`，双保险）；③上游丢失退出行为（`/healthz` 与 `/readyz` 分离探测使 alive-but-not-ready 显性化，本次真实栈即捕获一例）。

## 2. 差量（若已满足仅举证；最小增量）

### 新增
| 文件 | 作用 |
|---|---|
| `backend/gateway/internal/i18n/resolve.go` | locales 目录解析链：`GATEWAY_LOCALES_DIR` env（错配 fail-loud）→ 源锚定（`runtime.Caller`，CWD 无关）→ CWD 向上走查 → CWD 相对（遗留兜底）；`en.json`+`zh.json` 标记校验 |
| `backend/gateway/internal/i18n/resolve_test.go` | 7 测试：三敌意 CWD 等值、伪 locales 目录反例、env 覆盖、显式错配 fail-loud、子目录走查、Init 加载、标记校验 |
| `scripts/ops/supervisor_probe.py` | 探测与决策核心（纯函数、stdlib-only）：TCP/HTTP 探测 + 连败阈值/冷却/每小时上限/黑窗状态机——「活 PID ≠ 健康」在此编码 |
| `scripts/ops/service_supervisor.py` | 正式守护：自锚定 REPO（重启动作 cwd=REPO_ROOT）、health/ready 分离、有限重试→超限告警（不掩盖根因）、FIX-557 数据面属主只读预检（错属主→告警+拒绝）、`--once`/`--observe`/`--data-plane` 模式、JSONL 告警留痕 |
| `scripts/tests/test_supervisor_probe.py` | 10 测试（真实 decoy 进程）：失联红、伪失联红、503 红、阈值/冷却/上限/黑窗、CLI exit code |
| `scripts/tests/test_service_supervisor.py` | 7 测试（端到端）：真杀→exit 1、恢复闭环（红→restart→绿）、restart CWD 逐字断言、observe 不动手、上限转告警、属主预检真/负例 |
| `v4/evidence/V4-P03/*` | 五件套 + external_gate_binding.json |

### 修改（既有面修复，非重写）
- `backend/gateway/cmd/server/main.go`：`i18n.Init("locales")` → `DefaultLocalesDir()` 解析后 Init，成功记 INFO（含 resolution 诊断），失败记 WARN（含诊断）——启动语义（非致命回落）保持不变，仅路径来源改变。
- `scripts/dev/up.sh`：`docker exec sparkle-db/sparkle-redis` 容器名漂移修正（真名 `sparkle_db/sparkle_redis`）；compose up 前加 FIX-557 属主预检（已有 sparkle-cosmos 卷→不重建；错前缀→die 指向 RESTACK_RUNBOOK；死窗+真卷存在→要求 `SPARKLE_ALLOW_RESTACK=1` 显式越权）。
- `scripts/dev/healthcheck.sh`：同容器名修正（原 postgres_connect/redis_ping 两项恒假红）。
- `scripts/README.md`：登记 ops 监督面（REPOSITORY_STANDARDS 规则）。

## 3. 验收逐条举证（必须可失败）

### 3.1 进程失联能被检测，CWD 不决定资源路径
- **失联检测**（全部真实进程，无 mock）：健康 decoy→绿；`SIGKILL`→`--once` exit 1（test_real_process_loss_detected_red / test_once_cli_red_after_real_kill）；**伪失联反例**（端口关、进程面其他 PID 存活）→红（test_pseudo_dead_process_detected_red）——探测器不吃「进程存在」假象；活端口但 503→health 红。
- **CWD 不决定资源路径**：Go 单测真实 `os.Chdir` 到 `/`、`/tmp`、`$HOME` 解析等值；**真实二进制对照**——修复前基线二进制从 `/` 启动逐字复现 FIX-542 失败签名（`open locales: no such file or directory`），修复后二进制同 CWD 报 `i18n locales initialized ... resolution=source-anchored`；监督器层 restart 动作 `pwd` 输出逐字等于 REPO_ROOT 与调用方 CWD 无关。

### 3.2 无凭据/TCC 不越权，内部工作可继续
- 全程零凭据、零 TCC、零云调用、零 `.env` 密钥读取（启动探针 JWT_SECRET 为一次性 throwaway，POSTGRES_PORT=1 使 DB 面即拒）；真实栈三进程属他人会话，全程只读探测未杀未启；O-01 原状态（TODO/等用户 AK）原样沿用并在绑定文件中如实标注 BLOCKED_EXTERNAL——**内部监督/检测/绑定工作全部完成，外部门零越权**。

### 3.3 恢复/迁移/主题/selector 回滚分别有可执行证据
- **恢复**：test_full_recovery_restart_cycle——失联红→监督器执行 restart_cmd→服务绿+告警留痕（真实进程闭环）。
- **迁移**：`check_migration_contracts.py` exit 0（本卡零迁移；type/rollback_plan/verification_query/owner 契约门在岗）。
- **主题**：flutter `pixel_preview_prefs_guard/restore` 2/2——越界索引回落 classic（preview off=既有发布主题），合法档恢复。
- **selector**：`test_semantic_selector.py` 77/77——`SEMANTIC_SELECTOR_MODE` off/shadow/live 三态，shadow 不改生产路由，关 selector 即回 V3 安全策略（默认 off）。
- 附：FIX-557 数据面属主预检真/负例两端可执行。

## 4. 外部门绑定（不替代授权）
见 `external_gate_binding.json`：O-01（公网/证书/费用——等用户，V4 不复制申请账号卡）、Q-07（V4-Q07 沿用原判据，P03 监督面是其受测对象而非替代）、Q-08（四结论独立，外部发布结论消费三门原状态）。三门 `does_not_replace_authorization=true`。

## 5. 诚实失败与纠偏记录
见 `test_results.json` honest_failures_during_work——含监督器自身被真实栈纠偏一轮（redis NOAUTH 假绿→按应答体判）。

## 6. 真实栈 readyz 发现（登记给舰队，非本卡回归）
证据时点在跑网关 `/readyz`=503：`database unhealthy, SASL auth failed for user "postgres"`（/healthz=200 alive）。属既有运行态凭据/配置问题，归网关属主会话处置；本监督器的 health/ready 分离正是为这类「假活」设计的显性化面。
