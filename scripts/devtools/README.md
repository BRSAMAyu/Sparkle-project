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
| `rebuild_embedding_index.py` | E-05：embedding 索引重建/版本迁移/回滚（默认 dry-run；`--execute` 真实重嵌并打标 `embedding_model/dim`、重建 Redis 版本化 key；回滚=改回旧 EMBEDDING_* 配置后重跑） |
| `bench_hybrid_retrieval.py` | E-05：hybrid lexical+vector 检索基准（12 chunk 真实语料 × 6 查询，vector/lexical/hybrid 三策略 hit@5/MRR@5/时延；跑完自动清理基准数据） |
| `build_demo.sh` | Demo 版本自动打包（历史演示用途） |
| `demo_start.sh` | Demo 演示启动脚本（历史演示用途） |
| `TEST_INSTRUCTIONS.sh` | 全功能验收测试操作说明（历史） |
