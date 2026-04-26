Lane J 交付简报：已在 chat daily startup hydration 失败时展示“今日加载失败 / 重试”SnackBar，并保证点击重试会再次请求；Demo daily startup 改为读取当前 Demo 计划/下一任务，不再固定“计算机网络/TCP”；comeback 判定改用最近完成任务、最近用户消息与 last_login_at 的最大值，避免用户有真实学习/对话活跃时误判回归；Galaxy 贡献统计失败时显示可重试 banner。

验证：`pytest tests/aurora/test_comeback_context.py`、`flutter test test/features/aurora/data/repositories/aurora_daily_startup_repository_test.dart test/widget/aurora_daily_startup_retry_test.dart` 均通过；定向 `dart analyze` 仅剩既有 info 级提示。
