# V4-P03 二审 receipt（独立审查 wtP03R2）

> 2026-09-29 · 审查会话未参与 P03 实现与一审 · 分支 `agent/v4/p03` · 被审对象：feat `f14937de` + 证据 `ac5097b7` + R-1/R-2 修复 `3e2ae2d3` + 一审 receipt `8dcf1148`（可读不采信，独立下判）
> 方法：只读审查 + 独立对抗构造（合成时钟状态机演练 / 真实二进制敌意环境 / mock docker 干跑 / 静态写路径核查）+ 全量复跑。未真跑 up.sh、未动真实栈。

## 总裁决：PASS_WITH_CHALLENGES

卡验收三条二审独立复证维持成立（失联可检 / CWD 不决定资源路径 / 恢复·迁移·主题·selector 各有可执行证据）。一审 R-1 修复核实证成立；一审 R-2 **修复无效**（新挑战 **R2-1**：.gitignore 行内注释不构成注释，`artifacts/ops/` 实际未被忽略）；新挑战 **R2-2**：新测分母三处书面 26、实测收集 24（7+10+7，一审 receipt 中「7+10+7=26」系算术错误）。两者均为证据/防呆质量面，不改变 24/24 全绿与验收结论。C-4 残缺口归属裁决：**独立 ops 卡（首选）**。高风险卡双审至此齐，建议销账以 R2-1 一行修复落账为条件。

## 1. R-1/R-2 修复核（3e2ae2d3）

### R-1 up.sh 步骤4 容器名修正 —— 核实成立

`bash -n` 通过。ground truth：`docker-compose.yml:67 container_name: sparkle_redis`，修正确为真名。本地未真跑 up.sh（不动真实栈），以 mock docker（`/tmp/p03r2_mock`，假 `docker` 响应 inspect/exec/volume，真实栈零接触）干跑 5 场景：

| 场景 | 结果 | 判 |
|---|---|---|
| A 快乐路径（真卷属主+redis 活） | exit 0，步骤1-9 全执行，**步骤4 秒过**，AGE/索引/迁移按设计降级为非致命 WARNING，"Infrastructure UP." | 步骤4 恒死已解，步骤5-8 可达 |
| B redis 连续 15 败 | exit 1，`FATAL: Redis not ready after 15s.` | fail-closed 保持 |
| C FIX-557（容器灭失+真卷存在，无越权开关） | exit 1，指向 RESTACK_RUNBOOK | 预检不受本修复影响 |
| D 基线 `4a5dc5f2` 版 up.sh 同 mock | exit 1（基线死于更早步骤） | 红 |
| E 同 C + `SPARKLE_ALLOW_RESTACK=1` | exit 0，WARNING 后放行 | 越权门行为保持 |

边界逻辑亲核：`i=15` 时 `break` 先于 `die`（恰好第 15 次就绪不误杀）；`docker exec` 位于 `if` 条件位，`set -e` 不误触发；冷却判据同构正确。

### R-2 `.gitignore` artifacts/ops/ —— **修复无效（R2-1）**

`git check-ignore -v artifacts/ops/probe_r2.jsonl` **exit 1（未忽略）**；`git status` 出现 `?? artifacts/`。根因：gitignore 的 `#` 仅在**行首**才是注释，`artifacts/ops/  # P03-R2：…` 整行被当作字面 pattern（只匹配名为 `artifacts/ops/  # P03-R2：…` 的路径），防呆目的完全未达成。修法：注释移到上一行，`artifacts/ops/` 单独成行。R-1 的 diff/message 未宣称验证 ignore 生效，但「会话产物永不入库」的防呆缺口实际仍开着——本审查已在监督器测试全绿路径下确认 `artifacts/ops/` 不被产生（测试 monkeypatch 到 tmp），故无现实污染，仅防未来真实守护运行。

## 2. supervisor 对抗面（审查亲跑，非复用实现/一审判据）

以 /tmp 独立脚本直接驱动 `supervisor_probe.py` 真实现（合成时钟 + 真实 localhost socket），v1 13 检查 + v2 修正预测 5 检查：

- **a) 闪断（3 连败边缘抖动）**：fail,fail,green 抖动 ×20 周期 → 零重启（threshold=3 是防抖语义，自愈型闪断不重启为正确策略）；抖动后真 3 连败**恰在第 3 次**触发 restart，重启后计数复位（第 4 次失败重新计 1）。计数纪律一致。
- **b) 冷却 × 小时上限交叠**：永久死服务（30s 探测、threshold=3、cooldown=90、cap=3）→ restart@t=60/150/240（冷却节奏，`now-last==90` 恰好放行），第 4 次阈值命中转 `alert`@t=330，此后零 restart。**一小时内恢复再死仍被 cap 压制**（`restart_timestamps` 滚动窗口语义——保守但正确：cap 按滚动小时计，不因中间恢复豁免）。
- **c) 超时 vs 连接拒绝区分度**：TCP refused → detail `ConnectionRefusedError: [Errno 61] Connection refused`；HTTP timeout → `TimeoutError: timed out`；HTTP refused → `URLError: <… Connection refused>`——**观察层可区分（detail 文本），决策层同红**。判：对重启策略这是正确设计（hung 与 dead 都该重启），且补测出 `accept-nothing listener` 下 TCP 探针绿（backlog 握手完成）而 HTTP 探针红——health/ready 分离恰好覆盖该盲区。注意 refused/timeout 的映射随环境可变（本沙盒对同进程 bound-not-listen 连接得 TimeoutError），但只影响 detail 文本不影响判红。

非阻断小疵三条（登记，不要求本卡改）：**O-1** `alerted_cap` 是死字段（声明+green 复位、从不置 True 也不被读）——cap 告警每周期重发；其自有测试 `test_restart_cap_alerts_instead_of_looping` 断言 `actions[3]=="alert"` 已将该行为固化为事实设计，建议后续二选一（接线去重或删字段）。**O-2** `run_one_cycle` 重启执行 `subprocess.run(timeout=60)` 的 `TimeoutExpired` 未捕获——默认三条 restart_cmd 均 `&` 后台化故实际风险低，但自定义 config 前台长命令会击穿监督循环。**O-3** blackout 用 `"HH:MM"` 字串比较，跨午夜窗口（如 23:50-00:10）恒不匹配且无告警。

测试质量小疵两条：`test_supervisor_probe.py:125` 断言含恒真子句（`... or result.detail`），该断言实际不可失败；`test_full_recovery_restart_cycle` 每次运行经 `nohup … &` 重生的 decoy 不在 fixture 清单内，**每次泄漏 1 只孤儿进程**——现存 3 只（impl 会话×2：PID 12029/13844；R1 会话×1：PID 31816；本审查 1 只已自清）。建议 owners 顺手 kill，属主会话在测时补 fixture 清理。

## 3. i18n 四级链对抗（真实二进制 6 场景亲跑）

自建 `wtP03` 二进制（DB-fatal 探针设计：`POSTGRES_PORT=1` 即拒退出，不绑端口不触栈），敌意环境逐一：

| 场景 | 结果 | 判 |
|---|---|---|
| env 指向不存在路径（+敌意 CWD） | WARN `Failed to resolve locales dir` + `is not a valid locales dir (missing [en.json zh.json])` + diagnostics | fail-loud 成立 |
| CWD 深层嵌套 12 级（超 walk-up 上限 8） | source-anchored 绿 | CWD 不决定 |
| CWD 被删除（Getwd 必败） | source-anchored 绿 | CWD 丢失鲁棒 |
| symlink→真 locales 目录（经 env） | env override 绿 | symlink 目录可采纳（Stat 跟随） |
| symlink 自环（ELOOP） | Stat 败→无效→显式 WARN，无悬挂 | fail-loud |
| 经 symlink 路径进入的 CWD | source-anchored 绿 | 物理路径不敏感 |

语义精确化（与措辞差异，如实登记）：四级链的 fail-loud 是 **log 级**（zap WARN + fallback 默认 bundle、进程续行），非进程级 abort——与 main.go:43-53 实现及 i18n 非关键资源定位一致，一审「不静默」判断成立；运维监控若只盯 ERROR 级会漏 WARN，此为部署面注意事项非缺陷。

## 4. gate binding 完整性（三门只读静态核查）

- **v3/ 树全分支零触碰**：`git diff 4a5dc5f2..3e2ae2d3 -- v3/` 为空。
- **三门现值**：亲读 `v3/07_tasks/tasks.json`，O-01/Q-07/Q-08 status 均 `TODO`——与绑定 `original_status` 逐字一致。
- **写路径穷尽**：`external_gate_binding.json` 全仓 grep 消费者仅 3 个证据文档（diff_or_evidence_only/run_manifest/review_receipt）——**零代码消费者、零读写路径**；scripts/v4/backend 无任何自动化写 `v3/07_tasks/tasks.json` 的工具（backend 中 grep 命中均为文档注释）。「V4 侧状态变化试图翻转门」结构上无自动化向量：唯一翻转途径是人/会话直接编辑 v3 tasks.json，不在 V4 工具面内。
- 绑定内容：`does_not_replace_authorization=true` ×3；`candidate_readiness_snapshot` 记 V4 候选面（READY_INTERNAL / BLOCKED_EXTERNAL / NOT_RUN_BY_DESIGN ×2）非门状态；证据 commit 对 `v4/04_tasks/tasks.json` 的触碰仅 P03 自身条目（PENDING→in_progress/REVIEW_READY）。C-6 无泄漏结论二审加固成立。

## 5. C-4 残缺口归属裁决（一审留给属主，独立建议）

残缺口实质：FIX-557 真实事故形态（从 Sparkle-project 仓发起重建）在本仓 up.sh 结构上不可拦截；台账长期修法「两仓 compose 容器名分化」仍 OPEN。

**独立建议：独立 ops 卡（首选），不进 Q07，不停留于现状登记。**

- 形态：小卡、单会话、可失败（compose `container_name` 改本仓唯一前缀如 `sparkle_cosmos_db`；volume 名本就按 compose project 前缀分化，**无需数据迁移**）；同卡顺带闭合 C-4(b)（sparkle_redis/sparkle_minio 属主预检扩展）、RESTACK_RUNBOOK 跨仓注记、smoke.sh:34 / logs.sh 同族错名（`sparkle-redis`，初始 commit 既有债、P03 未宣称修复该两文件）一并收口。单侧分化后，错误仓重建与本仓数据面结构性无碰撞，事故形态被根除而非被拦截。
- **不进 Q07 的理由**：Q07 是 HEAVY 混沌**验证**卡，承载实现会把修 bug 混进终验、延迟一个 HEAVY 周期；正确关系是 Q07 消费该 ops 卡成果（「错仓重建无碰撞」作为混沌负例纳入演练）。
- **不停留于现状登记的理由**：事故 09-28 已实战发生一次（真数据卷险些被空卷顶替），RUNBOOK+预检属「拦到事故前后」而非「根除」，复发概率真实。
- 回退：若编队容量不足，至少在 FIX-557 台账长期修法项显式指派属主会话并保持 OPEN 显眼，避免与已 FIXED 的 runbook 短修混淆。

## 6. 复跑（审查亲跑，2026-09-29）

| 面 | 结果 | 判 |
|---|---|---|
| Go i18n `go test ./internal/i18n/ -count=1`（收集数 `grep -c "=== RUN"`） | **7**/7 PASS | ✅ |
| pytest probe+supervisor（venv pytest，`--collect-only` 计数 10+7） | **17**/17 PASS（2.96s） | ✅ |
| **新测分母** | 实测 7+10+7=**24**，与书面 26 不符 | ⚠ R2-2 |
| 迁移契约门 `BASE_REF=4a5dc5f2` | exit 0，No changed migration files | ✅ |
| selector `test_semantic_selector.py`（throwaway SECRET_KEY） | **77**/77 PASS | ✅ |
| gofmt -l / go vet ./... | 零输出 / exit 0 | ✅ |
| ruff（4 新 py 文件）/ mypy（2 ops 模块） | 全绿 | ✅ |
| black --check 120（black 26.3.1） | 4 新文件 + **33 个既有文件**同判 would-reformat | 注记 |

black 注记：新文件循仓库既有 black canon（旧版风格的参数换行）；black 26.3.1 对 33 个 P03 未触碰的既有脚本同样要求重排（含 base 版 `check_migration_contracts.py`）——属仓库级 black 版本工件，**P03 零新增漂移**，「black 全绿」仅在旧 canon 语义下成立。非挑战，登记为工具链事实。

## 7. limitations 8 条与一审 C-1..C-6 定性复核

**limitations 逐条核**：1（真实栈无破坏性演练，decoy 等价+归属 Q07）✓；2（readyz 503 既有态，归网关属主）✓ 与一审 C-3 互证；3（redis 仅 liveness，无凭据不引入）✓ 代码 `service_supervisor.py:164-176` 核实；4（无 launchd/supervisord 常驻）✓ 代码仅 --once/--observe；5（修法③只显性化，未改网关退出语义）✓ diff 无 handler/退出面改动；6（worktree 生成物手动移入）✓ 过程事实；7（black 风格差异）✓ 与 §6 注记互证；8（主题/selector delta=0 复跑举证）✓ diff 零触达两域。**8 条全部如实，无漏报。**

**C-1..C-6 定性复核**：C-1（decoy 等价性，restart 真实命令串归 Q07）维持——本审 §2 证明状态机/探测面对 decoy 与真实进程同代码路径，且 §3 真实二进制补了 CWD 面；C-2（红绿对照控制）维持；C-3（readyz 503 既有态）维持——三容器现 Up 10h 健康在跑，时间线自洽；C-4（预检穷尽性部分覆盖）维持，残缺口归属见 §5 独立裁决；C-5（NOAUTH liveness 语义）维持——`"AUTH" in detail` 宽匹配一审指出的小疵仍在（line 170），定性不变（不要求改判据）；C-6（绑定无泄漏）维持并经 §4 静态写路径核查加固。

## 8. 新发现汇总

- **R2-1【CHALLENGED·销账条件】R-2 修复无效**：.gitignore 行内注释不生效，`artifacts/ops/` 实未被忽略（§1 实证）。一行修复，建议随本 receipt 或紧随 commit 落账。
- **R2-2【低·登记更正】新测分母 26≠24**：`test_results.json` summary、feat commit message、一审 receipt（「7+10+7=26」算术误）三处书 26；实测收集 24，24/24 全绿为真。不改变验收，但违反「计数为实测收集数」纪律，建议在 test_results.json 加一行更正注记（26→24）。
- **O-1..O-5 非阻断观察**：alerted_cap 死字段/告警重发；TimeoutExpired 未捕获；跨午夜 blackout 恒不匹配；probe 测试断言恒真子句 + decoy 泄漏（现存孤儿 PID 12029/13844/31816 归 impl/R1 会话，建议顺手清理）；smoke.sh/logs.sh 同族容器名漂移（归 §5 ops 卡顺带收口）。

## 红线自检（审查首尾）

- 真实栈零接触：up.sh 未真跑（mock docker 干跑）；二进制探针 POSTGRES_PORT=1 即拒退出、不绑端口；docker inspect 仅只读（pytest 预检真实 inspect 属只读）；三容器审查全程 Up 10h (healthy) 零重启。
- 零凭据/零 TCC/零云调用；JWT_SECRET/SECRET_KEY 为 throwaway；未读任何 .env 密钥值。
- 监督器执行面零触发：审查全部状态机演练为纯函数驱动（合成时钟）；`--observe`/decoy 面未对真实进程执行重启；本审查 decoy 已自清。
- worktree 干净：审查产物全部在 /tmp；`git status` 零残留；artifacts/ops 全程未产生。

—— wtP03R2（未参与 P03 实现与一审）· 2026-09-29
