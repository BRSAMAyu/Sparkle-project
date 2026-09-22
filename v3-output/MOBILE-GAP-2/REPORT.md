# MOBILE-GAP-2 收工报告：光子兑 Pro 入口（D-COMM-2「学出会员」移动端面）

- Worker: MOBILE-GAP-2 ｜ worktree: `/Users/brsama/code/GitHub/Sparkle-sysrev/wt165` ｜ 基线 `4d2a385a`（含 MOBILE-GAP 自我锚先例）
- 交付物: `v3-output/MOBILE-GAP-2/REPORT.md` + `changes.patch`（16 文件，其中 5 新文件带 `--- /dev/null` 头；出 patch 后已 `git reset -q`，patch 已在基线克隆 `git apply --check` 验证干净可贴）
- 状态: **未 commit / 未 push**（纪律遵守）｜ 零凭据

---

## ① 并入 vs 新屏裁决：**新屏**（`/photon/redeem-pro`）

只读盘点 `mobile/lib/` 既有光子/资产消费面：

| 面 | 现状 | 证据 |
|---|---|---|
| `PhotonBalanceCard` | **孤儿组件**（全库无宿主） | `grep PhotonBalanceCard` 仅命中定义文件自身 |
| `/photon/history`（TransactionHistoryScreen） | 已路由但唯一入口在上述孤儿卡内 | `photon_balance_card.dart:30` 唯一 push 点 |
| `/photon/transfer` | 已路由、**零入口** | 全库无 push 命中 |
| 商城 `/shop` | 既有唯一活跃光子消费面（经 streak_details 可达），购买确认弹窗 watch 光子余额 | `purchase_confirmation_dialog.dart:32` |
| 设置页 | 有 D-REDEEM 兑换码入口（ListTile+对话框），非光子资产面 | `unified_settings_screen.dart:704` |

**结论：不存在活的「光子页」可并入**——并入即等于先建钱包聚合页（余额+流水+转账+兑换四合一），超出本卡必达并扩大回归面。商城并入方案否决：商城是「购买」语义框架（违反本卡「禁止买/解锁才可用暗示」红线），且其六 Tab 网格结构插入动作卡改动面大。故照 MOBILE-GAP 自我锚先例落「新屏 + 一次级入口」：新屏 `/photon/redeem-pro`，次级入口挂商城 AppBar ghost 图标（商城是既有唯一活跃光子经济面，Tooltip 语义与自我锚入口同款）。

## ② 实现清单（6 改 + 5 新）

| 文件 | 改动 |
|---|---|
| `mobile/lib/core/network/api_endpoints.dart` | +1：`photonRedeemPro = '/photons/redeem-pro'` |
| `mobile/lib/features/photon/data/models/photon_redeem_pro_model.dart` | **新**：`PhotonRedeemProResult`（成功 envelope `fromJson` + 结构化 `detail` 的 `fromDioError`，照 RedeemCodeResult 手写风格，不进 build_runner）+ `PhotonRedeemProOverview` + 有界终态枚举（对齐引擎词表 `ok/insufficient_balance/insufficient_base/monthly_cap_reached/error`）+ 展示常量 3000/7【待产品校准，响应值优先覆盖】 |
| `mobile/lib/features/photon/data/repositories/photon_redeem_pro_repository.dart` | **新**：`getOverview()`（`GET /photons/balance` + `GET /photons/transactions?transaction_type=redeem_pro` 服务端过滤 → UTC 自然月窗判定当月已兑）+ `redeem()`（POST，业务失败映射有界终态，不向 UI 泄漏异常结构）；demo 分支诚实零资产 |
| `mobile/lib/features/photon/presentation/providers/photon_redeem_pro_provider.dart` | **新**：autoDispose AsyncNotifier（照 self_anchor_provider 现行风格）+ repository provider |
| `mobile/lib/features/photon/presentation/screens/photon_redeem_pro_screen.dart` | **新**：SPEC v1.0 必达项 2——①光子资产卡（余额与可兑换基数**两数分开**；基数只由服务端响应揭示，未揭示前显示「由服务端核算，兑换时揭示」不产数字；基数<余额时如实注明「其余 N 光子来自转账等来源，不计入可兑换基数」）②兑换动作卡（成本/时长/月顶三要素 + 确认对话框 + 有界终态）。唯一交互 accent（brandPrimary 主按钮），状态区分只用文字层级；全令牌消费（context.colors/typo/space/radius），组件全部消费 owner（SparklePageScaffold/GraphiteCardSurface/SparkleButton/SparkleIconButton/SparkleRefreshIndicator/SparkleCardSkeleton/CustomErrorWidget/AppFeedback/ContentConstraint） |
| `mobile/lib/features/photon/photon_routes.dart` | +1 路由：`redeemPro = '/photon/redeem-pro'`（`app/routes.dart` 已聚合 `...PhotonRoutes.routes`，零改动自动生效） |
| `mobile/lib/features/photon/presentation/widgets/transaction_history_list.dart` | +2：枚举新成员的图标 switch case（见下条，编译必需） |
| `mobile/lib/shared/entities/photon_model.dart` | +`@JsonValue('redeem_pro') redeemPro` 枚举成员 + `transactionTypeName` case——**相邻域必修**：后端已上线写 `redeem_pro` 流水，`$enumDecode` 遇未知值抛 ArgumentError，不加成员则既有交易历史页在首笔兑换后必崩 |
| `mobile/lib/shared/entities/photon_model.g.dart` | build_runner 重生产物，diff 恰 +1 行（枚举映射），无其他漂移（全量 codegen 产生的无关 .g.dart 漂移已逐个 `git checkout --` 回退） |
| `mobile/lib/features/shop/presentation/screens/shop_screen.dart` | +13 行：AppBar actions 追加「光子兑 Pro」ghost 图标按钮（Tooltip 语义），次级位置不占内容主面积 |
| `mobile/lib/l10n/app_zh.arb` / `app_en.arb` | +25 键 ×2（`photonRedeemPro*` 24 键 + `photonTransactionRedeemPro`），带 `@` placeholder 元数据 |
| `mobile/lib/l10n/app_localizations*.dart`（3 个生成文件） | `flutter gen-l10n` 产物；diff 全部为插入（452 insertions / 0 deletions），基线重置后干净 |
| `mobile/test/features/photon/presentation/screens/photon_redeem_pro_screen_test.dart` | **新**：8 个测试（2 契约钉死 + 6 widget，见 ③） |

### SPEC 与语气申报

- 必达项 2/面（资产卡、动作卡），次级入口为导航不占必达；唯一 accent；零 `Color(0x…)`/`Colors.*`/`fontSize:` 字面量。
- 价值增量语气全检：25 个新文案键零「买/购买/解锁」字样、零免费功能提及；口径是「学习所得的光子，随时可兑换成 Pro 时长」（奖励出口，非付费墙）。

## ③ 回归结果

### 新测试 `photon_redeem_pro_screen_test.dart`（串行 `--concurrency=1`）**8/8 全绿**

1. **契约钉死 ×2**：成功 envelope 解析（成本/天数/基数/兑换后余额/到期时间）；结构化 409 detail → `insufficient_base` 映射 + 无结构体 body 时诚实退化为 `error`（409 双语义不可猜）。
2. **可兑态**：两数分开（余额 5200 + 基数未揭示 hint）+ 三要素（3000/7 天/尚未使用）+ 按钮可用 → 确认对话框（成本/不退还文案）→ 兑换成功 toast + 卡面翻转（余额 2200、月顶已用、按钮禁用）。
3. **基数不足态**：服务端响应揭示基数 1200 < 余额 5200 → 基数数字 + 「其余 4000 光子来自转账等来源」诚实注明 + 解释文案 + 按钮禁用。
4. **已月顶态**：overview 当月已兑 → 「本月已兑换，下月 1 日起可再兑」+ 按钮禁用 + 点击无对话框且不打接口（redeemCallCount==0）。
5. **余额不足**：500 < 3000 → 按钮禁用 + 「光子余额不足」。
6. **错误态→重试**：快照失败诚实错误文案 + 重试翻转回数据态。
7. **路由可达**：`/photon/redeem-pro` 经 `PhotonRoutes.routes` 注册进 GoRouter 直达渲染。

### 既有测试定向回归（全部串行 `--concurrency=1`，分批）

| 批次 | 文件 | 结果 |
|---|---|---|
| 1 | `photon_repository_test` + `photon_provider_test`（photon 域存量） | **29/29 绿** |
| 2 | `router_smoke_test` + `router_deep_link_test`（全量路由装配，含新路由） | **12/12 绿** |
| 3 | `shop_repository_test` + `shop_provider_test` + `equipment_display_provider_test`（次级入口所在商城域） | **45/45 绿** |

### analyze 与守卫

- 触碰面 `flutter analyze`：**0 error / 0 warning**；余 20 条 info 逐条与 `git diff -U0` 行号比对，全部为存量行（`photon_transfer_screen`/`photon_balance_card`/`shop_screen` 旧行/photon_provider.dart/photon_provider_test——均非本卡改动行）。
- `check_ux_component_convention.py`：**PASS**（rawButton 19/19、rawChip 11/11、colorLiteral 100/100——新代码零新增违规）。
- `check_ui_design_tokens_ratchet.py`：**PASS**（color 239/275、fontSize 719/727）。
- `check_l10n_regen_parity.py`：**OK**（11144 模板键 == abstract 成员，zh/en 子类完整）。
- `check_i18n_coverage.py`：**PASS**。

### 环境修复申报（非代码改动，均 gitignore 内不入 patch）

worktree 缺未入库产物导致首跑编译失败，照 MOBILE-GAP 先例补齐：`flutter pub get` → `flutter gen-l10n`（产物入 patch，见上表）→ `buf generate --template buf.gen.dart.yaml`（本机 `~/.pub-cache/bin` 的 protoc-gen-dart，补 26 个 `lib/gen/*.pb*.dart`）→ 全量 `dart run build_runner build`（补 community freezed 等缺失产物 + 重生 photon_model.g.dart；**无关存量 .g.dart 的 codegen 漂移已全部回退**，最终入库 diff 仅 photon_model.g.dart +1 行）。

## ④ 冲突面（零交集声明）

- **wt161**（JOURNEY-DRIVER，backend northstar_eval 域）、**wt162**（backend，工作树干净）、**wt164**（backend community_shared_errors + 一条迁移）：三卡全 backend 面，本卡全 mobile 面 + v3-output 专属目录，**文件面零交集**；`mobile/` 内本卡未触碰 plan/leaderboard/aurora 等任何在途域。
- l10n 两文件若与后续卡同轮追加键，合入时按各自区段插入，冲突 trivial（`git apply --3way` 可解；patch 已在基线克隆验证干净可贴）。
- `v3-output/MOBILE-GAP-2/` 为本卡专属输出目录，无他卡使用。

## ⑤ 诚实申报

1. **无 GET 状态端点，基数与月顶的数据源裁决**：引擎仅有 `POST /photons/redeem-pro` 一个兑换端点，**没有**可兑换基数/月顶的查询端点（盘点 `app/api/v1/photons.py` 全部 6 条路由证实）。故：①**可兑换基数只由兑换响应揭示**（成功 data 或失败 detail 均带 `redeemable_base`），动作前绝不本地推算、不展示编造数字（显示「由服务端核算，兑换时揭示」）；②**月顶状态**复用引擎同款真源——`GET /photons/transactions?transaction_type=redeem_pro`（服务端过滤）+ 客户端只做「created_at 是否落在本 UTC 自然月」窗口判定，即「审计即状态」的只读镜像，非自造口径。建议后续卡给引擎补 `GET /photons/redeem-pro/status` 以省一次往返。
2. **成本/时长为移动端展示常量**（3000/7，对齐引擎 settings【待产品校准】）：动作前展示用它；一旦有响应，成本/天数/基数全部以服务端返回值覆盖展示（`_lastResult` 优先），把「配置漂移导致文案撒谎」的窗口压到首次动作之前。常量已在模型文件显式命名并注明待校准。
3. **`redeem_pro` 枚举成员属相邻域必修而非顺手重构**：后端 D-COMM-2 已上线即写该类型流水，mobile 侧 `PhotonTransaction.fromJson` 的 `$enumDecode` 遇未知枚举值抛 ArgumentError——不加成员，首笔真实兑换发生后交易历史页解析即崩。连带 `transactionTypeName`/图标 switch 两处 case + 1 个 l10n 键。未跑商城/流水的额外 UI 测试（该文件无既有 widget 测试，编译期 switch 穷尽检查已由 analyze 0 error 覆盖）。
4. **demo 模式只覆盖读面**：`getOverview()` demo 态给诚实零资产；`redeem()` 不特判 demo（照 D-REDEEM `redeemCode` 既有先例——demo 下走真实接口得到业务终态，不造假成功）。
5. **409 无结构体 body 时退化为 `error`**：409 同时承载 `insufficient_base` 与 `monthly_cap_reached`，无 body 不可分——选择不猜、给通用失败文案，而非蒙一个可能错的状态（契约测试已钉死该行为）。
6. 未跑全库测试（资源纪律：定向回归 + 路由装配冒烟已覆盖改动可达面）；未起模拟器/Gradle/浏览器。
7. 全量 build_runner 曾连带漂移 7 个存量 .g.dart（statistics/notification/focus/task 域 codegen 版本差），与本卡无关，已逐一 `git checkout --` 回退并复核 `git status`——最终代码 diff 仅含本卡文件面。

## ⑥ 收工核查

- [x] `mobile/build`、`mobile/.dart_tool`：已删（见下）
- [x] `/tmp` 本卡产物：基线验证克隆 `/tmp/wt165-verify-baseline` 已删；无其他 /tmp 产物
- [x] 无模拟器/Gradle/浏览器 HEAVY 操作；flutter test 全程 `--concurrency=1`、单批 ≤3 文件
- [x] 零 commit / 零 push / 零凭据；主仓只读未触碰
- [x] 新 UI 全令牌消费，双守卫 ratchet PASS；l10n 双守卫 PASS
- [x] patch 在基线克隆 `git apply --check` 干净通过
