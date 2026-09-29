# FIX-566 · limitations（诚实登记）

## L1 环境格式器代差下的 gen 产物处置（需 owner 复核）
本机仅有一套 Flutter（3.41.3 homebrew，dart_style tall-style）；对 main 裸跑
`flutter gen-l10n` 即对既有 gen 产物产生 144+/50− 纯格式重排（多机车队入库 gen
产物出自旧格式器机器，U07/U13 的「gen-l10n 零漂移」在该机成立、本机不可复现为
零 diff）。处置：gen 产物恢复 HEAD 后按本机再生输出摘取**纯增量**三处入库，并以
脚本断言入库文件与完整再生输出的键集合逐文件相等（3/3）+ arb 中英键集合相等
（10267=10267）。**键级零漂移成立；行级零漂移在本机不可判**。若 R1 审查会话所在
机器格式器与入库一致，可直接 `flutter gen-l10n && git status` 复验零漂移。

## L2 环境性测试面收缩（①正的失败态经播种而非真实 send 流）
真实「send→ErrorEvent 失败→错误横幅渲染→点重试」全链 widget 测在本机稳定挂死
（错误横幅渲染帧等待不可达真实事件，process 级 sample 佐证 isolate 空等；
10.0.2.2:8080 在本机为黑洞路由，通道内真实 socket 与 fake-async 交错）。处置分两层：
- **provider 侧**（reuse 真语义，chat_provider.dart:1049/2334/2349）：纯 `test()`
  真实 send→ErrorEvent→`retryLastMessage()`→不追加重复用户消息+新 run 开启
  （chat_f566_retry_reuse_path_test.dart，确定性绿）；
- **screen 侧**（本卡差量所在）：失败态经 `seedRetryableFailure()` 播种（复用
  ChatState 既有 copyWith 字段，非 mock 通道），钉「点重试 → force 回最新端」。
  mutation M-① 证明该钉对本卡差量有牙（去 force 即红 580.0≠0.0）。
残余风险：播种态与真实失败态在**错误横幅渲染**上等价性未独立验证（真实流挂死
无法对照）；横幅渲染行为非本卡改动面（`SparkleExitTransition` 零 diff）。

## L3 ②入口样式为最小实现，视觉终审归 Q05
「跳最新」入口按台账「微卡+最小实现」落地：单行胶囊（图标+双语文案，DS 令牌，
`DS.surfaceOverlay`+`DS.borderSubtle` 系），无出场动画、无未读计数、无长按态。
UI-TOKENS 棘轮 PASS（color=225/275、fontSize=632/727 零新增硬编码）。Q05 视觉
审查可裁决必要性/形制；如需改动仅涉 chat_screen.dart 单 Positioned 块。

## L4 OVERLAY-SMALL 叠放让位为静态偏移
compact-short 面悬浮预测 dock 在场时入口 `bottom: 64`（dock 高度经验值）而非
测量对齐；两者同屏时入口恒在 dock 上方 12dp 间距档。极端字体缩放下未做
200% 面验证（U07 缩放套件覆盖的是 Markdown 气泡面）。

## L5 `_showJumpToLatest` 为 Stateful 同步位而非独立可观察
入口可见性 = `!_scrollAnchor.shouldFollow` 的帧级镜像（`_handleScroll` 翻转帧
setState）。锚本身未暴露通知流（遵循 U07「纯阈值判定、无第二套状态机」裁决），
故可见性与锚的一致性由同函数内先后两行保证；未来若锚改为多观察者，需同步改造
该镜像点。
