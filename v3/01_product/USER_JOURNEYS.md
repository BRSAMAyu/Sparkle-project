# Sparkle V3 用户旅程

## Journey A — First 3 Minutes
1. 打开 Sparkle；
2. 两个清晰入口：`体验一个示例` / `开始我的目标`；
3. 真实新用户只回答足够开始的最小问题：目标、时间边界、已有材料（可跳过）；
4. Sparkle 立刻形成一张可读的 Goal Card，而不是做人格问卷；
5. Aurora 给第一个 Smallest Useful Step；
6. 用户能看见“为什么这一步”、预计时间、完成证据、人机分工；
7. 用户开始/调整/拒绝，系统学习到第一条明确偏好。

目标：用户在 3 分钟内理解产品，不需要认识“贝叶斯画像、Memory、RAG、Galaxy”等内部名词。

## Journey B — “我卡住了”
1. 从 Today / Goal / Action 任意位置触发“我卡住了”；
2. Aurora 使用已有 Context 判断信息是否充分；
3. 如果缺关键变量，只问 **一个最能改变决策的问题**；
4. 输出 1 个主方案 + 可选“换个方向”，不倾倒十条建议；
5. 展示旧 Action → 新 Proposal 的差异；
6. 标 Human / Agent / Hybrid；
7. 用户确认后才写真实状态；
8. 结果通过 outcome/evidence 回流。

## Journey C — Hybrid Work
例：用户要完成一段 Related Work。
- Agent：检索/整理候选论文和比较框架；
- Human：阅读关键差异、形成自己的判断；
- Agent：基于用户判断生成结构化草稿；
- Human：做核心论证与取舍；
- Agent：做引用/一致性/格式检查。

Sparkle 的价值是压缩 friction，不是拿走作者认知所有权。

## Journey D — Correction → Future Adaptation
1. Sparkle 判断“太难”；
2. 用户纠正：“不是难，我今天只有 20 分钟”；
3. UI 显示：“本次我会按时间约束调整。要只用于今天，还是这个项目以后都考虑？”；
4. 保存正确 scope；
5. 同项目类似场景合理复用；
6. 不相关场景不引用；
7. 用户可在“我的 → Sparkle 对我的理解”看到并删除。

## Journey E — Return After Days
1. 用户回来；
2. Aurora 不用夸张“想你了”，而是恢复目标状态；
3. 展示“上次停在… / 自那以后变化了… / 建议现在…”；
4. 若计划已过时，先 rescope，不让用户清理 backlog；
5. 用户能在 1–2 次点击回到 meaningful action。

## Journey F — Goal Completion
1. 完成 Action 不是终点；
2. 记录真实 artifact/outcome；
3. Goal trajectory 更新；
4. Galaxy/Chronicle 展示形成的知识、成果和关联；
5. Reflection 回答：“什么真正帮助你推进？”；
6. 仅将有未来价值的信息升级为 Experience Memory。

## Journey G — Failure & Recovery
覆盖：模型失败、断网、工具部分成功、worker restart、版本冲突、权限失效、取消。
核心信任语义：
- 不假成功；
- 结果未知就明确未知；
- 能查询 run 状态；
- 不因为重试产生重复副作用；
- 用户永远知道自己接下来可以做什么。
