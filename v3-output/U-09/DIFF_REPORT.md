# U-09 三端 Diff Report（真机批次填写）

- 构建 SHA：`<BUILD_SHA>`（base `<BASE_SHA>` → final `<FINAL_SHA>`）
- 采集环境：gateway `<GATEWAY_URL>` / engine `<ENGINE_URL>`
- 执行人/日期：`<EXECUTOR>` / `<DATE>`
- 断言底线（MULTIPLATFORM.md）：核心层级/文案/状态语义必须一致；
  允许平台 native 差异（逐条 reason 见下）。

## 逐状态比对

对每张截图对（Android vs Web vs macOS）填写：

```
| SURFACE | STATE | PLATFORM | 结论(一致/A-B issue) | 证据文件 |
|---------|-------|----------|----------------------|----------|
| <SURFACE> | <STATE> | <PLATFORM> | <一致 or issue#> | <png 名> |
```

### A/B visual issue 记录（有则逐条）

```
issue-<N>: platform=<PLATFORM> surface=<SURFACE> state=<STATE>
现象：<一句话>
层级/文案/状态语义哪一类：<层级|文案|状态语义|布局 overflow|交互语义>
截图：<android png> vs <macos/web png>
```

## 允许差异（预登记，逐条 reason；新增差异必须补 reason 后方可放行）

| 差异点 | 涉及平台 | reason |
|--------|----------|--------|
| 导航转场（iOS=Cupertino/其余=FadeForwards） | 全端 | 平台导航手势约定，不砍平台能力 |
| 触觉/音频后端 | 桌面/web 降级 | 移动硬件能力，桌面/web 无硬件约定 |
| API 默认主机（android=10.0.2.2） | android | 模拟器宿主回环别名，dart-define 可一致 |
| token 存储后端（web=localStorage） | web | secure storage web 并发写丢失实证（W-1/W-2），竞赛口径可接受 |
| IME 动作按钮视觉 | android/iOS | 系统渲染；行为契约（send 语义）已由契约测试钉住 |

## 提交物

- [ ] screenshot 全集（命名合规，`visual_baseline.py verify` 通过）
- [ ] manifest.json（--build-sha/--platform/--viewport 逐端）
- [ ] 本 report 填写完成，A/B issue 有 ledger 归属
