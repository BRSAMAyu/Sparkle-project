# Auth & Onboarding

## Job
让用户尽快进入自己的真实目标，不把注册/画像建设变成产品主体。

## V3 design
- 首屏清晰区分 `开始我的目标` / `体验一个示例`；
- guest example 与真实 account 数据隔离；
- 注册后不强制长问卷，采用 progressive profiling；
- 建模聊天只问会改变第一步的变量；
- 登录/恢复/游客升级不丢 Goal/Action；
- auth loading/error/offline 双击/重复提交都有反馈。

## Acceptance
- 清状态三端走通；
- URL/session 不残留错误页面；
- guest→account 数据迁移有明确规则；
- seed persona 永不成为真实 Memory；
- 第一 action ≤3min。
