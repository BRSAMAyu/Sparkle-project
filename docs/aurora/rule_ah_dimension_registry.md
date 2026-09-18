# Rule AH · 源状态维度登记（dimension registry）

> 守卫登记文档。维度顺序以 `backend/app/services/source_state_encoder.py` 为唯一事实来源；
> 原未跟踪版本丢失，本文档按其维度常量重建，Rule AH 校验两侧一致。

源状态维度（按编码器声明顺序）：

1. `tool_category` — 工具类别
2. `sufficiency_level` — 充分性等级
3. `conflict_outcome` — 冲突裁决结果
4. `skill_domain` — 技能域
5. `achievement_tier` — 成就层级
6. `calendar_pressure` — 日历压力
7. `cohort_segment` — 群组分段
