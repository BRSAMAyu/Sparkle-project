# 机器交接简报 —— 2026-09-30 深夜（换机收尾）

> 本机（brsama MacBook）V4 舰队会话向新机器交接。权威版本=origin/main（本简报随最终推送入库）。

## 一、当前状态快照

- **任务版图**：65 卡 60 闭（原 58 卡 54 闭 + G 系列 7 卡 6 闭）。剩余 5 卡：
  - **V4-U06（在航未闭）**：分支 `agent/v4/u06` 已推远端（9743e329 验收③+42e54cbf 裁决回填已提交；本机 wtU06 另有 1 个未提交文件 `mobile/integration_test/u06_landing_sim_test.dart`——新机重新派发 U06 即可，卡面 tasks.json 仍 NOT_STARTED，scout 材料在 v4/evidence/V4-U06-prep/）
  - V4-Q05 / V4-Q07（heavy，依赖 U06；侦察齐备：V4-Q05-prep/ 7 家族×15 态矩阵、V4-Q07-prep/ 144 行 MVP 切面）
  - V4-Q08（压轴分层裁决；侦察 V4-Q08-prep/ 含 22 项悬置清单+裁决框架提案；**10/3 EOD=降级启动决策点**——Q05/Q07 未闭则带显式 BLOCKED 降级先行，leader 留痕，不许自行豁免依赖）
  - V4-G07（末张 G 卡，等 U06；侦察 V4-G07-prep/ 含 U06 文件锁预案+降级先行域）
- **CI**：CI57 在测（watcher 本机 exec 在跑，换机即失效——新机 `gh run list` 自查）。CI54 双红双修+CI55 全绿+CI56 lint 门修毕的历史全在台账。
- **价值判定基调**：Q01 已闭 value=FAIL 如实记录（L3 真栈 16 步全绿/Hybrid 揭案双缺陷）；Q02 FAIL_L1_BLOCKED_L2_NOT_PASS 已固化——评测 FAIL 可交报告但产品 value 不许标 PASS。

## 二、数据面（本机独有，不入 git）

- **共享 PG 数据在 docker 卷（sparkle_db）**：全量导出已归档 `/Volumes/移动E/sparkle-offload/db_migration_20260930/sparkle_full_20260930.sql`（196M，pg_dump exit 0）。新机恢复：起容器后 `psql -U postgres -d sparkle < dump.sql`。数据属主 compose 在 sparkle-cosmos 仓（FIX-557 铁律）。
- **本机栈残留**：gRPC 50051/FastAPI 8000/Gateway 8080 四进程跑在已删 wtQ01 目录（修前码）——换机即自然消亡，无需处理。Docker daemon 在收尾期间掉过一次已恢复（db 手动 start，三容器 healthy）。
- **外置盘归档目录** `/Volumes/移动E/sparkle-offload/`：V4-Q01 全套（含幽灵线 ghost_lineage 227M）、com.apple.wallpaper 全库、db_migration、FIX-586/582 证据副本。
- **launchd 守卫（com.sparkle.disk-swap-guard，900s）**：本机专属——新机需重建（脚本在仓 scripts/devtools/disk_swap_guard.sh + pg_env_drift_probe.sh 已接线）。

## 三、运营纪律（血泪铸成，新会话必读）

1. **资源双红线**（AGENTS.md 权威）：盘 <15G 主动清、<8G 停重活；flutter test 一律 --concurrency=1；HEAVY=1/宿主机；产物即清；大文件去外置盘。
2. **判活只信返回通知**：transcript mtime/工作树写入都不可靠（本日三次误判实证）；**worktree force 删除=处决令**，删前必须全员死亡证明。
3. **立卡前必台账查重**：grep DYNAMIC_ISSUES 同域关键词（FIX-582 DUP-OF-571 双重失误案）。
4. **测试路径必须实查**（find/git show --name-only）：幻影路径六犯，每次都烧时间。
5. **多 heredoc 脚本路径变量不复用**；写台账前 json.load 校验是 MD（覆写事故案）；`&&` 串联门禁不许 `;` 滑步提交。
6. **中文文档 python heredoc 禁 printf**；tail 吞 exit 用重定向+echo EXIT。
7. **验收模型**：自称完成不算完成=独立未参与会话审查+合并态可失败测试；高风险双审；审查员不信任实现者第二手证据（亲跑/亲杀 mutation）。
8. **跨卡合并**：改共享屏面必须跑相邻家族测试（CI54 G05×G03 旧钉案）；cherry-pick continue 前 grep 冲突标记。
9. **CI push-lock**：起跑至裁决零 push；红=真测试门修/风格门棘轮分诊，backend 分片 skip 看级联。
10. **组员线**：slsjz 在 sparkle-cosmos 跑 RF-06（其工作树/进程只读）；动 mobile 前盘点其未合并改动。

## 四、悬置决策与待办

- **10/3 EOD**：Q08 降级启动决策点（预付裁决条款已入台账 note 34:30 段）。
- **栈重启复测窗**（原挂 U06 后，换机后=新机起栈自然达成）：F583 C1 终裁（Q01 Hybrid 复测）+ FIX-582 R-4 驻留进程解 + Q01 driver 绕行回正（FIX-587 评估过可回正，需三轮定稳）。
- **O-01 AK 轮转**：用户已授权 leader 裁决=推迟 10/7 后标准三步（新建→迁移→停用）。
- **FIX-585 B 型遗留**、FIX-586 C1-C5 改进面、KNOWN_CODE_DEBT_LEDGER 2026-09-30 节——全部登记态，非阻塞。
- 停止条件=Q08 分层结论或全部可执行卡结束且余项真实阻塞。

## 五、权威指针

- 规格权威：v4/04_tasks/tasks.json（65 卡全字段）
- 运行台账：v3/.sparkle_v3_fleet_state.json（notes 530+ 条，只追加）+ v3/06_agent_fleet/DYNAMIC_ISSUES.md（FIX 台账 586+ 行）
- 证据：v4/evidence/（每卡五件套制）
- 接力：docs/competition/2026-tmall-hackathon/接力日志.md（cosmos 仓）
- 节奏：10/4 内部交付、10/7 官方截止
