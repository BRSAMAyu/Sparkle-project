## Lane D Handoff

已新增 `STUCK` 任务状态、migration、`POST /tasks/{id}/stuck`、`task.stuck`/SRL 事件。接口会携带任务标题、最近步骤和计时器秒数调用 Aurora runtime，生成并持久化 `stuck_help`。移动端“卡住了”先取实时诊断再渲染 sheet；“和 Sparkle 聊聊”改为 push chat，携带 `task_state.stage=stuck`，任务执行页留在栈内。

验证：2 个后端定向 pytest、`flutter test test/widget/task/test_task_execution_ux.dart`、定向 `dart analyze` 通过；全量 `flutter analyze` 仍被既有 third_party errors 阻断。
