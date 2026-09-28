# Sparkle V4｜有证据的自适应体验
**设计提案与增量 Agent 执行包 · v0.1 · 2026-09-28**

V4 不是重做 V3，也不是给 V3 加一层像素皮肤。目标是把“接得上、改得对、成长有痕迹”做成 Sparkle 自己的交互语言，同时证明历史经验在该用时能改善下一次行动。

## 三个入口
- 团队阅读：`MASTER_DESIGN.md` → `01_product/SIGNATURE_JOURNEYS.md` → `02_design/REFERENCE_CRITIQUE.md`。
- Agent 执行：`05_agents/START_PROMPT.md` → `04_tasks/tasks.json`；JSON 为任务规格唯一真源，Markdown 卡由其生成。
- 风格讨论：`prototype/DESIGN_LAB.html`。这是本地交互示意，不接真实 AI，不含真实产品测试结果；可切换纸昼/暮色/低刺激，体验纠正与回执。

## 本版的权限与冻结点
参考图是提案，不是已批准的全站设计。Agent 可完成组件、内部 preview 与垂直旅程；`v4.pixel.preview` 只在开发预览开放，默认发布仍沿用已验收主题，直到设计选择被明确记录。AI 增量不依赖色板批准；更换色板不应重写业务代码。

名字固定 Sparkle / 星火。能力、目标与底层权限不改名。保留实际五 Tab 的路由合同，不因参考图四 Tab 直接删导航。上线场景仍以当前最有依据的学习/备考/技能项目为锚，不宣称已经服务所有人生需求。

## 开始运行
```bash
python tools/validate_pack.py
python -m unittest discover -s tests -v
python tools/next_tasks.py
```
以上只验证本包、离线参考逻辑和依赖规划，不启动产品，不调用模型，不改仓库。把本包收编进现有仓库后，由 Leader 按 START_PROMPT 绑定已有 CI/模拟器/模型环境，沿用现有 fleet 状态系统。没有真实运行证据的任务不得自动签成 VALUE_PASS。

## 完成含义
`V4_DONE.md` 定义 DESIGN_PREVIEW、ENGINEERING_VERIFIED、VALUE_VERIFIED 与 RELEASE_READY。任何一个都不是“真实用户喜欢/付费/留存”的替代证据。Agent 可以完成模拟器与自动化工作，不能用虚拟用户证明市场匹配，也不能在模拟器中证明真实扬声器和触觉的舒适度。

## 不做什么
不重布 V3 已完成卡；不绕权限/关闭安全来追指标；不自动发布、付费、接受条款或推送到被冻结远端；不新建第二套 Memory/Task 真源；不把“评测诚实失败”当产品效果通过。有关外部依赖沿用原 O-01/Q-07/Q-08 状态，不制造新的重复工程卡。
