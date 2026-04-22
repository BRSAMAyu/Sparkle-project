# Rule AS Exceptions

| 文件 | 方法 | 原因 | 计划收口阶段 |
| --- | --- | --- | --- |
| `backend/app/services/profile_context_service.py` | `_attach_metacognition_dashboard` | Dashboard 继续走既有 UI 路径，不进入 Router | 保留现状 |
| `backend/app/services/profile_context_service.py` | `_attach_metacognition_process_scaffolding` | 继续沿用 Stage 30 prompt path，不在 Stage 35 重构 | 保留现状 |
| `backend/app/services/profile_context_service.py` | `_attach_idiographic_summary` | 继续沿用 Stage 31 的现有消费路径，不在 Stage 33 重构 | 保留现状 |
