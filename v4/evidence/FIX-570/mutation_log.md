# FIX-570 mutation 自验记录（可证伪性亲证）

两次 mutation 均已还原（`git checkout --`），工作树仅余新增测试文件。每步 exit code 为 flutter test 进程真实退出码。

## M1 · ① 删 gate 调用（还原 U14 前直连接线）

- **mutation 内容**：`mobile/lib/features/task/task_routes.dart` 执行路由 pageBuilder 的
  `TaskExecutionDeepLinkGate(taskId: taskId, origin: origin, interventionId: interventionId, …)`
  块替换为 U14 前形态 `TaskExecutionScreen(origin: origin, interventionId: interventionId)`；
  import 由 deep_link_gate 换 task_execution_screen（diff +2/-5）。
- **命令**：`flutter test test/features/task/task_routes_fix570_gate_wiring_test.dart --no-pub`
- **exit_code = 1**，失败信息：
  ```
  Expected: exactly one matching candidate
    Actual: _TypeWidgetFinder:<Found 0 widgets with type "TaskExecutionDeepLinkGate": []>
     Which: means none were found but one was expected
  ```
  （test/features/task/task_routes_fix570_gate_wiring_test.dart:107）
- **还原后复绿**：+1: All tests passed!（exit 0）。

## M2 · ② _currentScene 写入挪回 ambient 门之前（CH-2/U14 形态）

- **mutation 内容**：`mobile/lib/core/services/sensory_feedback_service.dart` playAmbient 内，
  `_currentScene = scene; await _saveAmbientScene(scene);` 从会话获批后的提交点（:624-625）
  移至 `final previousScene = _currentScene;` 之后、资产门之前（U14 时点 :489 同位；diff +2/-3）。
- **命令**：`flutter test test/core/services/sensory_feedback_service_fix570_test.dart --no-pub`
- **exit_code = 1**，两钉齐红：
  ```
  钉1（:149）Expected: AmbientScene:<AmbientScene.none>
              Actual: AmbientScene:<AmbientScene.rain>
    门拒调用不得留下 _currentScene 残留（CH-2）

  钉2（:179）Expected: true
              Actual: <false>
    门拒后同场景显式重放必须真实可达（被早退吞掉即 CH-2 回归）
  ```
  钉2 即 CH-2 用户症状逐字复现：门拒残留 + 重开开关后同场景显式重放被 `scene == _currentScene` 早退吞掉（played=false）。
- **还原后复绿**：+2: All tests passed!（exit 0）。

## 结论

两缺陷的回归面均可证伪：任何把①接线还原（闸旁路）或②写入挪回门前（状态残留）的合并，本卡各钉必红。
