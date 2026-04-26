## Lane I Handoff

改动 `adaptive_replanner.py`、`planning_workflow.py`、Aurora runtime service 及对应测试。自适应压缩会读取 `calendar_context`，把保底任务避开冲突并写入建议时段；daily startup 会点名当天日历事件时间，建议空档。验证：`pytest tests/unit/test_adaptive_replanner_stage34.py tests/aurora/test_daily_startup_message.py`，7 passed。遗留：未改日历同步生产链路。
