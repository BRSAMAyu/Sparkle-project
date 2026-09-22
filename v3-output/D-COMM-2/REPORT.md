# D-COMM-2 · 光子→Pro 7 天有界兑换通道（「学出会员」）收工报告

- Worker：D-COMM-2 ｜ worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt156`（基线 `52fe93a7`）
- 交付物：本报告 + `changes.patch`（5 文件，新文件 `--- /dev/null` 头）
- 纪律：未 commit / 未 push / 主仓只读 / 未动活栈 / 无迁移 / 无凭据

## 0. 结论速览

`POST /api/v1/photons/redeem-pro`（authed）落地：合同/首胜/成就类光子按 **3000 光子 = Pro 7 天【待产品校准】** 兑换，**自然月硬顶 1 次**，`transfer_in` 不计入可兑换基数，复用 D-REDEEM `_grant_pro` 叠加语义写 `users.entitlement + entitlement_expires_at`。**零迁移、零网关 diff、免费闭环零变化（对比法验证零新增失败）**。

## ① 盘点表（只读盘点结论）

| 面 | 现状 | 对本卡的意义 |
|---|---|---|
| 余额存储 | `users.photon_balance` **单一混桶字段**，无来源分桶 | 可兑换基数必须走**审计流水重放**（`photon_transaction_history`），不能按桶汇总 |
| 流水覆盖（收入侧） | `grant_achievement` / `grant_contract` 发放点 `record_history=True` ✅；`grant_daily_first`（achievement_engine:2736）与 combo `grant_bonus`（:2665）**未入流水** | 基数重放按设计卡四类型词表；缺口为**发放侧既有现状**，见 ④ 诚实申报 |
| 流水覆盖（支出侧） | 契约失败扣 stake `record_history=True` ✅；transfer_in/out 恒有流水 ✅ | `deduct_contract_stake/penalty` 可同步扣减基数；transfer 双向均被词表排除 |
| 类型枚举 | DB 枚举 `models/shop.PhotonTransactionType`（String 列，枚举仅做映射）；未知类型落 `admin_adjustment` 兜底 | 新增 `REDEEM_PRO="redeem_pro"` 枚举成员（纯增量），专有审计类型不落兜底误标 |
| 核销链路衔接点 | `redeem_service._grant_pro`：叠加语义（有效期内顺延 / 过期与 free 起算 / **永久 pro 保持 NULL 绝不降级**） | 本卡直接复用该核（`from app.services.redeem_service import _grant_pro`，任务卡明示"复用 D-REDEEM 核销核"），判级真源唯一（`core/entitlement.py`） |
| Pro 判定面 | `users.entitlement('free'|'pro')` + `entitlement_expires_at`；网关 `IsProEntitlementEffective` 同语义 | 兑换只写既有两列，网关零改动即生效 |
| 幂等面 | `IdempotencyMiddleware` 只保护 chat/tasks/plans/events 四前缀；photons 域无 | 本通道以**月顶为幂等屏障**（见 ②），不新增中间件路径 |
| 网关面 | `/photons/*path` authed catch-all（`proxy_routes.go:1120` + `registerREST` 全方法注册） | `POST /api/v1/photons/redeem-pro` **天然被代理，网关零 diff**；BA-ROUTES 守卫实测通过（352 proxy ↔ 963 engine） |
| 端点路径命名 | 任务卡写 `photon/redeem-pro`；引擎既有前缀为 `/photons`（复数）且网关 catch-all 挂在该组 | 按既有约定落 `/photons/redeem-pro`，换取零网关改动（偏差已在 ④ 申报） |

改动面（全部最小侵入）：新增 `photon_redeem_service.py` + 测试文件；`photons.py` 追加一个端点；`settings.py` 追加 3 常量；`shop.py` 追加 1 枚举成员。**未动 photon_service.py / redeem_service.py / entitlement.py 任何既有行**。

## ② 月顶与防刷实现论证

**判定真源 = 审计流水本身**：当月已兑笔数 = `photon_transaction_history` 中 `transaction_type='redeem_pro'` 且 `created_at >= 自然月起点(UTC)` 的行数。审计即状态，**零新表零迁移零新唯一约束**。

**并发不超月顶（验收①，模式同 D-REDEEM §0 条件 UPDATE 族）**：单事务内以光子原子扣减（`UPDATE users SET photon_balance = photon_balance - cost WHERE photon_balance >= cost` 行内守卫，复用 `PhotonService._deduct_balance_atomically`）为**每用户串行化点**：

1. 并发同用户请求在扣减行锁上排序（PG 行锁 / sqlite 写锁，两引擎同效）；
2. 后到者获锁后做**月顶复查**——READ COMMITTED 新快照必见先到者已提交的 `redeem_pro` 流水 → 拒绝；
3. 自身流水**晚于复查**才写入（自查不可见自身行，排除恒真误判）；
4. 拒绝路径服务内 `rollback()` 自愈，撤销已 flush 的扣减，**拒绝零副作用**。

测试实证：8 并发恰 1 成功 / 7 月顶拒；余额恰扣一次；entitlement 只 +7 天未叠加双倍；流水恰 1 条。

**防刷三闸**：
- `transfer_in` 不在收入词表 → 小号互转来的光子**基数恒 0**（实测：受让方余额充足仍被拒 `insufficient_base`）；`transfer_out` 也不返还转出方基数，但转出后物理余额归零，扣减闸兜底；
- 基数闸：四类收入净额（减契约失败 stake/惩罚）≥ cost 才放行 → 商城消费、转账支出无法"重赚"基数；
- 余额闸：混桶物理余额行内守卫（负余额不可能）。

**幂等（验收红线）**：月顶即幂等屏障——同月重复请求恒返回同一结构化终态 `monthly_cap_reached`（409），不重复扣减、不重复授予，状态收敛（实测前后快照相等）。比 `Idempotency-Key` 头更强的语义：无头重放、跨端重放均收敛。故未要求该头（与 `/photons/transfer` 的差异已申报）。

**防套利边界**：月顶 1 次 × 7 天 = 月获取 Pro 上限 8 天等效，营收蚕食有界；兑换是已赚光子的出口，免费闭环零变化（零光子新用户 API 面实测：balance/transactions 照常、兑换 409、余额与 entitlement 不动）。

## ③ 冲突面（零交集声明）

| 在途卡 | 面 | 交集判定 |
|---|---|---|
| wt144 events | 事件总线/ingest | **零交集**——本卡不触 events 域任何文件 |
| wt155 排行榜 | leaderboard/CQRS 读模型 | **零交集**——本卡不触 leaderboard；且设计卡明确榜分不用行为量，光子兑换不回写任何榜面 |

git status 全量：仅本卡 5 文件（3 改 + 2 新），无其他域文件被动。`models/shop.py` 仅追加枚举成员（纯增量，shop 套件两侧对比 4P=4P）。

## ④ 诚实申报

1. **汇率未校准**：3000 光子 / 7 天 / 月顶 1 次为设计卡保守拍定值，已进 `settings`（`PHOTON_REDEEM_PRO_COST/DAYS/MONTHLY_CAP`）并全量标注【待产品校准】；校准只动配置不动代码。
2. **基数口径的既有缝隙（发放侧，非本卡引入，未修）**：a) 每日首胜发放未开 `record_history`（achievement_engine:2736），流水无该收入；b) combo 加成用 `grant_bonus` 类型，不在设计卡四类型词表（且该字符串不在 DB 枚举内，历史行落 `admin_adjustment` 兜底）。两者后果均为**基数少算、可兑上限降低（fail-safe 方向：绝不放水）**。未顺手修的原因：给 daily_first 补流水会触发 `_find_existing_transaction` 去重路径（type+amount+source+related_item_id 四元组比对）把次日首胜误判为重复发放——需独立设计去重键（如 source 带日期），属发放侧独立卡。
3. **路径偏差**：任务卡写 `/api/v1/photon/redeem-pro`，实落 `/api/v1/photons/redeem-pro`（既有复数前缀 + 网关 catch-all 零改动）。移动端接卡时以实落路径为准。
4. **transfer 语义口径**：`transfer_out` 不返还转出方基数（设计卡只列 stake/penalty 为扣减项）；意味着"转出再转回"不能刷基数（转回部分仍是 transfer_in）。
5. **billing 侧双写**：设计卡"双写流水"落为 photon 侧 `redeem_pro` 流水行 + 结构化审计日志（`photon redeem ok/rejected ...`，与 D-REDEEM 的 logger 注记同款）；D-REDEEM 的 billing 侧无独立表可复用（其审计即日志 + redeem_codes 表，与本通道无关），未造第二张表。
6. **访客守卫**：端点照 `/photons/transfer` 同款 `is_guest` JWT 声明守卫；单测基座无法注入 request.state，该分支未单测覆盖（代码路径与 transfer 逐字同款）。
7. **测试基座限制**：测试级 `db.rollback()` 后同会话再查询在 aiosqlite+NullPool 下触发 greenlet 断链（SQLAlchemy 2.0.48 测试基座特有，生产 asyncpg 路径无此问题）——测试改为列选择直读 + 拒绝路径零写入断言；服务内拒绝路径 rollback 的正确性由并发用例（7 个失败者各走一次内部 rollback）实证。

## ⑤ 收工核查

- **新测试 11/11 绿**：正常兑换（扣减/授予/专有流水/枚举不落兜底）、stake 净额口径、transfer_in 排除（双向）、余额不足拒、月顶+幂等收敛、跨月额度恢复、8 并发恰 1 成功、有效期顺延、永久 pro 保护、API 终态映射、免费闭环抽查。
- **定向回归对比法零新增失败**（改动侧 = 基线克隆侧）：
  - rd01 + photon_service + o04：`1F/42P = 1F/42P`（唯一失败 `test_request_tier_wires_into_context_budget_dimensions` 两侧同败，原因 `ModuleNotFoundError: app.gen`——worktree 未跑 `make proto-gen` 的环境缺口，与本卡无关）；
  - photon_service_simple + d02_spine：`10P = 10P`；shop_service：`4P = 4P`。
- **守卫绿**（定向 4 条）：BA-ROUTES ✅（352↔963，catch-all 覆盖新路由）、BB 金融原子性 ✅、DB-HEAD 单头 ✅（`erridemconc_20260922`，未挂新头——无迁移）、BA 契约 parity ✅。
- **纪律**：未 commit/push；主仓只读；worktree 无 .env；测试全部 `DATABASE_URL="sqlite+aiosqlite:///:memory:" SECRET_KEY=test` 前缀 + 绝对路径 pytest + 定向文件级运行（无裸跑全量）；基线克隆 `/tmp/dcomm2-baseline` 已于收工删除；无构建产物、无遗留进程。
