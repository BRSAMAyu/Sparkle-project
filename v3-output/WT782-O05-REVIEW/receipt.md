# WT782 · O-05 独立审查 receipt（Backup/Restore + Agent Run/Memory Consistency 演练）

- **审查对象**：V3 卡 O-05（`v3/07_tasks/cards/O-05.md`，OPS/V3-6/critical/HEAVY/2 reviewers）交付 wt773
- **交付基线**：main@a7698ab6（亲证 HEAD 祖先 ✓）；交付 commit 原始 SHA `86972fc9`（wt773 分支），主干集成 SHA **`1680d16c`**（rebase 版，代码与证据文件清单一致；台账少 1 行，见 §7）
- **审查点（integration HEAD）**：本 worktree `agent/node-b/wt782/o05rev` @ `7dfe1577`（轮#271）；目标文件 `git diff deb5e27c..7dfe1577` 零变更，审查结论对当前 HEAD 有效
- **环境铁律遵守**：零 docker 容器（未起任何栈做 restore 复刻）；以「实录可复现性审查 + 不变量逻辑审查 + 脚本静态复核 + sqlite 短命单测/变异」替代真演练；生产栈/ns001 零接触

## 结论：**APPROVE（附销账前置条件，见 §9）**

修复面（V3-FIX-504 脚本面 + V3-FIX-505 restore 侧）代码正确、测试全过、实录证据链自洽且对失败切片（GJ08 real_llm）如实登记。发现 4 项新残差/簿记问题（§5/§6/§8），均不推翻交付本体，但 2 项为销账前置（台账补登、FIX-505 残差范围修正+AOF 缺口登记）。

## 1. 独立执行记录（非转抄交付者数据）

| 执行 | 结果 |
|---|---|
| `unittest scripts.tests.test_o05_restore_consistency`（本 worktree，integration HEAD，backend venv） | **14/14 OK**（0.013s，sqlite 内存库，零 DATABASE_URL） |
| 变异抽验 M1（INV-2 新形状：向 r1 追加 `occurred_at` 更晚的 FAILED 迁移、状态行留 SUCCEEDED——异于交付 red 测试的"改状态行"形状） | INV-2 **红**，报 `状态行 SUCCEEDED != 最后迁移 to_status FAILED` |
| 变异对照 M1b（同形迁移但 occurred_at 更早=乱序重放） | INV-2 **不误报**（时序取末条判据正确） |
| 变异抽验 M2（INV-4 纯回填：不加 outbox 行，直接降计数器至 0 < max_seq=1） | INV-4 **红**，报"计数器回填，新事件将撞号" |
| 空洞性验证 M3（复活墓碑 m2 后单跑 INV-5） | INV-5 **仍 PASS**——独立坐实 §5 判据空洞性 |
| CLI 端到端 M4（文件 sqlite：`--capture-baseline` rc=0 → 注入复活漂移 → `--baseline` 校验 rc=1，报文含 `episodic_recallable`、`verdict=FAIL violated=INV-7`） | **通过**（退出码契约可用，可接 CI/cron） |
| ruff / black(120) / mypy `--ignore-missing-imports`（两新文件） | 全过（与 notes §8 声称一致） |
| `bash -n` 两脚本 | 语法过 |

## 2. 卡面 Work 对账

1. 备份 PG/MinIO/必要 Redis durable state；恢复 staging — ✅（一次性四容器栈代 staging，PG/Redis/MinIO 三面齐 + checksum + manifest；restore 后按 CONFIG dir 落盘）
2. 恢复期间/之后 Agent run、Memory epoch、outcome consistency — ✅（INV-1..7 校验器 + 演练执行；本审查 §5 逐条复核判据有效性）
3. RPO/RTO 实测 — ✅ 如实（操作时长 5-7s/6s 实测；端到端 RPO=cron 周期最坏 24h 如实登记，未冒充端到端 RTO）

## 3. 卡面 Acceptance 对账

| 项 | 裁定 |
|---|---|
| 恢复后 GJ03 通过 | ✅ `gj03_summary.json` PASS 11/11（18:56:49Z，经网关 :18080 对恢复栈，时间线与 backup 18:53:29 → checker 18:53:40 衔接自洽） |
| 恢复后 GJ08 通过 | ⚠️ 4/6 如实：非 LLM 面（memory_readback/calibration/correction）全过；两 `*_real_llm` 步 HTTP 200 空 text（`gj08_steps.jsonl` 原始实录在库，`event_types: ["error","done"]` 与"无 key→demo mode"自洽）。环境阻塞切片，交接"有 key 环境 `--gj GJ08` 补证"（§10.3）——**不阻塞销账**，但属卡面剩余切片 |
| run query 通过 | ✅ notes 三面 200（与 GJ03 同链路佐证；原始 trace 未单独入库，见 §6 缺口 3） |
| 无已删 memory 复活 | ✅ 判据实质在 INV-7 `episodic_recallable` 基线比对（M3/M4 亲证红路径）；INV-5 单独判据空洞见 §5 |

Forbidden 四条逐查：未重建权威真源（只改 scripts/ 新增文件）；无 mock 冒充（GJ08 失败切片如实照登）；无"静态阅读宣称体验通过"（起了真引擎+真网关跑全链）；未弱化安全守卫（restore 排空连接限于 DR 语境且注释在案；`.env` 随包 chmod 600 是补强）。

## 4. 修复面 diff 逐 hunk 复核（504/505）

| hunk | 复核结论 |
|---|---|
| `pg_dump --clean --if-exists`（backup） | ✅ 语义正确：转储自带 DROP/重建，非空库重放=精确快照；`--if-exists` 保空库路径。M1/M4 与 14 用例 + 演练 GREEN 佐证。注：`docker exec -t`（TTY）为**既有**写法（本 commit 保留非引入），pg_dump 纯文本经 pty 的 CRLF 在 psql/COPY 文本模式被容忍且演练内容核对全过——留观察项 |
| restore `ON_ERROR_STOP=1` + `pg_terminate_backend` 排空 | ✅ 假成功禁令成立；排空防 --clean 的 DROP 被长事务锁挂死，`|| true` 不吞后续错误 |
| MinIO backup 改 `docker cp`→宿主 tar | ✅ 方案正确——`docker cp` 走 dockerd 归档流，**不依赖容器内 tar**，生产镜像无 tar 的事实缺陷被真修；产物名不变保 restore 兼容。⚠️ 小缺陷 A：else 分支（数据路径缺失）WARNING 后跳过，但 `checksum_file ... minio-data.tar.gz` 对不存在文件必失败 → `set -e` 在 checksum 步中止、manifest 不产——"skip"实际不 graceful（fail-loud 可接受，但与自身 WARNING 矛盾，且恢复侧对缺 tar.gz 是容错的，两侧不对称） |
| MinIO restore 精确交换（rm 含 `.minio.sys` + 宿主解包 + docker cp + restart） | ✅ 与 PG --clean 同一快照语义；`${MINIO_DATA_PATH:?}` 防空值 rm 灾难 |
| redis restore 按 `CONFIG GET dir` 动态落盘 | ✅ `tail -n 1` 取值正确，缺省回退 /data。⚠️ **小缺陷 B（新发现）**：`_redis_cli_args=()` 空数组在 `set -u` 下展开，bash <4.4（**本机唯一 bash=3.2.57**，`/bin/bash -c` 实测 `arr[@]: unbound variable`）即崩——无密码 restore 路径在 macOS 默认 bash 上 PG 恢复完成后中止（fail-loud 但部分恢复）。交付者实录未触发系演练容器带密码（非空数组）。修法一行（条件展开或 if/else 调用） |
| STRICT_SCHEMA 代差门 / manifest 增强（alembic_head/pg 版本/耗时） | ✅ 恢复前比对，方向正确（新代码吃旧包）；默认告警+ STRICT 硬门分层合理 |
| `.env` 随包 chmod 600 | ✅ 代码路径正确；但演练 manifest `config_files: []`——**该路径未在演练实测**（见 §6 缺口 2），commit message"实测"措辞过强 |

## 5. 不变量逻辑审查（INV-1..7 判据能否抓住对应漂移）

| # | 判据复核 | 裁定 |
|---|---|---|
| INV-1 | 词表挂冻结真源（`app.core.run_state_machine` import，退化副本+单测对账钉）；本审查比对真源：12 状态/7 终态/归因词表逐字一致（USER_STEP/APPROVAL 属 RunWaitKind 非混淆）；`heartbeat_at` 生产列 nullable=False（`agent_run.py:116`）无假阳 | ✅ |
| INV-2 | 末条迁移投影：`occurred_at DESC, created_at DESC, id DESC` 取末条；M1/M1b 证明"追加迁移漂移"抓住且乱序不误报 | ✅ |
| INV-3 | 非终态 per-intent 唯一（x05 部分唯一索引应用层镜像）；red 用例 + 判据直读 | ✅ |
| INV-4 | 口径亲证：`agent_run_service._next_sequence`（:2156）upsert `VALUES 1 … +1 RETURNING`——计数器行值=最近已分配序号，稳态==max_seq 是对的，`<` 才违例；M2 红证 | ✅ |
| INV-5 | ⚠️ **独立判据空洞**：`recallable > total` 算术恒假（三墓碑全空计数必 ≤ 总数），M3 实证复活墓碑后仍 PASS——"无复活"的实质判据全在 INV-7 `episodic_recallable`。交付 notes 如实披露（红证经 INV-7），不算虚报，但**无基线跑 INV-1..6 时该面零防护**（notes §10.4 的灾后流程正好跳过基线——建议 INV-5 补一条真判据如"基线墓碑行集合随包比对"或文档明示） | ⚠️ 登记 |
| INV-6 | 四项孤儿检查；episodic/preferences 侧缺 `IS NOT NULL` 过滤与 agent_runs 侧风格不一，但两列生产 schema 均 nullable=False（`memory.py:22/96`）现网无假阳 | ✅（风格注记） |
| INV-7 | 基线 12 项比对；`test_ghost_rows_red`/`test_tombstone_resurrection_red` + M4 端到端红证；"恢复后有写入转 FAIL"是设计灵敏度非缺陷 | ✅ |

## 6. 交付者实录可信度

- **时间线自洽**：backup manifest 18:53:29Z（duration 5s 与"5-7s"合）→ checker 18:53:40 PASS 12 项 → GJ03 18:56:49 → GJ08 18:57:36。数量自洽：INV-5 total=4/recallable=2/archived=1/retracted=1 在 notes 与两份 checker 产物逐字一致；14 用例计数与文件实况一致。
- **诚实性**：GJ08 4/6 照登 FAIL 明细（bytes/ms/空 text），RPO 如实给 24h 最坏窗，未伪造。
- **缺口（不推翻结论，登记为证据面改进）**：① notes 引用的 `drill/red_restore_head.log`/`green_restore_final.log`（2156 错误 RED 实录、GREEN restore 日志）**未入库**——2156 之数只能静态旁证（251 表 × CREATE/ALTER/COPY/索引/FK 冲突族，量级合理），不可复核；② `.env` 捕获路径未实测（manifest `config_files: []`）；③ notes "INV-4 6 计数器（含 GJ 流量新写）"与在库 checker 产物（3 计数器）、"GJ 后基线复检转 FAIL"均无在库 report 对应——应为一次性宿主上未随包的后续运行。

## 7. 台账对账（重要簿记发现）

- 交付分支 commit `86972fc9` 台账 **+2 行**（FIX-504 backup 三缺陷 RESOLVED + FIX-505 OPEN/PARTIAL）；主干集成 commit `1680d16c` 台账 **只 +1 行（仅 505）**。
- 504 号在主干已被 wt769 的无关行占用（`b0418523`，FIX-258 闭账指针发现，OPEN）——**wt773 的 FIX-504 行在集成时被撞号丢弃，且无任何重编号行（V3-FIX-520 或其他）存在于现库**（`git log -S "FIX-520"` 全历史 0 命中；HEAD grep 0 命中）。协调侧以为的"520（FIXED）"行实际**不存在**——本审查即 FIX-508 所述"行内容于合并丢失"同族第五例（本轮撞号版）。
- FIX-505 行在库且 OPEN ✅，但其范围表述需修正（§8）。

## 8. FIX-505 残差裁定

1. **"prod 容器重建即 Redis 全损"表述过时/过强**：`docker-compose.prod.yml:616-618` 已 `exec redis-stack-server /redis-stack.conf --dir /data`（注释明言覆盖 wrapper 的 /var/lib/redis-stack，"RDB+AOF 落回挂载卷"，OPS-QUIRKS 裁决 2 实测在案）——**prod 形制 dir 错位已被现有 compose 消解**。错位真实存在的面是 **dev `docker-compose.yml`**（裸 `redis-stack-server --requirepass …` 无 `--dir` 无 conf 挂载 → 持久化写未挂载的 /var/lib/redis-stack，重建即失）。ops 卡应按 dev 面裁决。
2. **新残差（本审查发现，建议随 ops 卡同批登记）**：prod `redis.conf` `appendonly yes`（:26）——backup 仅捕 RDB（`redis-cli --rdb`），restore 仅落 `dump.rdb`+restart；AOF 启用的目标在加载期 AOF 优先于 RDB，旧 AOF 重放/新建空 AOF 令 RDB-only restore **在 prod 形制下不可靠**（与 FIX-505 同族"静默无效恢复"）。演练容器未挂 repo conf（AOF off）故 drill 抓不到。修法方向：备份随包 AOF 面（`BGREWRITEAOF`+拷 appendonlydir）或 restore 侧按 `CONFIG GET appendonly` 处置。
3. 裁定：残差**不应阻塞本卡销账**（505 行保持 OPEN 正确），但 §8.2 必须随销账补登进残差清单——它是"备份恢复通路在 prod 形制下不闭合"的实质缺口。

## 9. 销账建议

**APPROVE——V3-FIX-504（脚本面）与 V3-FIX-505（restore 侧）可销账**，前置条件按序：

1. **补登丢失行**：按取号纪律（grep 复核空闲）为 O-05 backup/restore 三缺陷重登一行 `FIXED@1680d16c`（内容可从 `git show 86972fc9 -- v3/06_agent_fleet/DYNAMIC_ISSUES.md` 原行取回），注记撞号丢弃成因（与 504/508 同族）；登记点=集成/主会话。
2. **FIX-505 行注记修正**：残差范围改写为"dev compose dir 错位 + §8.2 AOF-restore 缺口"；"prod 全损"表述纠偏（prod 已 `--dir /data`）。
3. 登记两条小缺陷（不阻塞）：restore bash<4.4 无密码路径空数组崩溃（§4 缺陷 B，一行修）；backup MinIO skip 分支与 checksum 步矛盾（§4 缺陷 A）。
4. GJ08 `*_real_llm` 两步：有 key 环境补跑 `--gj GJ08` 补证（交接已在 notes §10.3）；INV-5 空判据补强与 red/green 日志随下次演练补档为低优先改进。

## 10. 审查自证

- 独立 worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt782-o05rev`（branch `agent/node-b/wt782/o05rev`，**不 push**）；主仓只读未写；零容器。
- 变异 harness：`/tmp/wt782_mutation_test.py`（会话临时件，不入库）；e2e 库 `/tmp/wt782_e2e.sqlite`（用后即弃）。
- 审查者 wt782 未参与 O-05 实现；本 receipt 全部数字为本次独立执行所得或在库文件直读。
