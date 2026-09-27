# WT729-GOV015 notes — GOV-015 孤儿屏（你的控制权三死 tile）处置

- Agent: wt729（node-b；主线仓库只读，本分支 `agent/node-b/wt729/gov015`，base main@e85eec52）
- 日期: 2026-09-27
- 任务来源: wt714 HUNT2 未成立清单 §3.1 留档卫生项（V3-FIX-440）
- 目标: `mobile/lib/features/settings/presentation/screens/data_usage_dashboard_screen.dart`（GOV-015 注释：统一透明度数据使用面板；207 行）

## 1. 裁决：处置 A（外科整链删除）

### 亲证零可达（e85eec52 基线，删前实录）

wt714 定位复核成立，四向独立 grep 全部归零（不依赖 wt714 结论、全部本机重跑）：

1. **类名**：`DataUsageDashboardScreen` 于 mobile/lib 仅 `data_usage_dashboard_screen.dart:6/:7` 自身定义 2 命中；test/ 0 命中。
2. **路由串**：`data_usage_dashboard` / `dataUsageDashboard` / `data-usage` 于 lib+test+integration_test 0 命中（routes 家族 20 个文件与 app_link_router_service 均无 datausage 字样）。
3. **l10n 消费者**：32 个 `dataUsage*` 键除屏自身 + l10n 五件套（arb×2+gen×3）外全仓零消费者。
4. **测试字面量**：「你的数据与隐私 / Your Data & Privacy / 你的控制权 / Your Controls / DataUsageDashboard」于 test/+integration_test/ 0 命中。

### 反证保留动机（为何不走选项 B 接线）

- docs/ 全仓 grep `GOV-015` 0 命中、`数据使用` 无该屏相关设计要求——**无设计文档要求保留**（GOV-015 仅存于屏注释自身与 wt714 notes）。
- 数据控制权承诺语义已有真身：`SettingsDataControlsCard`（settings_behavior_explanation.dart:202 起，export/delete/hide 全接线），挂载于统一设置 `unified_settings_screen.dart:2050`——用户可达且行为真实，删除孤儿屏不损失任何数据控制能力。
- 选项 B（挂路由+入口）实质是把一个「三控制 tile 均无 onTap」的承诺失效面接入用户可达路径——正好制造 wt714 猎场④（按钮死路）新受骗面，与 GOV-015 原意（诚实透明）相反。否决。

## 2. 删除内容（纯删 655 行 0 增）

| 文件 | 动作 |
|---|---|
| `mobile/lib/features/settings/presentation/screens/data_usage_dashboard_screen.dart` | 整文件删除（207 行，含 `_SectionHeader`/`_DataCard`/`_ControlTile` 三个死 tile 子件） |
| `mobile/lib/l10n/app_zh.arb` | 删 32 个 dataUsage 键值行（原 12741-12772 连续块） |
| `mobile/lib/l10n/app_en.arb` | 删 32 个 dataUsage 键值行（原 12724-12755 连续块） |
| `mobile/lib/l10n/app_localizations.dart` | 手改同步删 32 块（每块 doc echo 5 行 + getter 1 行 + 尾随空行，共 192 行） |
| `mobile/lib/l10n/app_localizations_zh.dart` | 手改同步删 32 块（@override+getter+空行，96 行） |
| `mobile/lib/l10n/app_localizations_en.dart` | 手改同步删 32 块（@override+getter+空行，96 行） |

gen 手改按 wt363/wt710/wt717/wt724/wt725 判例（gen-l10n 重生成会引入 intl 格式漂移全量噪声，弃用产物、手改与 arb 逐值同步）。无 `@dataUsage*` 元数据键需删。不在 49 冻结键（aurora*19+visual*30 前缀不相交）。

## 3. 红先行/证据

- **删前在位实录**：`grep -c dataUsage` → app_zh.arb 32、app_en.arb 32、app_localizations.dart 64（doc echo 含键名 2 次/键）、zh/en gen 各 32；屏文件在位 207 行（见 §1 四向 grep）。
- **删后归零**：`dataUsage` 与 `DataUsageDashboardScreen`/`data_usage_dashboard` 于 mobile lib+test+integration_test 全部 0 命中；arb JSON 解析合法，zh=en=10054 键对称零差集（wt725 基线 10086 口径 -32，账目吻合）。
- diff 实测：6 files changed, 655 deletions(-), 0 insertions(+)。

## 4. 验证（全部真实运行）

- `flutter analyze`：**No issues found!**（24.8s）
- L10N-REGEN-PARITY：**OK 10054 template keys == abstract members; zh/en subclasses complete**
- i18n-coverage：**PASS — all presentation files with Chinese strings import i18n infrastructure**
- 受影响/邻域测试（删前 grep 亲证测试零钉值零引用，选 settings 邻域 + l10n 面 6 文件）：unified_settings_bgm + unified_settings_no_fake_confirm + settings_provider + chat_settings + wt422_l10n_harvest_smoke + i18n_service —— **22 用例全绿（All tests passed!）**
- 台账 verify：`python3 scripts/devtools/ledger_union_merge.py --verify v3/06_agent_fleet/DYNAMIC_ISSUES.md` → **verify 通过**：312 行 V3-FIX 行，裸管分布 {8: 312}，零冲突标记残留，ID 无重号，状态枚举合法，零 FAIL。

## 5. 台账

- 登记 **V3-FIX-440**（P4），状态 FIXED@b06f972a。
- 号段亲证：落号前 grep 台账 V3-FIX-440/441/442 全 0 行（e85eec52 快照均空闲）；任务书提示「441 已被 wt728 预占」在当前 main 快照未见落地（wt728 预占若在 coordination 分支未合入，与本次 440 无号冲突），按任务书首选 440 落号。

## 6. 产出与提交

- 代码提交：`b06f972a` fix(V3-FIX-440)——6 文件纯删 655 行。
- 台账+notes 提交：见本分支后续 docs(fleet) 提交。未 push（铁律）。
