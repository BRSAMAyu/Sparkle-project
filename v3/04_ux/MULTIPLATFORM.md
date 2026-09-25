# Multi-platform Quality

## Android
至少 1080×2400 4GB+ AVD；键盘、手势条、飞行模式、resume、后台/前台切换。

## Web
1280×720 + mobile-like width；路由 URL、刷新恢复、鼠标真实点击、键盘、semantics、network throttle。

## macOS
小窗口/正常窗口；Keychain/session；鼠标/键盘；重启恢复。

## Diff
同一 golden state 截图命名一致，允许平台 native 差异；核心层级/文案/状态语义必须一致。

## 允许差异登记（U-09 起权威；新增平台分支必须在此登记 reason）

机器可读同步件：`mobile/test/shared/canonical_state_fixture.dart` 的
`platformDivergences`（契约测试 C7 钉「逐条有 reason」，两处需同步维护）。

| 差异点 | 涉及平台 | reason |
|--------|----------|--------|
| 导航转场 `pageTransitionsTheme`（iOS=Cupertino，其余交付端=FadeForwards，fuchsia=框架默认） | 全端 | iOS 边缘滑返手势是系统能力，不为一致而砍平台能力；fuchsia 非交付目标 |
| 触觉/音频后端（`sensory_feedback_service`/`bgm_service`） | 桌面/web 静默降级 | 触觉是移动硬件能力，桌面/web 无对应硬件约定 |
| API/WS 默认主机（android=10.0.2.2 模拟器宿主别名，其余=localhost） | android | 模拟器访问宿主服务必须走别名；dart-define 覆盖时三端一致 |
| token 存储后端（io=Keystore/Keychain，web=localStorage） | web | secure storage web 并发写静默丢失实证（web-round1 W-1/W-2）；竞赛口径可接受，生产升级路径见 `token_storage_web.dart` 头注释 |
| 键盘 IME 动作按钮视觉 | android/iOS | 系统渲染；行为契约（textInputAction=send + onSubmitted 真发送）由 U-09 契约测试 C5 三端钉死，不随平台漂移 |
| enter-to-send 默认值 | 全端一致 | 是用户偏好（设置项持久化）而非平台分支——三端默认同开，偏好关闭三端同回落 newline |

## headless 契约测试与真机截图矩阵的分界（U-09 两段交付）

- **headless 段（已交付）**：`mobile/test/widget/u09_platform_render_contract_test.dart`
  ——同一 canonical state（U-06 SurfacePhase + dashboard harness 的
  persona/goal/task 样本）在 android/iOS/macOS 目标与 MULTIPLATFORM
  viewport 下断言渲染指纹逐字一致、URL/session/keyboard 契约同源、
  布局零 overflow。
- **真机段（HUMAN_INBOX+主会话）**：`scripts/devtools/visual_baseline/`
  `matrix` 子命令生成 45 行采集清单（v3-output/U-09/SCREENSHOT_MATRIX.md），
  `report-template` 输出 diff report 模板（v3-output/U-09/DIFF_REPORT.md）；
  真实浏览器/AVD 截图不伪造，采集后走既有 `manifest/verify/diff` 链。
