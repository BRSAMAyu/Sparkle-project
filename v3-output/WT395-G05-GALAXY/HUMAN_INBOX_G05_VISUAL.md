# G-05 真机段视觉/FPS 清单（转 HUMAN_INBOX，不伪造截图/FPS）

- 构建 SHA8：提交后见 `git rev-parse --short=8 HEAD`（分支 wt395-g05-galaxy，base 60366592）
- 依据：U-09 SCREENSHOT_MATRIX（`v3-output/U-09/SCREENSHOT_MATRIX.md`）galaxy 行 + 本卡 headless 段结论
- 采集前置：真实后端（gateway/engine 常驻栈可用）与真实账号（demo_data），galaxy 允许 dark cosmic

## A. 真机截图矩阵（U-09 galaxy 行，5 张）

| # | surface | state | persona | platform | viewport | 采集入口 | 断言点 |
|---|---------|-------|---------|----------|----------|----------|--------|
| 1 | galaxy | tree_expanded | demo_data | android | 1080x2400@3.0 | galaxy Tab → 等待节点树渲染后展开演示节点 | 核心层级结构/文案/状态语义；节点卡片无重叠遮挡；选中高亮可见 |
| 2 | galaxy | tree_expanded | demo_data | web | 1280x720@1.0 | 同上 | 同上 |
| 3 | galaxy | tree_expanded | demo_data | web | 360x720@1.0 | 同上 | 同上 + 窄屏无 overflow |
| 4 | galaxy | tree_expanded | demo_data | macos | 800x600@2.0 | 同上 | 同上 |
| 5 | galaxy | tree_expanded | demo_data | macos | 1280x800@2.0 | 同上 | 同上 |

命名模板：`galaxy__tree_expanded__demo_data__<platform>__<viewport>__<SHA8>.png`（B-04 naming.py 注册表，含 macos 段）。

## B. 真机 FPS/latency 口径（headless 段的替代闭环）

headless 段已交付（`flutter test test/features/galaxy/performance/g05_galaxy_frame_budget_test.dart`，逐帧 Stopwatch p50/p95）：

| scale | 拖拽帧 p50/p95/avg（headless VM） | 结论 |
|---|---|---|
| 50 | 见 v3-output/WT395-G05-GALAXY/raw_frame_budget.md | 全部 <50ms 红线 |
| 500 | 同上 | 全部 <50ms 红线 |
| 5000 | 同上 | avg <50ms；p95 <160ms VM 余量 |

真机段需补测（无设备→人工执行，DevTools Performance 页）：

- [ ] Android 真机（或模拟器 1080x2400@3.0）：Galaxy 页 50/500 节点拖拽/捏合滑动 FPS（目标 ≥55fps 交互档；large 图走 LOD 降级后无卡死）
- [ ] macOS：同上，桌面口径
- [ ] Web (Chrome)：同上，canvas/shader 降级路径是否 graceful（shader 不可用回退静态背景）
- [ ] 断网重连：galaxy 页断网→恢复，验证 EnhancedGalaxyRepository stale-cache 回退提示 + 数据一致性（headless 段已实证服务面零丢失）

## C. headless 段已覆盖、无需人工复验的项

- A/B 渲染契约：状态管线 11 相位三端指纹一致（U-09 C1 继承，本 base 未触碰状态管线）
- 交互正确性：缩放五级 LOD/选择边展开/空间索引命中/手势钳制/力引擎局部性（`g05_galaxy_interaction_scale_test.dart` 7/7 绿，headless 可复跑）
- 核心操作 overlap：拖拽热路径逐帧泵入零 overflow 异常（flutter_test 溢出即抛），真实 renderer 帧内零重叠断言由 painter 单pass 绘制保证
