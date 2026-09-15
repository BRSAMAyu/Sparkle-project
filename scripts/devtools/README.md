# scripts/devtools/ — 一次性与维护脚本

> 从仓库根目录收纳的开发/调试/演示脚本（2026-09-08 整理轮）。**无 CI 引用、不保证可维护**——使用前自行检查可用性；新的一次性脚本也放这里，不要散落仓库根目录（见 `docs/engineering/REPOSITORY_STANDARDS.md`）。

| 脚本 | 用途 |
|---|---|
| `setup_env.sh` | 一键安装本地开发环境依赖（支持 `--skip-flutter`） |
| `start_celery.sh` | 快速拉起 Celery 服务组（worker/beat/flower） |
| `create_test_user.py` | 创建测试用户（真机联调用，见 `backend/docs/REAL_DEVICE_INTEGRATION_TEST.md`） |
| `check_settings.py` | 检查 backend 配置项完整性 |
| `force_sync_db.py` | 强制全量同步数据库（导入所有模型后重建 schema，谨慎使用） |
| `test_job_service.py` | 手动验证任务服务 |
| `test_llm_parser.py` | 手动验证 LLM 解析器 |
| `build_demo.sh` | Demo 版本自动打包（历史演示用途） |
| `demo_start.sh` | Demo 演示启动脚本（历史演示用途） |
| `TEST_INSTRUCTIONS.sh` | 全功能验收测试操作说明（历史） |
