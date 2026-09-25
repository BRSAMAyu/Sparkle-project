# WT401 Q-03 — Autonomous Visual QA 最终波 REPORT

- worker/卡：wt401 / Q-03（stream QUALITY，HEAVY，gate V3-7，lock visual-baseline）
- base SHA：`61af0f0a`；分支：`wt401-q03-visualqa`（final SHA=本文件所在提交）
- 渲染方式：flutter test 泵**真实 GoRouter**（配方同 `test/app/router_smoke_test.dart`：
  demo mode + 真 auth/onboarding harness + Isar/Hive 临时目录），standard 档
  （StimulationLevel.standard 默认主题，无 low 档 override——双刺激档属 wt399/U-02），
  390×844@2x；`matchesGoldenFile(--update-goldens)` 落盘，**无 mock 语义**：空/错/加载态
  由真实 Notifier 状态与真实加载时序产生（fixture 文案允许）。chat 态由 fixture 驱动，
  依赖 V3-FIX-53（wt400）但不阻塞、已登记。
- 证据环境补齐（均为测试侧，产品零改动）：MaterialIcons/Roboto/Arial Unicode 三字体
  注册（flutter_tester 无平台字体，中文/图标否则 tofu）、audio/local_notifications/
  connectivity/path_provider 平台通道 mock、debug banner 关闭。

## 覆盖

- 路由表叶子 ~102；截图 **107 张 PNG**（核心 13 屏 19 态 + long-tail 85 屏 + 参数屏
  unknown-id 缺数据态），清单见 `screens.md`。
- 每屏同步程序化探针：RenderFlex 溢出异常 / RenderParagraph 截断候选（box vs text
  extent）/ 越界 widget / WCAG 对比度采样 → `layout_probe_*.json`、`contrast_probe_core.json`。
- **修复后 107/107 零 pump 异常**（修复前 5 屏异常：L40/41/42/48/60）。

## 12 维打分汇总

- 核心 13 屏（C01–C13）：修复后全 2 分，**A/B=0** ✅（逐屏表 `rubric_scores.md` §一）
- Long-tail 85 屏：A=0 ✅；B=0（修复后）；遗留 C 共 7 项（对比度 4、截断观察 2、
  density 1）——`rubric_scores.md` §二
- 计数（修复前→修复后）：A 1→0（L60 溢出+chip 不可达）；B 3→0（G2 ticker、
  G3 覆盖层竞态、G4 星图顶部遮挡）

## 修复清单（红→绿，守卫 `mobile/test/goldens/q03_visual_qa/q03_layout_fix_guards_test.dart`）

| # | 文件 | 缺陷（级别） | 红（base 实测） | 绿 |
|---|------|-------------|----------------|-----|
| G1 | `lib/features/community/presentation/screens/create_post_screen.dart` | 心情条 390w 溢出 66px、第 5 chip 不可达（A） | `RenderFlex overflowed by 66 pixels` | ✅ + `compare/L60_post_create_side_by_side.png` |
| G2 | `lib/features/achievement/presentation/screens/streak_details_screen.dart` | 今日格单 ticker mixin 建双 controller（B） | `SingleTickerProviderStateMixin but multiple tickers` | ✅ |
| G3 | `lib/core/services/share_poster_service.dart` | 生成窗口期离开源页→失活 context 调 Theme.of→根覆盖层整屏红（B；L40/41/42 三屏证据） | `Looking up a deactivated widget's ancestor is unsafe` | ✅ + `compare/L4{0,1,2}_*_side_by_side.png` |
| G4 | `lib/features/galaxy/presentation/screens/galaxy_screen.dart` | 星图模式面板（top:112 兄弟 Positioned）被 top:48 统计列内容压住（B；rect 112–154 vs 128–244） | G4 交叠断言红 | ✅ + `compare/C02_galaxy_side_by_side.png` |

产品 diff 最小化（4 文件 40+/25-，无整文件重排）；`git checkout` 回退过一次
dart-format 全文件重排与 l10n 意外再生成的漂移。

## before/after 对照

- 成对文件：`compare/{stem}_before.png` / `{stem}_after.png`（6 组：C02_galaxy、
  L60_post_create、L48_streak_details、L40/41/42）
- 并排合成：`compare/{stem}_side_by_side.png`（1364×1514，左 before 右 after）

## 质量门

- `flutter analyze` 全量：base **601** = 改后 **601**，error 0；4 个产品文件仅
  既有 3 条 info（prefer_foreach/cascade_invocations/use_named_constants，base 同在），
  **棘轮零新增** ✅
- `flutter test test/goldens/q03_visual_qa/`：26/26 绿（含守卫 4/4；capture 模式
  `Q03_VISUAL_CAPTURE=true --update-goldens` 亦 26/26）✅
- 邻域：galaxy widget+unit（123）、`poster_studio_regression_test`、
  `router_smoke_test` + `main_actions_smoke_test`（17）全绿 ✅
- 断言零删改；无 mock 冒充（状态全由真实 Notifier/加载时序产生）✅

## DYNAMIC_ISSUES 新增号段

- **V3-FIX-59（P2）**：连胜概览文案窗矛盾「过去7天你有70天完成了任务」（L48 截图）
- **V3-FIX-60（P3）**：星图右缘工具栏与草稿卡「现在审核」CTA 部分重叠（先于本卡存在）
- 占用号段：57–58（49–56 既有）

## DEFERRED（后续卡/裁决项）

1. V3-FIX-59/58 修复（见上）。
2. C02 首访三张信息层（草稿卡/贡献横幅/统计）合并或降层的设计裁决（density 1 分）。
3. C 级对比度打磨：chat 时间戳 3.08、plans「75 分钟」2.50、login 品牌字 4.28、
   profile 折叠区「普通」1.74。
4. 双刺激档（low stimulation）全屏对比属 wt399/U-02，本卡未触碰。
5. group/private chat、执行类参数屏（/tasks/:id/execute 等）需真实后端会话/实体，
   登记为 backend-gated（screens.md §C），非本卡 headless 可达面。
6. emoji 字体在 flutter_tester 不可加载（环境限制）：涉及标题处黑块属证据环境
   现象，真机无此问题。
