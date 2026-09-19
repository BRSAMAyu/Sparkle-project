# Data Flywheel — V3 灵魂

## 1. 闭环
`Interaction/Event → Evidence → User World Update → Context → Aurora Decision → Intervention → Action → Outcome → Evidence`

每个模块必须接入这个闭环，否则它只是孤岛 feature。

## 2. Understanding Dimensions（内部）
不用单一理解百分比。内部至少维护：
- **Coverage**：当前 decision 所需维度知道多少；
- **Correctness**：明确纠正/冲突率；
- **Scope Precision**：是否在正确范围使用；
- **Freshness/Calibration**：旧信息是否被更新；
- **Utility**：个性化是否真实改善 action/outcome。

## 3. Evidence types
explicit user statement > correction > accepted/rejected proposal > artifact/outcome > behavior observation > model inference。

## 4. Feedback loops
### Immediate
accept/reject/edit、why-not、correction。
### Behavioral
start/complete/abandon、actual time、artifact。
### Outcome
goal progress、quiz/result、user-rated usefulness。
### Longitudinal
similar context 中 intervention 的重复效果。

## 5. 禁止的数据飞轮假象
- 用更多聊天量当理解增长；
- 用模型自己给自己打分当效果；
- 用 seed/mock 进入真实 cohort；
- 把相关性写成“这个策略导致成功”；
- 通过隐藏失败样本让指标上升。

## 6. North Star
WVPL：每周至少完成一个 goal-linked outcome/evidence loop 的活跃用户数。

Driver：
- first meaningful value conversion；
- stuck→useful-action rate；
- action→outcome rate；
- correct personalization rate；
- return recovery time；
- proactive precision。

Guardrail：
- over-personalization；
- unsafe autonomy；
- notification burden；
- false success；
- cost/WVPL。
