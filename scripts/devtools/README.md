# scripts/devtools/ — 一次性与维护脚本

> 从仓库根目录收纳的开发/调试/演示脚本（2026-09-08 整理轮）。**无 CI 引用、不保证可维护**——使用前自行检查可用性；新的一次性脚本也放这里，不要散落仓库根目录（见 `docs/engineering/REPOSITORY_STANDARDS.md`）。

| 脚本 | 用途 |
|---|---|
| `setup_env.sh` | 一键安装本地开发环境依赖（支持 `--skip-flutter`） |
| `start_celery.sh` | 快速拉起 Celery 服务组（worker/beat/flower） |
| `create_test_user.py` | 创建测试用户（真机联调用，见 `backend/docs/REAL_DEVICE_INTEGRATION_TEST.md`） |
| `check_settings.py` | 检查 backend 配置项完整性 |
| `force_sync_db.py` | 强制全量同步数据库（导入所有模型后重建 schema，谨慎使用） |
| `orm_migration_audit.py` | ORM ↔ Alembic 迁移链 ↔ 实库 三方列集审计（scratch 库真重放迁移链；exit 非零=白名单外漂移；见 round2 schema-consistency-audit 报告） |
| `db_debris_cleanup.py` | dev 库 schema 碎片清理（29 张会话遗留表 + tasks 三列 db-only 残留；默认 dry-run，`--apply` 实删；演练验证与 runbook 见 `docs/engineering/DB_DEBRIS_CLEANUP.md`） |
| `test_job_service.py` | 手动验证任务服务 |
| `test_llm_parser.py` | 手动验证 LLM 解析器 |
| `ledger_union_merge.py` | 舰队台账 union-merge 固化（V3-FIX-268，吞行 ≥4 次事故根修）：`v3/06_agent_fleet/DYNAMIC_ISSUES.md` 冲突按 V3-FIX-N 分轨并集——表格行取状态更进化者（OPEN<FIXED@/CLOSED@/WONTFIX，同状态才比长度，非纯长度启发）、非表格行按出现序零丢失；`--renumber OLD=NEW` 可重复（theirs 侧整行重编号+自动注记）；`--check` 零标记残留+双侧 ID 全在场吞行检测。`pytest scripts/devtools/test_ledger_union_merge.py` |
| `test_ledger_union_merge.py` | 上者 pytest 套件（15 测：246/247 吞行事故复现/OPEN→FIXED 进化非纯长度/非表格零丢失/renumber/check 检测+CLI 端到端） |
| `rebuild_embedding_index.py` | E-05：embedding 索引重建/版本迁移/回滚（默认 dry-run；`--execute` 真实重嵌并打标 `embedding_model/dim`、重建 Redis 版本化 key；回滚=改回旧 EMBEDDING_* 配置后重跑） |
| `bench_hybrid_retrieval.py` | E-05：hybrid lexical+vector 检索基准（12 chunk 真实语料 × 6 查询，vector/lexical/hybrid 三策略 hit@5/MRR@5/时延；跑完自动清理基准数据） |
| `c03_pipeline_perf_profile.py` | C-03：context 硬过滤→rerank 管道延迟剖面（合成 memory+knowledge 候选 × 规模轴；纯函数滤芯 + 合成向量 rerank，真实 LLM/embedding 0 次；`--scales` 可调） |
| `trace_timeline.py` | O-02：按 trace_id 从引擎日志还原全链时间线（TRACE_SPINE span/latency/context funnel/entry-exit 锚点聚合；actual model/cost/causal receipt 关联；只读、正文零输出） |
| `x02_run_allocation_eval.py` | X-02：allocation 盲评报告生成器（规则层独跑 60+ 场景 → `v3-output/X-02/EVAL_RESULTS.md`；不触 DB、零 LLM） |
| `x10_run_action_e2e_eval.py` | X-10：Action Engine E2E 无人值守评测（77 场景真实服务层+真实 DB，六元组+独立判定 → `v3-output/X-10/`；acceptance 不绿 exit≠0；零 LLM/零模拟器/零 gradle） |
| `p15_outcome_absorption_probe.py` | P1-5：星图 mastery 生长链活栈探针（真实库重构 outcome.recorded payload 过修复版吸收器，before/after mastery + 幂等复跑；用法见脚本 docstring；报告见 `v3-output/P1-5-MASTERY/REPORT.md`） |
| `audit_community_readmodel.py` | S-01 段一：Community 读模真相审计（每投影一行：来源/新鲜度/一致性风险/live 可测性 + grep 锚点复核；`--live` 追加只读探测，失败如实记录不合成假 realtime；默认零 PG 连接；报告见 `v3-output/WT361-S01-READMODEL/REPORT.md`） |
| `bench_ai_stack_l0_l3.py` | E-08：AI Stack 集成 Bench（L0-L3 四层 × 104 真实 query 经 gRPC StreamChat 真模型真路由；TTFT/total/token/cost/context/stage/fallback/quality 全字段 → `v3-output/WT372-E08-BENCH/`；`run`/`summarize` 子命令可断点续跑；DB 归因经 `docker exec sparkle_db psql`；需常驻引擎 :50051/:8000 与主仓 backend/.venv） |
| `q06_perf_bench.py` | Q-06/wt406：分层性能/成本终验（每层 50 distinct×2 reps=100 真样本，pro 车道走 `user_profile.is_pro=true` 网关忠实形态；p50/p95 仅 n≥100 报告；复用 E-08 语料+价表保可比 → `v3-output/WT406-Q06-PERF/raw-bench.jsonl`；需 wt406 worktree 引擎 :50061 + redis db1 billing worker） |
| `q06_growth_scaling.py` | Q-06/wt406：Context token × Memory 增长标度（ContextPackBuilder 真服务面，episodic 10/50/100/500/1000 行 + preference 版本链轴，幂律拟合指数判超线性；sqlite 隔离 + fakeredis，LLM judge 0 次、仅真实 embedding batch） |
| `q06_provider_chaos.py` | Q-06/wt406：供应商波动注入（mock OpenAI 兼容上游 :9099 + `serve`/`run` 子命令；429/慢 TTFT/断流/队列压力/全断供七场景，用户可见面+引擎 fallback/熔断日志+上游尝试链三面观测 → `chaos_results.jsonl`；注入点=env base_url 重定向，产品代码零改动；配套 `q06_chaos_engine.sh` 管理 chaos 引擎 :50062） |
| `q06_chaos_engine.sh` | wt406：chaos 引擎启停（:50062 + redis db2 + 上游三 base_url→mock 的 .env 段落式覆盖/恢复；stop 按端口精确杀，不触常驻 :50051） |
| `q06_smoke_tier.py` | wt406：tier 分层 smoke 探针（free/deep/pro/提权封堵四形态 → :50061；非交付物，报告引用输出） |
| `build_demo.sh` | Demo 版本自动打包（历史演示用途） |
| `demo_start.sh` | Demo 演示启动脚本（历史演示用途） |
| `TEST_INSTRUCTIONS.sh` | 全功能验收测试操作说明（历史） |
