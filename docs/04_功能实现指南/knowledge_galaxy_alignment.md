# 知识星图全局对齐文档

更新时间：2026-03-09

## 1. 文档目的
这份文档对齐当前仓库里“知识星图”已经落地的真实状态，用于后续继续迭代时快速接手。

它回答 4 个问题：

1. 当前星图到底已经完成到什么程度
2. 现在真正生效的架构骨架是什么
3. 哪些旧文件已经废弃或被替换
4. 后续再做增强时，哪些约束不能破

这不是规划稿，是基于当前代码的工程现状文档。

---

## 2. 当前总状态

### 2.1 结论
知识星图已经从“需要推倒重做的原型”进入“可持续迭代的产品骨架”。

当前核心能力已经具备：

- 自定义相机，零漂移缩放
- 原始指针手势状态机
- 空间索引与视口裁剪
- 5 级 LOD
- 节点点击、长按预览、拖拽与坐标持久化
- 搜索定位
- 小地图导航
- 入场动画
- Build replay 相机巡航
- 边线粒子流动
- 节点成就反馈
- 玻璃质感控件栏
- 概览统计条
- 深浅色模式
- 性能降级安全阀

### 2.2 现在的主设计原则

1. `GalaxyCamera` 是唯一坐标转换真源
2. `GalaxyGestureHandler` 只发命令，不改任何 UI 状态
3. `GalaxyScreen` 负责状态编排、动画时序、缓存持有
4. `StarMapPainter` 只做纯渲染，不持有业务状态
5. 所有新增视觉效果都必须接受性能降级开关

---

## 3. 阶段完成情况

| 阶段 | 状态 | 结果 |
|---|---|---|
| Phase 1 骨骼层 | 已完成 | 自定义相机、原始指针手势、单一 painter |
| Phase 2 性能层 | 已完成 | Grid 空间索引、LOD、预算制、边缓存、标签缓存 |
| Phase 3 交互层 | 已完成 | tap 进详情、long press 预览、节点拖拽、坐标持久化 |
| Phase 4 视觉层 | 已完成 | 背景、扇区雾气、节点分级、关系边样式、标签精修 |
| Phase A 视觉品质升级 | 已完成 | 三层星空、扇区氛围、节点恒星质感、边线渐变与箭头 |
| Phase B 交互完整性 | 已完成 | 双击聚焦、搜索、mini-map、入场动画、增强预览卡 |
| Phase C 动效升级 | 已完成 | replay 相机跟踪、边粒子、成就动画、空闲微漂移 |
| Phase D UI 打磨 | 已完成 | 控件栏重设计、状态页升级、主题切换淡入、统计条、触觉反馈 |
| Phase E 清理与保障 | 已完成 | 死文件清理、性能监控、关键单测补齐 |

---

## 4. 当前生效架构

### 4.1 主页面
文件：

- [galaxy_screen.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/screens/galaxy_screen.dart)

当前职责：

- 图数据加载与刷新
- 相机动画、回放动画、入场动画
- 触觉反馈
- 搜索、小地图、预览卡、统计条等 overlay 编排
- 物理引擎驱动与拖拽释放收尾
- 性能降级监控
- painter 需要的全部纯渲染参数组装

说明：

- 当前 `GalaxyScreen` 仍然偏重，但状态边界已经清楚。
- `galaxy_provider.dart` 不再是当前主渲染链路的一部分；它仍保留给旧导出和旧测试，不参与这条新骨架。

### 4.2 相机
文件：

- [galaxy_camera.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/widgets/galaxy/galaxy_camera.dart)

当前职责：

- `screenToWorld`
- `worldToScreen`
- `applyPan`
- `applyZoom`
- `centerOnWorldPoint`
- `fitRect`

说明：

- 缩放锚点公式仍是零漂移数学公式。
- 所有命中测试和绘制转换都统一走这层。

### 4.3 手势层
文件：

- [galaxy_gesture_handler.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/widgets/galaxy/galaxy_gesture_handler.dart)

当前命令：

- `PanCommand`
- `ZoomCommand`
- `TapCommand`
- `DoubleTapCommand`
- `LongPressCommand`
- `DragNodeCommand`
- `FlingCommand`

说明：

- tap 与 double tap 已做延迟互斥
- long press 与 drag 已做消岐
- `DragNodeCommand` 仍只传屏幕 delta，世界坐标换算在 `GalaxyScreen`

### 4.4 渲染层
文件：

- [star_map_painter.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/widgets/galaxy/star_map_painter.dart)

当前职责：

- 背景、扇区、边、节点、标签统一绘制
- LOD 切换
- 节点/边预算制
- 关系聚焦与搜索 dimming
- 边缓存、标签缓存接入
- 粒子、庆祝态、空闲微漂移等状态的纯渲染消费

关键缓存：

- `GalaxyEdgePictureCache`
- `GalaxyLabelCache`

当前没有在 painter 内持有动画状态。

### 4.5 空间索引
文件：

- [galaxy_spatial_index.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/data/services/galaxy_spatial_index.dart)

当前实现：

- Grid 索引
- `cellSize = 200`
- 支持 `queryRect`
- 支持 `queryNearest`

### 4.6 物理与回弹
文件：

- [galaxy_force_engine.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/data/services/galaxy_force_engine.dart)

当前能力：

- 拖拽时 anchor neighborhood
- 松手后 release + settle
- 邻域弹簧与排斥
- 视口外减弱

### 4.7 业务数据层
文件：

- [enhanced_galaxy_repository.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/data/repositories/enhanced_galaxy_repository.dart)
- [galaxy_model.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/shared/entities/galaxy_model.dart)

保留原因：

- 图数据获取稳定
- 节点详情链路稳定
- 节点坐标回写稳定
- Demo 模式已打通

---

## 5. 当前交互能力

### 5.1 基础导航

- 单指拖拽平移
- 双指缩放
- fling 惯性减速
- 双击空白快速聚焦 / 全景切换
- 双击节点聚焦该节点

### 5.2 节点交互

- 单击节点：tap 回弹后进入详情页
- 单击空白：取消选中和关系聚焦
- 长按节点：弹预览卡
- 长按后移动：进入节点拖拽
- 拖拽结束：异步回写坐标

### 5.3 搜索
文件：

- [galaxy_search_panel.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/widgets/galaxy/galaxy_search_panel.dart)

当前行为：

- 非全屏浮层搜索面板
- 本地名称 / 标签 / 扇区实时过滤
- 点击结果后相机飞行定位
- 搜索过程中非匹配节点 dimming

### 5.4 小地图
文件：

- [galaxy_mini_map.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/widgets/galaxy/galaxy_mini_map.dart)

当前行为：

- 左下角小地图
- 显示所有节点与当前 viewport
- 点击小地图跳转
- 拖拽小地图 viewport 做主画布导航

### 5.5 预览卡
文件：

- [galaxy_node_preview_card.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/widgets/galaxy/galaxy_node_preview_card.dart)

当前行为：

- 显示扇区、掌握度、重要度
- 显示掌握环与进度条
- 支持“聚焦查看”
- 支持“查看关联”

---

## 6. 当前视觉与动效能力

### 6.1 背景

- 深色主背景：深海蓝黑
- 浅色背景：冷灰白
- 三层星空
- 低频星云色块
- 相机平移视差

### 6.2 节点

- 5-stop 恒星渐变
- mastery 对亮度、外环、光晕生效
- 未解锁节点虚线与轻脉冲
- importance 5 节点可见微射线
- 选中 glow
- tap ripple
- celebration glow

### 6.3 边

- source -> target 渐变
- `parentChild / prerequisite / derived` 轻微弧线
- `prerequisite` 箭头
- 关系型虚线
- 选中关联边提亮，其他边压暗
- 选中节点直接关联边粒子流动

### 6.4 回放

- Build replay 不再只做 reveal
- 相机会按星域阶段巡航
- 阶段切换伴随轻触觉反馈
- 用户触摸会中断 replay

### 6.5 入场与主题切换

- 首次进入有相机缩放入场
- 页面整体做主题切换淡入
- 返回详情页不会重复播放入场动画

---

## 7. UI 组件状态

### 7.1 控件栏
文件：

- [galaxy_controls.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/widgets/galaxy/galaxy_controls.dart)

当前能力：

- 毛玻璃质感
- 缩放组 / 工具组分组
- 搜索按钮
- 回放激活态 glow

### 7.2 状态页
文件：

- [galaxy_screen.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/screens/galaxy_screen.dart)

当前状态：

- 加载态：星点 orb + 点状 loader
- 错误态：文案 + 重试按钮
- 空态：引导文案 + CTA

### 7.3 概览统计条

- 仅在全景 / 远景出现
- 显示总节点数、解锁率、平均掌握度
- 数字 count-up 动画

---

## 8. 性能保障现状

### 8.1 已启用

- Grid 空间索引
- 视口裁剪
- 节点 / 边预算
- 边 Picture 缓存
- 标签 LRU 缓存
- 帧时监控
- 连续慢帧自动降级

### 8.2 当前降级策略

- 关闭边粒子
- 关闭空闲微漂移
- 收紧节点 / 边预算
- 背景星点数量降低

### 8.3 当前监控点

`StarMapPainter` Timeline 标签：

- `GalaxyPaint`
- `GalaxyPaintEdges`
- `GalaxyPaintNodes`
- `GalaxyPaintLabels`

同时带节点数、匹配数、粒子数等基础参数。

---

## 9. 已清理的遗留文件

以下文件已删除，因为当前新骨架中无引用：

- [galaxy_search_dialog.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/widgets/galaxy/galaxy_search_dialog.dart)
- [node_preview_card.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/widgets/galaxy/node_preview_card.dart)
- [zoom_controls.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/widgets/galaxy/zoom_controls.dart)
- [parallax_star_background.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/widgets/galaxy/parallax_star_background.dart)
- [central_flame.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/widgets/galaxy/central_flame.dart)
- [galaxy_entrance_animation.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/widgets/galaxy/galaxy_entrance_animation.dart)

说明：

- `star_success_animation.dart` 没删，因为现在已重新接入并生效。
- `galaxy_provider.dart` 没删，因为仓库里仍有导出和旧测试引用，但它不是当前主星图运行链路。

---

## 10. 当前仍需注意的约束

### 10.1 `GalaxyScreen` 仍然较重
虽然状态边界已经清楚，但它仍是 orchestrator。

后续如果继续复杂化，建议把以下内容继续拆出去：

- 搜索态管理
- replay stage 生成
- celebration / haptic 协调
- stats / status panel 局部组件

### 10.2 空闲微漂移是“渲染态漂移”，不是业务坐标漂移

- 它不会改后端坐标
- 命中测试仍以真实位置为准
- 当前偏移量很小，因此不会造成体感错位

### 10.3 主题切换使用页面级淡入
这是轻量方案，不是所有 painter 颜色逐帧 lerp。

优点：

- 风险低
- 不破坏现有 painter 纯渲染结构

代价：

- 严格意义上不是每个像素的连续色彩插值

### 10.4 背景与扇区层尚未做独立 Picture 缓存
当前性能仍在预算内，但如果未来继续叠粒子或 shader，优先考虑把背景层再缓存化。

---

## 11. 回归验证结果

### 11.1 静态检查

- `flutter analyze` 已通过：
  - [galaxy_screen.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/screens/galaxy_screen.dart)
  - [star_map_painter.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/widgets/galaxy/star_map_painter.dart)
  - [galaxy_controls.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/widgets/galaxy/galaxy_controls.dart)
  - [galaxy_mini_map.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/widgets/galaxy/galaxy_mini_map.dart)
  - [galaxy_search_panel.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/widgets/galaxy/galaxy_search_panel.dart)
  - [galaxy_node_preview_card.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/widgets/galaxy/galaxy_node_preview_card.dart)

### 11.2 新增单测

新增文件：

- [galaxy_camera_test.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/test/features/galaxy/unit/galaxy_camera_test.dart)
- [galaxy_force_engine_test.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/test/features/galaxy/unit/galaxy_force_engine_test.dart)
- [galaxy_gesture_handler_test.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/test/features/galaxy/unit/galaxy_gesture_handler_test.dart)
- [galaxy_lod_test.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/test/features/galaxy/unit/galaxy_lod_test.dart)

覆盖内容：

- 相机零漂移缩放
- 力学释放后收敛
- tap / double tap / long press -> drag 状态转换
- LOD 边界与 fade 边界

`flutter test` 已通过以上 4 个测试文件。

---

## 12. 后续如果继续增强，建议顺序

1. 把 `GalaxyScreen` 的 replay / celebration / search 状态再拆成 coordinator
2. 如果追求更高上限，再把背景层和扇区层做 Picture 缓存
3. 如果要继续冲击“艺术品级”，再考虑 shader 背景和更精细的边动画
4. 在做第 3 步前，先用真机 DevTools 重新量一轮帧时

---

## 13. 现阶段一句话判断

知识星图已经不再是“需要重做的模块”，而是“可以继续精修和扩展的稳定底座”。
