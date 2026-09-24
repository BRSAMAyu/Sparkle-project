# WT313 · Comeback 引擎侧重校准（replan 执行器 + 日期感知 highlights）

> 注：worker 原始 REPORT.md 与 changes.patch 在主会话删树时未入 git（树内未 commit 未落盘），随 worktree 移除丢失。
> 本报告由 worker 返回回执忠实重建；代码改动完整（见 33a1c513 五文件，+567/−12）。

## 缺陷复现（base 全红，7 例新 API 测试）
1. `_build_day_highlights` 恒推 Day 1：Day6 推导日实测 `got 1`。
2. `recommended_action:"replan"` 有标签无端点：`POST /plans/{id}/replan` 404。
3. health 无「离开」维度：`days_since_last_activity` 读取即 `KeyError`。

## 修法
- **日期感知 highlights**：以 plan 开始日 + 今天推派生日（不做日程截断）；today/resume/completed 三态诚实降级；payload 增 `today_day` / `degraded`。
- **replan 执行端点**：走 `PlanService.update` 既有链重锚超期终点（今天 + 未完成任务跨度）；回执落 `source_metadata.last_replan`；三种情形无变更 no-op 保幂等；属主不符 404。
- **health 离开维度**：`PlanProgressService` 增 `days_since_last_activity` metric + reason（阈值 3 与 mobile wt303 同口径；活动信号取 max 只放宽不收紧）。
- **网关纯透传一行**（proxy_routes.go，BA-ROUTES 门强制——缺它移动端触达不到）。

## 测试证据
- plans 域 12/12 绿（树内 + 主树复验）
- 定向回归 1110+ 例全绿（含 health 信号族 983）
- gateway handler 全包 go test 绿（CGO_ENABLED=0）
- mypy 冷缓存 1795 棘轮持平（主树复验；2 条闭包窄化新增已在卡内归零）
- black / ruff / gofmt 干净；守卫 83 rules exit 0

## 交接与风险
- 真 rescope（任务重排）不在本卡范围——本卡只做重锚；
- mobile 侧可开始消费 `today_day` / `degraded` / `days_since_last_activity`（wt303 的 staleness 判定可升级为服务端真源）。
- 工程教训：worker 交付物必须 commit 进分支后再返回（已在舰队协议加硬条款，本卡为教训案例）。
