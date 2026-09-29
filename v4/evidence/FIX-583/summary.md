# FIX-583 summary —— hybrid start 系统性挂死修复（P1，DONE 待独立审查）

## 缺陷（Q01 真端 3/3 复现）

`POST /api/v1/journey/hybrid` 100% 超网关 30s 503；run 永久 `RUNNING/prep`；
僵尸事务（`idle in transaction`）持该用户 `agent_runs` 行锁把重试钉死——
一次挂死永久钉死该用户的 Hybrid。

## 定性（详见 verification.md §1）

- **挂点**：prep 工具成功返回后、`complete_agent_step` 提交前——DB 快照钉死
  （run updated_at 冻结在 RUNNING 迁移 +18ms；`agent_tool_calls`/`hybrid_artifacts`
  零落库 = 推进窗口的写从未提交；prep 本体 3.8-4.3s 真实成功）。
- **形态**：重活 + 开放请求事务 + 行锁绑定在请求生命周期上；应用侧在持锁时
  await 无超时操作（`idle in transaction` 证明非 DB 锁互等）。
- **预定位两候选裁决**：外层未提交事务持锁=成立；工具账本写互等=不成立
  （账本键按 run 派生，无同键互等路径）。

## 修法（三件套，`hybrid_journey_service.start_hybrid_journey`）

1. **重活出请求事务**：run 创建 + RUNNING 迁移提交后显式收口请求事务；
   prep 检索走 executor owned-session（`db_session=None`）。
2. **显式超时 + 补偿**：`wait_for(PREP_TOOL_TIMEOUT_SECONDS=20s)`（< 网关 30s）；
   超时 → wt392 F1 FAILED 补偿（`prep_timeout`）→ 可重试失败。
3. **僵尸启动自检回收**：resolve 命中超龄（15min）`RUNNING/prep` 僵尸 →
   FAILED（`prep_zombie_reclaimed`）→ 开新 attempt；新鲜活跃 run 仍幂等回放。

## 回归与 mutation

- 既有全绿：j06 + wt392 + migration + hybrid_run_steps 家族 40 passed；
  终态 23 passed。零断言删除/弱化（test_j06 仅 +3 行 fixture 对齐）。
- 新增 3 条可失败回归钉（`test_fix583_hybrid_start_hang.py`）：超时不钉请求
  会话 + 僵尸不钉重试 + 新鲜 run 不被误回收。
- MUT-A/B/C 三变异全被杀，还原后复绿；ruff 全绿。

## 遗留（limitations.md）

挂死 await 的行级定位未决（末语句与调用树不匹配，需真端 py-spy）；真端复测由
Q01R1 在保持运行的栈上裁决。judgment 段核查无同构暴露（其 LLM 本就 12s 超时、
无工具执行），无下一卡需要。
