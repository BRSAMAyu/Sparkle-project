# Rule AP - Idiographic Individual-Internal Association Discipline

1. 关联计算必须在单用户数据上完成，严禁跨用户聚合。
2. 用户可见发现必须通过模板化语言输出，禁止自由措辞和因果词。
3. 置信度封顶 `0.80`，且仅在 `BH-FDR q < 0.05` 与 `|r| > 0.30` 同时满足时允许展示。
4. 每条发现必须附带样本透明与“这只是你数据中的模式，不代表因果关系”免责说明。
5. Idiographic 输出不得作为 Router 分支条件，只允许作为 Prompt 注入背景。
6. 用户 disconfirm 后，该关联对 30 天内不再呈现。
7. 45 天窗口内出现连续 `>= 5` 天沉默时，必须切断关联窗口。
8. `mood_valence` 不得作为单一关联结论的主导维度。
