# FIX-583 audit —— 红线与纪律自查

| 红线 | 执行情况 |
|---|---|
| 不 push | 未 push；改动仅在本 worktree 分支 `agent/v4/f583` 提交 |
| 不删断言不弱化语义 | `test_j06_hybrid_journey.py` 仅 +3 行（fixture 补 `AsyncSessionLocal` 指向测试引擎——修后 prep 走 executor owned-session 路径，测试引擎必须同指向；断言零删改）；wt392 零改动；语义弱化无 |
| 行为修复须带可失败测试 | 3 条新回归钉 + mutation A/B/C 三变异全被杀（还原后复绿）——双向验证 |
| 每命令记 exit code | 全程记录（见 run_manifest.json commands；pytest 以重定向 + `echo EXIT=$?` 捕获真实退出码） |
| 中文文档 python heredoc 禁 printf | 证据文件用 Write 工具落盘，未用 printf 写中文 |
| tail 吞 exit 用重定向+echo EXIT=$? | pytest 全部 `> /tmp/…log 2>&1; echo EXIT=$?` 口径 |
| 磁盘 | 本机磁盘充足（未触发 <15G 清缓存线） |
| 勿动运行中的 Q01 栈 | 未触碰 gRPC 50051/8000/8080 任何进程；未起容器；proto 生成走 host 工具链（`PROTO_USE_DOCKER=0`，避免 docker 面接触） |
| pytest 环境 | `/opt/homebrew/opt/python@3.11/bin/python3.11 -m pytest` + `DATABASE_URL=sqlite:// SECRET_KEY=x` 覆盖 |
| 会话产物不入库 | 证据仅此五件套入 `v4/evidence/FIX-583/`；pytest 输出留 /tmp |

## footprint

- `backend/app/services/hybrid_journey_service.py`：+96/-12（全部落在修复面：
  imports/常量/补偿函数/僵尸判定/start_hybrid_journey 主体；diff hunk 逐个核过，
  无无关重排）
- `backend/tests/unit/test_j06_hybrid_journey.py`：+3（fixture）
- `backend/tests/unit/test_fix583_hybrid_start_hang.py`：新增（3 测试）
- `v4/evidence/FIX-583/`：五件套（run_manifest.json / verification.md /
  limitations.md / summary.md / audit.md）
- 台账 `v3/06_agent_fleet/DYNAMIC_ISSUES.md`：FIX-583 行追加状态（python 追加）

## 基线事实

- base：`3528623a`（main HEAD，工作树起点干净）
- Q01 被测版本 `5cbc715f` 为 base 祖先且两核心文件其间零改动——代码读面即
  缺陷本体（`git merge-base --is-ancestor` 实证）
