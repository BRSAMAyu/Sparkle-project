# Proactive Sparkle

## 1. 原则
主动价值 = 有新信息的及时干预；不是更多通知。

## 2. Trigger Pipeline
Deterministic event trigger → suppression/filter → Aurora decision → NO_ACTION / SUGGEST / AUTO_EXECUTE(if pre-authorized low-risk) → outcome。

Triggers：deadline approaching / task overdue / planned slot missed / user active / upstream completed / goal stalled / new material / run awaiting user。

## 3. Suppression
- quiet hours
- explicit mute
- per-day cap
- cooldown per goal/intervention
- recent rejection
- insufficient novelty
- same suggestion already seen
- no actionable next step

## 4. Quality threshold
通知必须回答：为什么现在、有什么新信息、点开后能得到什么。纯“记得学习”“任务逾期”不够。

## 5. Autonomy
自动执行只用于用户预授权、低风险、可撤回操作；默认建议式。

## 6. Metrics
proactive precision（被接受/有后续行动）、dismiss/mute、repeat rate、WVPL contribution、notification burden。不要用打开率单独优化。
