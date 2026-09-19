# P1-A 任务完成端点必 500 修复（galaxy outbox）

> 基线 6b5cb301，基线复核真实 PG16。每日流 R2 定位（daily-flow-eval-r2.md）。

## 三层根因（逐层实证）
1. `stats_service._write_spark_outbox_event` 在 `sa_text()` 写 `:payload::jsonb`：SQLAlchemy 两遍正则行为不一致（TextClause 注册假绑定参数 `payloa`；asyncpg 编译器裸 `:` 直送 PG → PostgresSyntaxError）。
2. 异常被吞成 WARNING 但事务已 aborted → `task_service.py:695` 的 group_task_claims SELECT 踩 InFailedSqlTransactionError → 500（数据已 commit，故"库里有、端点报错"）。
3. 只修 cast 是假修复：`event_outbox.aggregate_type` NOT NULL 无默认值（修完语法照样 NotNullViolation）；`sequence_number` 恒 1，网关投影器游标消费（builder.go:247 `>$2`）第 2 条起永不投递。

## 修复
对齐生产已验证的 `GalaxyService._write_mastery_outbox_event` 管线：SQL 提为模块级常量（可单测），counters upsert 取单调序号 + 全列无 cast 纯命名参数 INSERT。

## 红绿与回归
- `tests/api/test_task_complete_galaxy_outbox.py` 4 例（方言编译干净/NOT NULL/端点 200+落库/二次完成序号 1→2）：修前 4/4 红 → 修后 4/4 绿。
- 一次性 PG16 容器复现：旧 SQL 逐字 PostgresSyntaxError + 同事务 SELECT 中止；新链路 jsonb 落库、序号递增。
- 全仓 ~1050 处 `text()` 混用扫描：0 残留（age_client 走原生 fetch 不经 SQLAlchemy）。
- 邻域 57 passed（galaxy/complete/DF-5 耦合/task_service）。

（注：原报告随 worktree 误删，本文档由主会话据修复员结论重建；patch 内容以 git 提交为准。）
