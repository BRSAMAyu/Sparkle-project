# PHOTON-CALIBRATION · 光子兑 Pro 汇率校准报告（3000→1500）

> D 纵队 Worker 交付 · worktree wt169（基线 f09f9d57）· 2026-09-22
> 主会话裁决落地：`PHOTON_REDEEM_PRO_COST` 3000→1500；DAYS=7、MONTHLY_CAP=1 维持不变。

## 0. 裁决依据（TOUR 纵队实测）

TOUR 活栈全旅程实测：诚实日均光子收入 **30-80**，旧价 3000 → 兑 Pro 需约 **100 天**，实际无人可达——「学出会员」形同虚设。新价 **1500 ≈ 强投入月（25 天 × 60 均值）可达**；休闲刷分不可达——正是「学出」的语义边界。符合 FLEET-BRIEF 价值增量红线：免费闭环行为零变化，光子只经「学出会员」出口变现。

## ① 改动清单（5 文件，+31/-23）

| 文件 | 改动 |
|---|---|
| `backend/app/config/settings.py` | `PHOTON_REDEEM_PRO_COST: int = 3000 → 1500`；注释块更新：TOUR 实测依据（日均 30-80）、「学出」语义边界、下次校准数据钩子 |
| `backend/tests/unit/test_dcomm2_photon_redeem_pro.py` | `COST = 3000` → `COST = settings.PHOTON_REDEEM_PRO_COST`（读部署值）；`_grant_ledger(db, user, 3000, …)` 字面量 → `COST`；基数断言与 monkeypatch 值 2500 → `COST - 500`（校准无关化）；注释「基数仍 3000」→「基数仍 COST」 |
| `backend/tests/northstar_eval/feature_tour.py` | 镜像常量 `REDEEM_PRO_COST = 3000 → 1500`（本模块是消费面，不 import 产品代码，只能镜像）；S8 两处硬编码 "3000" 文案 → 插值 `{REDEEM_PRO_COST}`（`EARN_TARGET = REDEEM_PRO_COST + 200` 自动随动 1700） |
| `mobile/lib/features/photon/data/models/photon_redeem_pro_model.dart` | 兜底展示常量 `photonRedeemProDisplayCost = 3000 → 1500`；doc 注释由【待产品校准】改为登记本次校准依据 |
| `mobile/test/features/photon/presentation/screens/photon_redeem_pro_screen_test.dart` | 兜底相关断言改为引用常量（见②）；mock 服务端回显值 3000→1500 且派生值随之校正（balance_after 2200→3700 = 5200-1500，保持 mock 内部自洽；insufficient_base 用例基数 1200 / 转账差额 4000 语义不变） |

**不改（申报）**：l10n arb 无 3000 字面量（确认对话框为参数化消息 `photonRedeemProConfirmContent(cost, days)`，数值由屏内常量注入）——零改动；`backend/app/data/shop_seeds.py` 的 `price_photons=3000` 是商城传说皮肤定价，与兑换汇率无关——不动；`test_photon_stream_audit_ledger.py` 的 `monkeypatch.setattr(…, 60)` 本就自设值、与部署值解耦——不动；DAYS=7 / MONTHLY_CAP=1 照裁决维持。

## ② 测试改常量引用的防再改论证

**引擎侧（test_dcomm2）**：`COST` 由字面量 `3000` 改为模块加载时读 `settings.PHOTON_REDEEM_PRO_COST`。下一次校准只改 settings 一处，本测试族 11 例零改动全绿。三条派生面全部去字面量化：

- 授予额：`_grant_ledger(db, user, COST)`（原硬编码 3000）；
- 「净值恰可兑」用例：断言 `== COST - 500`、monkeypatch 目标 `COST - 500`——原实现把断言钉在 2500、monkeypatch 也钉 2500，本质是「测试本地算术（grant-deduct）+ 校准值」两层耦合；改后测试本地算术不变（COST-500），校准值维度彻底退出，用例语义从「价格为 2500 时可兑」升华为「价格=净值时可兑」，对任何 COST 取值成立；
- 全族其余断言均经 `COST` 相对表达（`COST*2`、`COST*8-COST`、`-COST`），本就校准无关。

**mobile 侧（screen test）**：动作前展示 = `_lastResult?.costPhotons ?? photonRedeemProDisplayCost`（屏内逻辑），故未兑换前 `find.text('3000')` 与确认对话框 `'3000 光子'` 断言的是**兜底常量**而非服务端值——已改为 `find.text('$photonRedeemProDisplayCost')` / `find.textContaining('${photonRedeemProDisplayCost} 光子')`，下次改兜底常量测试零改动。服务端回显 mock（`cost_photons` / `costPhotons`）保持独立字面量（1500）：契约解析面测的是「服务端说什么就是什么」，不应绑定本地常量；取新部署值仅为本文件经济口径叙述自洽。

## ③ 冲突面声明

- **wt166（intake）/ wt167（mobile 小队系）**：本卡不触 intake、社区/小队任何文件，零重叠。
- **wt168（photon status 端点）**：同在 photon 域，已做隔离设计——本卡只改 `settings.py` 常量行+注释（wt168 不改 settings）、测试两个文件、mobile model+test；**不触** `backend/app/api/v1/photons.py` 与 `photon_redeem_service.py`（status 端点落点），与其改动文件零重叠预期成立。若 wt168 给 status 端点带上部署值回显，mobile 兜底常量的「服务端值优先」逻辑（`?? photonRedeemProDisplayCost`）天然消费之，无需本卡跟进。
- **TOUR 纵队交付物**：`feature_tour.py` 为活栈探针脚本（消费面镜像常量），与 TOUR 已产报告（v3-output/TOUR/）为读-写分离，不冲突。

## ④ 回归验证（全绿）

| 族 | 结果 |
|---|---|
| D-COMM-2（`test_dcomm2_photon_redeem_pro.py`） | **11/11 passed** |
| PHOTON-STREAM（`test_photon_stream_audit_ledger.py`） | **7/7 passed**（任务卡计 6 例 + 基线已含 TOUR 回归钉 VARCHAR50 共 7，如实申报） |
| photon 域定向（+`test_photon_service.py` 12、`test_photon_service_simple.py` 6、`test_d02_photon_spine.py` 4） | **40/40 passed**（sqlite 内存库，`DATABASE_URL=sqlite+aiosqlite:///:memory: SECRET_KEY=test`，18.9s） |
| mobile 兑换屏（`photon_redeem_pro_screen_test.dart`） | **8/8 passed**（--concurrency=1 串行） |
| mobile photon 域（repository 12 + provider 17） | **29/29 passed**（串行第二批 ≤3 文件/批） |

环境备注：worktree 无 `mobile/lib/gen/`（gitignore 产物，基线不含）——用本仓 buf 工具链 `buf generate --template buf.gen.dart.yaml` 现场再生后 flutter test 可跑；属构建产物，收工已清（见⑤）。

## ⑤ 下次校准的数据钩子（登记）

1. **status 端点上线后**（wt168 合入）：`GET /photons/*status*` 可观测真实「可兑换基数 / 余额 / 兑换渗透」分布，替代 TOUR 单用户 30-80 的采样口径；
2. **30 天窗口复议**：观察指标——(a) 月度兑换渗透率（redeem_pro 流水户数/活跃户数）；(b) 达标时长分布（首笔合同/首胜/成就收入累计到 1500 的天数）；(c) 强投入 vs 休闲用户达成比。若强投入用户 <50% 可达 → 下调；若休闲刷分面出现可达路径 → 收紧收入词表而非涨价；
3. **数据落点**：审计流水 `photon_transaction_history`（`transaction_type IN (grant_contract, grant_daily_first, grant_achievement, grant_combo…)`）本就是可兑换基数真源，status 端点聚合后即可直接出分布报表，无需新埋点。

## ⑥ 诚实申报

- 工作机无本仓 venv，用系统 python3.11（homebrew，依赖齐备）跑 pytest；非项目标准 uv 环境，但 40 例全绿、无 skip/warning 异常。
- `flutter pub get` 报 2 个 discontinued 包、若干版本滞后——基线固有状态，未动 pubspec。
- mobile `lib/gen` 为现场再生的 gitignore 构建产物，未入 patch。
- 未跑全库后端测试（遵守「定向测试绝不宽扫描」资源纪律）；未跑 flutter analyze（非本卡范围，兑换屏测试编译通过即覆盖所改文件语法面）。
- 未 commit / 未 push（纪律）；零凭据。

## ⑦ 收工核查

- [x] worktree 改动仅 5 个目标文件（`git status --short` 核对，无 untracked 泄漏）
- [x] `mobile/build`、`.dart_tool`、`mobile/lib/gen`（现场再生产物）、`.pytest_cache` 已清
- [x] 无独立端口进程遗留（本卡未起服务；未用模拟器/浏览器——LIGHT 任务）
- [x] /tmp 无本卡产物（pytest tmp_path 系统临时目录随系统回收）
- [x] 交付物：`v3-output/PHOTON-CALIBRATION/REPORT.md` + `changes.patch`（5 文件 +31/-23）
