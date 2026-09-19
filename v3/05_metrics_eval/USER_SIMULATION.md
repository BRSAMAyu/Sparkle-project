# Agent-driven User Simulation

## Simulator 不是“点遍页面”
每个 Persona 带：goal、knowledge、constraints、preference、frictions、hidden truth、future changes。
Simulator 通过真实 UI 操作，不直接调用内部 API 跳过体验层。

## Session loop
1. reset/create persona；
2. execute natural journey；
3. 根据 UI 决定下一步；
4. 记录“需要开发者解释”的地方；
5. 注入 interruption/offline/time change；
6. next session 观察 continuity；
7. screenshot + trace；
8. 视觉 Reviewer 独立评分。

## Longitudinal
至少覆盖 Day0 / Day1 / Day3 / Day7-like state，不要求真实等待，可通过受控测试时钟推进。

## Ban
不能因为 simulator 知道内部 route 就绕过找不到入口的问题；找不到就是产品缺陷。
