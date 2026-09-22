# PHOTON-STATUS · 兑换前状态快照端点 + mobile 真数接线 — 收工报告

> 卡：北极星全旅程战役 D 纵队 / MOBILE-GAP-2 诚实申报的引擎缺口补齐
> worktree：`wt168`（基线 `c5a0e47d`）｜日期：2026-09-22
> 口径源：`v3/FLEET-BRIEF.md` 口径词典——「可兑换基数」= 审计流水重放（四收入类型+首胜/combo，transfer_in 排除）

## 0. 一句话

新增 `GET /api/v1/photons/redeem-pro/status`（与 `POST /redeem-pro` 同一 service 判定函数，零第二套算法），mobile 兑换屏的「由服务端核算」占位换成 status 快照真数，兑换响应后刷新——用户在决定前看到真数。

---

## ① 同源一致性证明（红线）

**引擎侧单一真源承诺（结构性保证，非仅测试保证）**：`get_redeem_status()` 不含任何新算法——

| 判定 | status 复用的函数 | 与兑换路径共用 |
|---|---|---|
| 可兑换基数 | `get_redeemable_base()`（审计流水重放） | `redeem_pro()` 校验同一函数 |
| 月顶判定 | `_count_redeems_in_month()` | 兑换快速失败面 + 串行化后复查同一函数 |
| 金额/时长/月顶常量 | `redeem_pro_cost()/days()/monthly_cap()` | 兑换同一常量函数 |
| 月窗 | `_month_start()` / 新增 `_next_month_start()`（纯日历推导） | 同一 UTC 自然月语义 |

唯一新增查询 `_latest_redeem_at_in_month()` 只取**展示面时间戳**（当月最近一条 `redeem_pro` 流水的 `created_at`，过滤条件与 `_count_redeems_in_month` 逐字相同）；月顶**判定**不走它，杜绝判定/展示双算法。

**测试钉死（`backend/tests/unit/test_photon_redeem_pro_status.py`，12 条全绿）**：
- service 层：同一用户 `status.redeemable_base == redeem_pro() 终态揭示值`（`test_status_base_equals_redeem_outcome_reveal`）；
- HTTP 层：`GET status` 的 `redeemable_base` == 随后 `POST redeem` 响应 `data.redeemable_base`；且 `balance_after == status.balance − status.cost_photons`（`test_api_status_base_equals_redeem_response_reveal`）；
- transfer_in 场景：status 的 `balance=3000/base=0` 与兑换拒绝面同判 `insufficient_base`（`test_status_base_transfer_income_excluded_same_as_redeem`）；
- 月顶翻转：兑换前 `monthly_cap_used=false` → 兑换后 `true` + 时间戳 == 本通道流水 `created_at`（同真源交叉验证）+ `next_window_at` = 下月 UTC 月初；API 面再翻转一次（`test_monthly_cap_flips…` / `test_api_status_contract_and_cap_flip`）。

## ② 实现清单

**引擎（2 文件）**：
- `backend/app/services/photon_redeem_service.py`：`PhotonRedeemStatusSnapshot` dataclass + `get_redeem_status()`（纯只读）+ `_next_month_start()` + `_latest_redeem_at_in_month()`
- `backend/app/api/v1/photons.py`：`GET /redeem-pro/status`（`# route-tier: authed`，照 D-COMM-2 POST 先例；响应 `data`: `redeemable_base / balance / cost_photons / pro_days / monthly_cap / redeems_this_month / monthly_cap_used / monthly_cap_redeemed_at / next_window_at / can_redeem`）

**网关（0 文件）**：`/photons/*path` catch-all（GET 在 `registerREST` 五动词内）已覆盖新路由——BA-ROUTES 367↔982（981→982 仅 +1 本路由）56 catch-all groups OK；`CGO_ENABLED=0 go test ./internal/handler/ -run "TestProxyRoutesHandler_RouteRegistration|TestProxyRoutesHandler_RegisterProxyRoutes"` 绿；`git status backend/gateway/` 零 diff（照 D-COMM-2 同款验证法）。

**mobile（5 文件）**：
- `lib/core/network/api_endpoints.dart`：+`photonRedeemProStatus`
- `lib/features/photon/data/models/photon_redeem_pro_model.dart`：`PhotonRedeemProOverview` 扩展（`redeemableBase/costPhotons/proDays/monthlyCap/nextWindowAt/canRedeem`）+ 手写 `fromStatusJson`（对齐 `PhotonRedeemProResult` 风格；字段缺失不猜，`redeemableBase` 恒 nullable）
- `lib/features/photon/data/repositories/photon_redeem_pro_repository.dart`：`getOverview()` 改为单次 `GET status`（原「余额+流水两读」合一）；**删除客户端 UTC 月窗自算** `_hasRedeemedThisMonth()`——月顶判定交还引擎同源，消灭双端漂移面；demo 态诚实空账本零值
- `lib/features/photon/presentation/screens/photon_redeem_pro_screen.dart`：基数真源链 `status 快照 → 兑换响应揭示 → 展示常量兜底`；不足预判与引擎拒绝顺序同序（基数→余额）动作前呈现；兑换响应后 `ref.refresh` 快照
- **provider 未改结构**（读面经仓库直达 status）；**l10n 零改动**（`photonRedeemProBaseHint`「由服务端核算」降级为 status 缺失基数时的诚实兜底，zh/en 无新键）

**测试（2 文件）**：引擎新测试 12 条（上表 + 常量回显/只读三不动/零光子诚实零值/上月流水不翻转）；mobile 屏幕测试 11 条（占位→真数断言、status 契约钉死、兑换后刷新计数断言、老引擎无基数字段兜底）。

## ③ 冲突面声明

- 与 **wt162（backend tour）**：零交集——本卡只动 photon service/api 两文件，不动编排/文档面。
- 与 **wt166（backend intake）**：零交集——未动 intake 域任何文件；`photons.py` 仅在文件尾追加新路由 + 删一行既有 unused import（`REDEEM_PRO_OK`，ruff F401，基线即未使用）。
- 与 **wt167（mobile 小队）**：零交集于功能面（未动 squad/community 任何文件）；**潜在文本冲突面仅 `mobile/lib/core/network/api_endpoints.dart`（共享注册表，本卡只 +1 行常量）**与 mobile 测试目录（本卡只动 photon 兑换屏测试文件）。l10n arb、`photon_routes.dart`、shop 屏均零改动。
- 改动统计：7 文件修改 +343/−79，1 引擎测试新文件；无 DB 迁移、无 proto 变更、无网关变更。

## ④ 诚实申报（残余缝隙）

1. **快照有时效性**：status 是读取时刻的快照，并发窗口下 `can_redeem` 可能过期——UI 已声明「最终以兑换响应终态为准」，兑换失败路径原样保留为第二道诚实揭示。
2. **时间戳格式**：`monthly_cap_redeemed_at/next_window_at` 为 naive-UTC isoformat（无 Z 后缀）——与既有 `entitlement_expires_at` 契约同一形制，未另起炉灶。
3. **balance 走 5min TTL 缓存**（`PhotonService.get_balance`，与 `GET /photons/balance` 同源同缓存；增减/兑换路径均主动失效缓存）——status 的余额可能与极近期的他端变动有至多一个缓存 TTL 的窗口，与现有余额面完全一致，未加重新。
4. **demo 模式**返回空账本真值（0/0/false），不造假资产；与真实新用户 status 响应一致。
5. **风格工具声明**：本机可用 black 为 26.3.1，对基线未改文件同样报 reformat（代码库为旧版 black 形制）——新增代码逐行对齐所在文件的既有形制，未用新版 black 重排既有行制造 patch 噪音；ruff 全绿（含修复本卡触达文件内 3 处可自动修复项，其中 1 处为基线遗留 unused import）。

## ⑤ 回归与收工核查

**定向回归（对比法）**：
- 引擎 photon 域 + D-COMM-2 族 6 文件：基线 **58 passed** → 改后 **58 passed + 新文件 12 passed = 70 passed，零新增失败**；
- mobile：兑换屏测试 **11 passed**（占位→真数断言更新后）+ 相邻批 2 文件 **29 passed**（`--concurrency=1`，共 3 文件/批，符合资源纪律）；
- 守卫：BA-ROUTES ✅ / AX(route-tier DIFF) ✅ / BA(gateway-contract parity) ✅ / i18n-coverage ✅ / L10N-REGEN-PARITY ✅ / UX-component-convention ✅；
- dart analyze（触达文件）：0 error / 0 warning，残留 15 info 全部为 photon 目录基线既有。

**收工清理**：`mobile/build`（123M）、`mobile/.dart_tool`、本卡生成的 proto 产物（`mobile/lib/gen`、`backend/app/gen`、`backend/gateway/gen`，gitignored 可再生）、`/tmp/photon-status-*` 探针文件；pytest 全程 `-p no:cacheprovider` 无缓存残留；无模拟器/长驻进程。

**交付物**：本报告 + `changes.patch`（含新测试文件）。零凭据、零 commit、零 push。
