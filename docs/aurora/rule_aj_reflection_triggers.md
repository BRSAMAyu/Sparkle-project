# Rule AJ/AJ-TRIGGERS · 任务反思触发器登记（reflection trigger registry）

> 守卫登记文档：反思触发类别与运行时开关（env）映射。类别集合以
> `backend/app/services/task_reflection_service.py` 的 `ELIGIBLE_CATEGORIES` / `PROMPT_TEMPLATES` / `TRIGGER_PROMPT_VERSIONS` 为准；
> 原未跟踪版本丢失，本文档按其重建。

| 触发类别 | 运行时开关（env） |
| --- | --- |
| too_difficult | `AURORA_REFLECTION_TRIGGER_TOO_DIFFICULT` |
| unclear | `AURORA_REFLECTION_TRIGGER_UNCLEAR` |
| abandoned | `AURORA_REFLECTION_TRIGGER_ABANDONED` |
| intervention_ineffective | `AURORA_REFLECTION_TRIGGER_INTERVENTION_INEFFECTIVE` |
| plan_stall | `AURORA_REFLECTION_TRIGGER_PLAN_STALL` |
| overload | `AURORA_REFLECTION_TRIGGER_OVERLOAD` |
