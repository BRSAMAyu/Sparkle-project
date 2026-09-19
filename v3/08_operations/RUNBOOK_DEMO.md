# Demo Runbook（工程版）

这是 V3 产品验收演示，不替代比赛人工讲稿。

## Golden story
1. 进入“体验示例”快速看到真实感 Goal；
2. 切换到“开始我的目标”；
3. 输入一个目标；
4. Today 生成第一个 useful action；
5. 用户说“我不是不会，只是今天20分钟”；
6. Aurora 显示 correction + scope；
7. 生成新的 Hybrid action；
8. Agent 做机械部分，用户完成判断；
9. outcome 进入 Galaxy/Chronicle；
10. 新 session 同类场景正确复用；
11. “Why this?” 展示来源并允许删除；
12. 删除后重新决策不再使用。

## Technical prep
- disk >10GB free；
- 4GB+ AVD；
- 不同时跑多个重构 build；
- provider probe；
- queue/DB/Redis/MinIO health；
- staging HTTPS health；
- kill switches snapshot；
- clean demo account + separate seed example；
- trace dashboard open。

## Failure story
如果模型/provider 失败，产品应展示真实降级，不临时切假回复。
