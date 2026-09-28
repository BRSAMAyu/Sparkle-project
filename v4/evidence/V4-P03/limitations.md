# V4-P03 已知限制

1. **真实栈未做破坏性演练（设计如此）**：证据时点 engine-api/engine-grpc/gateway 三进程属他人会话，HEAVY 纪律下本卡未对它们执行 kill/自愈演练；失联检测与恢复闭环以专用 decoy 真实进程等价证明（同一监督器代码路径）。对真实栈的混沌级演练属 V4-Q07/原 Q-07 终验，不在本卡代跑。
2. **在跑网关 readyz=503（既有态，未处置）**：`/readyz` 报 database unhealthy（SASL auth failed for user postgres），`/healthz` 200。属运行栈既有配置/凭据问题，非本卡引入；本卡仅显性化。归网关属主会话处置；若按监督器策略该服务会被探测为红（有限重启后仍红→转告警），重启动作能否修复取决于其凭据配置，监督器不掩盖根因。
3. **redis 数据面检查仅到 liveness**：生产 Redis 需 AUTH，监督器无凭据（也不应持有），NOAUTH 应答判定为 alive-but-auth-gated；全量 ready（可读写数据）需运维显式提供只读凭据后另行启用，本卡不引入密钥。
4. **守护部署形态未落 launchd/supervisord**：本卡交付的是仓库内正式监督器（进程面等价于台账 530 行的「launchd/supervisord 提案」核心语义：自动拉起+防环+黑窗），开机自启/系统级集成（launchd plist 等）未做——属宿主机配置面，需机器属主决策；当前以 `--observe`/`--once` 模式供 cron/人工在用。
5. **FIX-542 修法方向③只做显性化**：网关对上游丢失的退出行为（后端死是否应退出）台账标注「若系设计则守护必配」——本卡未改变网关退出语义（行为面改动需更宽授权），以 readyz 分离探测+监督器告警承接，语义裁决留待属主。
6. **worktree 需手动移入 gitignored 生成物**：gateway `gen/`、mobile `lib/gen/`、backend `app/gen/` 不入库；新 worktree 跑 Go 构建/flutter/部分后端测试前需从主检出复制（本卡已复制，不入 commit）。此为仓库既有工作方式，非本卡引入。
7. **black 格式化差异**：新 python 文件按 black 120 格式化，与仓库部分既有脚本风格存在换行差异；ruff/mypy 全绿，未触碰既有文件格式。
8. **主题/selector 回滚证据为既有面复跑**：两域的本卡 delta 为零（如实按「当前仓库已满足本卡行为时做差量举证」执行）；证据仅证明回滚面在当前 SHA 在岗且可执行，不代表新增能力。
