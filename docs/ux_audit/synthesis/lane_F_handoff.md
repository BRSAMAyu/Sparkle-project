## Lane F Handoff

已验证 Round 1-12 证据仍存在：`from_modeling_complete` 首轮会停在策略确认态，前端拿不到 `plan_id` 后显示错误，并且返回兜底指向 onboarding。

本次改动让建模完成桥接会话在规划信息齐全时首轮直接生成 Sprint 计划和任务；前端拿到规划 metadata 后进入计划详情，同时刷新计划列表、计划详情和学习档案。建模页系统返回现在兜底到首页，计划详情返回也会在无栈时回首页。新增后端测试覆盖首轮建模桥接直接产出 plan/task，更新 Flutter widget 测试覆盖自动规划携带建模输出、拿到 plan route 后不显示错误并进入计划页。

验证：`pytest tests/orchestration/test_planning_workflow.py::test_modeling_complete_bridge_generates_plan_on_first_turn tests/orchestration/test_planning_workflow.py::test_exam_sprint_fast_track_single_message_enters_planning_with_pack_prefill`、`pytest tests/integration/test_north_star_journey.py::TestNorthStarJourney::test_modeling_to_plan_auto_bridge`、`flutter test test/widget/modeling_chat_screen_test.dart` 均通过。`flutter analyze` 仍失败于仓库既有 5306 条 info；本 lane 触碰文件的定向 `dart analyze` 仅剩 `plan_detail_screen.dart` 两条既有 info。
