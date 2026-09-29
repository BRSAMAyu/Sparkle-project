# FIX-586 — FIX-582 诊断残余面热修（R-1/R-2/R-5）

- 执行：FIX-586 fleet 修复 agent（worktree `wtF586`，分支 `agent/v4/f586`）
- 时刻：2026-09-29 12:31–12:5x UTC（DB 时钟 Etc/UTC 实测；本机 +0800 20:3x–20:5x）
- 依据：`v4/evidence/FIX-582/diagnosis.md` §4 R-1/R-2/R-5 + leader 裁决（台账 FIX-582 行，2026-09-30）
- 纪律：凭据全指纹化零回显零落盘（防泄检查 PASS）；运行栈写面=R-1 role 面 surgeries（先查证后执行，偏差披露见 R1 报告 §2）；零 restart；F583 僵尸事务/run/驻留栈零触碰（终扫 idle_in_txn=7 为其自然演进，未干预）

## 三件交付

| 项 | 交付 | 结果 |
|---|---|---|
| R-1 孤儿 role 清理（方案 A） | [R1_report.md](./R1_report.md) + SQL 全文 [R1_roles_fix.sql](./R1_roles_fix.sql) + raw/ 前后快照/门禁/执行回执/鉴权探针 | 三 NULL 密码 role（engine/celery/readonly）零活跃连接+零对象归属查证后 DROP（全簇 ACL 4634→0）；sparkle_gateway 孤儿密码对齐 gateway/.env 现行凭据（`5faa8c266d2a`→`3ab7ba2145b1`，宿主侧 scram AUTH_OK）；c17 GRANT 面 288 条保留；c17 最小权限债登记 docs/engineering/KNOWN_CODE_DEBT_LEDGER.md 2026-09-30 节 |
| R-2 漂移探针 | [R2_report.md](./R2_report.md) + 脚本 scripts/devtools/pg_env_drift_probe.sh + raw/R2_probe_run.txt | 探针落地（全指纹化零明文，V1/V2/V3 三判定）+ disk_swap_guard.sh 尾部接入（launchd 900s 例行，live 副本原子同步）+ 本机实跑全一致（V1:PASS V2:PASS(4源) V3:PASS，exit=0）+ DRIFT 分支 /tmp 注入证伪（exit=1）+ 守卫端到端日志验证 |
| R-5 Q04 limitations 回注 | [R5_diff.txt](./R5_diff.txt) | §2 末尾 python heredoc 只追加一行勘误注记（三联经 FIX-571@6110b6a5 修复+FIX-582 复测成立），diff 2 插入 0 删除，正文零改动 |

## 台账与关联

- 台账 `v3/06_agent_fleet/DYNAMIC_ISSUES.md` FIX-586 行：状态追加「实现完成待独立审查」（写前 fleet state `v3/.sparkle_v3_fleet_state.json` json.load 校验通过；python 追加仅该行变化，numstat 1/1）
- live 栈终态复核（12:4xZ）：容器 Up 5h healthy 零 restart；pg_authid sparkle_% 仅剩 sparkle_gateway；token_usage 1471 行未动；连接面 postgres 48+后台 4
- Sparkle-project 侧两文件（pg_env_drift_probe.sh 新增 / disk_swap_guard.sh 更新）为 live 运行副本同步，**不在本分支提交范围**（卡片授权单分支 agent/v4/f586），其 repo 工作区留 M/+?? 状态待其属主处置
