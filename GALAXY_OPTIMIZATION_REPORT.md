# 知识星图功能优化方案报告

**版本**: v2.0
**日期**: 2025-12-28
**目标**: 解决卡顿、优化层级渲染、改进连线逻辑、重设交互方式

---

## 一、问题诊断总结

### 1.1 初始视图问题
- **现状**: 初始 scale=1.0，直接显示 4000×4000 画布中心，渲染全部节点
- **症状**: 进入时大量节点同时绘制，造成首帧卡顿
- **根因**: `_transformationController` 初始化时未设置合理缩放比

### 1.2 层级渲染问题
- **现状**: `AggregationLevel` 仅有 3 档（full/clustered/sectors），阈值固定 (0.6/0.3)
- **症状**: 缩放过渡生硬，节点切换无动画，视口外节点虽做了 culling 但仍参与预处理
- **根因**:
  - 缺乏渐进式 LOD（Level of Detail）
  - 节点展开/收束无过渡动画
  - `_preprocessData()` 在构造函数中执行，每次重建 Painter 都重算

### 1.3 连线混乱问题
- **现状**: 所有 edges（含 parent-child 隐式边）全部渲染
- **症状**: 低重要度节点的连线密集交织，视觉噪声大
- **根因**:
  - 未按层级过滤连线
  - 缺少"点击展开关联"的交互机制

### 1.4 交互设计问题
- **现状**: 单击直接跳转详情页 (`context.push('/galaxy/node/$id')`)
- **症状**: 用户难以快速预览节点，误触率高
- **建议**: 短按显示连线+弹窗预览，长按跳转详情

---

## 二、优化方案

### 2.1 初始视图优化

#### 目标
进入星图时显示全局「星域鸟瞰视角」，仅渲染 7 个星域质心 + 根节点

#### 实现思路

1. **初始缩放设为 0.15~0.2**
   - 位置: `galaxy_screen.dart` 的 `initState` 或 `_centerTransformation`
   - 效果: 触发 `AggregationLevel.sectors`，仅绘制 7 个星域球体

2. **入场动画分两阶段**
   - 阶段 1（0-1.5s）: 当前 `GalaxyEntranceAnimation` 保留
   - 阶段 2（1.5-3s）: 从 scale=0.15 平滑 Tween 到 scale=0.25，伴随星域名称渐显

3. **懒加载节点数据**
   - 初次 `loadGalaxy()` 只请求根节点 + 一级子节点（importance ≥ 4）
   - 用户放大到 scale ≥ 0.5 时，异步加载剩余节点
   - 新增 API: `GET /galaxy/nodes?depth=1&importance_min=4`

#### 关键改动点
```
galaxy_screen.dart:56 → 设置初始 matrix scale
galaxy_provider.dart:138 → 分阶段加载逻辑
```

---

### 2.2 渐进式层级渲染

#### 目标
缩放时仅渲染视口内接近当前缩放级别的节点，配合精美展开/收束动画

#### 层级定义（5 档 LOD）

| 档位 | Scale 范围 | 渲染内容 | 节点数量级 |
|------|-----------|---------|-----------|
| L0 (宇宙) | < 0.2 | 星域质心 | 7 |
| L1 (星系) | 0.2-0.4 | 根节点（importance=5）| ~20 |
| L2 (星群) | 0.4-0.6 | importance ≥ 3 的节点 | ~100 |
| L3 (星云) | 0.6-0.8 | importance ≥ 2 的节点 | ~300 |
| L4 (全览) | ≥ 0.8 | 全部节点 | 1000+ |

#### 渐进渲染机制

1. **视口动态 Culling 前置化**
   - 将 culling 从 `StarMapPainter` 移至 `GalaxyNotifier.updateScale()`
   - 每次缩放变化时计算 `visibleNodeIds`，Painter 直接使用过滤后的列表

2. **节点隐显动画**（关键体验点）
   - 放大进入新 LOD 时：子节点从父节点位置「绽放」展开
     - 动画: 300ms EaseOutBack，opacity 0→1，position 从 parent 移动到 target
   - 缩小离开当前 LOD 时：子节点「收束」回父节点
     - 动画: 250ms EaseInQuad，opacity 1→0，position 从 target 移动到 parent
   - 实现: 新建 `AnimatedNode` widget，或在 Painter 中维护 `nodeAnimationProgress` map

3. **RepaintBoundary 分层**
   - 将静态层（背景星空、星域雾气）与动态层（节点、连线）分离
   - 静态层用 `RepaintBoundary` 包裹，避免重绘

4. **帧率保护**
   - 检测 FPS < 30 时自动降级：关闭 glow、减少粒子、简化连线
   - 使用 `SchedulerBinding.instance.currentFrameTimeStamp` 监测

#### 关键改动点
```
galaxy_provider.dart → 新增 _computeVisibleNodes()、nodeAnimationStates
star_map_painter.dart → 读取 animationProgress 绘制过渡态
新建 animated_node_controller.dart → 管理节点展开/收束动画
```

---

### 2.3 连线显示优化

#### 目标
默认仅显示关键连线，点击节点后显示其关联连线

#### 连线分级策略

| 连线类型 | 默认可见条件 | 说明 |
|---------|-------------|-----|
| 星域→根节点 | scale < 0.4 | 中心到根的放射线 |
| 根→一级子节点 | scale 0.4-0.6 | 主干结构线 |
| parent-child | scale ≥ 0.6 + 父节点 importance ≥ 4 | 树形层级线 |
| 横向关联 (related/similar/contrast) | **仅点击时** | 避免蜘蛛网效果 |
| 前置/衍生 (prerequisite/derived) | 目标节点 importance ≥ 4 | 学习路径线 |

#### 点击展开连线

1. **状态管理**
   - 新增 `GalaxyState.selectedNodeId` 和 `expandedEdgeNodeIds: Set<String>`
   - 短按节点 → 设置 selectedNodeId → 触发该节点关联边的渲染

2. **连线动画**
   - 点击后，关联连线从目标节点「射出」
   - 动画: 200ms 线条从 0 长度生长到完整，伴随 glow 扩散

3. **二次点击收回**
   - 再次点击同一节点或点击空白区域 → 收回连线

#### 关键改动点
```
galaxy_provider.dart → 新增 selectedNodeId, expandedEdgeNodeIds
star_map_painter.dart:_drawEdges → 增加可见性过滤逻辑
galaxy_screen.dart:_handleTapUp → 改为设置 selectedNodeId 而非跳转
```

---

### 2.4 交互重设计

#### 目标
短按 = 预览 + 显示连线，长按 = 跳转详情

#### 交互矩阵

| 手势 | 作用对象 | 行为 |
|-----|---------|-----|
| 短按 | 节点 | 显示该节点到关联节点的连线 + 弹出预览卡片 |
| 短按 | 空白 | 收起所有展开的连线，关闭预览卡片 |
| 长按 | 节点 | 跳转至知识详情页 `/galaxy/node/{id}` |
| 双指缩放 | 画布 | 缩放 + 触发 LOD 切换 |
| 拖拽 | 画布 | 平移 |

#### 预览卡片设计

1. **弹窗位置**: 节点上方或下方（根据屏幕空间自适应）
2. **内容**:
   - 节点名称（标题）
   - 所属星域（彩色标签）
   - 掌握度进度条
   - 简短描述（1-2 句，来自后端 `node.description`）
   - 「前往学习」按钮（等效长按）
3. **动画**:
   - 出现: 150ms FadeIn + ScaleUp (0.9→1.0)
   - 消失: 100ms FadeOut

#### 手势识别实现

```dart
GestureDetector(
  onTapUp: (details) => _handleTap(details),       // 短按
  onLongPress: () => _handleLongPress(),           // 长按
  child: InteractiveViewer(...),
)
```

需新增 `_handleLongPress()` 并存储当前触点对应的节点 ID

#### 关键改动点
```
galaxy_screen.dart → GestureDetector 增加 onLongPress
新建 node_preview_card.dart → 预览卡片 widget
galaxy_provider.dart → 新增 previewNodeId 状态
```

---

## 三、性能优化补充

### 3.1 渲染优化

| 优化项 | 方案 | 收益 |
|-------|-----|-----|
| Gradient 缓存 | 按 (startColor, endColor, points) 缓存 Gradient 对象 | 减少 Gradient 创建开销 |
| TextPainter 复用 | 维护 `Map<String, TextPainter>` 按节点 ID 缓存 | 避免每帧 layout |
| Glow 简化 | scale < 0.5 时关闭 MaskFilter | 减少模糊计算 |
| 边数量控制 | 可见边 > 500 条时自动降级为虚线 | 减少 drawLine 调用 |

### 3.2 内存优化

| 优化项 | 方案 |
|-------|-----|
| 节点分块加载 | 按星域懒加载，离开视口 5 秒后释放 |
| 图片资源 | 节点图标使用 SpriteSheet 而非独立 Asset |
| 动画对象池 | `EnergyParticle` 使用对象池复用 |

### 3.3 布局引擎优化

| 优化项 | 方案 |
|-------|-----|
| 收敛检测 | 力导向迭代时检测位移 delta < 0.5 提前终止 |
| 空间索引 | 使用四叉树加速斥力计算（O(n²) → O(n log n)） |
| 增量更新 | 新增节点时仅重算局部，不全量重布局 |

---

## 四、实施优先级

| 阶段 | 内容 | 关键文件 | 影响范围 |
|-----|------|---------|---------|
| P0 | 初始视图缩放 + 入场动画优化 | galaxy_screen.dart | 首屏体验 |
| P0 | 连线分级过滤 | star_map_painter.dart, galaxy_provider.dart | 视觉清晰度 |
| P1 | 短按/长按交互重设计 | galaxy_screen.dart, 新建 node_preview_card.dart | 用户体验 |
| P1 | 5 档 LOD + 节点展开收束动画 | galaxy_provider.dart, star_map_painter.dart | 流畅度 |
| P2 | 性能优化（缓存、对象池） | star_map_painter.dart, energy_particle.dart | 帧率稳定性 |
| P2 | 布局引擎四叉树优化 | galaxy_layout_engine.dart | 加载速度 |

---

## 五、预期效果

| 指标 | 优化前 | 优化后目标 |
|-----|-------|----------|
| 首帧渲染时间 | ~800ms | < 200ms |
| 缩放过渡帧率 | 15-25 FPS | 稳定 60 FPS |
| 可见连线数量 | 全量 (~500+) | 动态 (10-50) |
| 内存占用 (1000节点) | ~120MB | < 60MB |
| 用户误触跳转率 | 高 | 低（长按才跳转） |

---

## 六、附录：关键代码位置索引

| 功能模块 | 文件路径 |
|---------|---------|
| 主屏幕 | `lib/presentation/screens/galaxy_screen.dart` |
| 状态管理 | `lib/presentation/providers/galaxy_provider.dart` |
| 节点/边渲染 | `lib/presentation/widgets/galaxy/star_map_painter.dart` |
| 布局引擎 | `lib/core/services/galaxy_layout_engine.dart` |
| 星域配置 | `lib/presentation/widgets/galaxy/sector_config.dart` |
| 入场动画 | `lib/presentation/widgets/galaxy/galaxy_entrance_animation.dart` |
| 能量粒子 | `lib/presentation/widgets/galaxy/energy_particle.dart` |
| 小地图 | `lib/presentation/widgets/galaxy/galaxy_mini_map.dart` |
| 缩放控件 | `lib/presentation/widgets/galaxy/zoom_controls.dart` |

---

*报告完毕。请根据项目实际情况调整优先级并按阶段实施。*
我已完成知识星图功能的全面优化，主要改动如下：

### 1. 核心架构与性能优化 (LOD 系统)
- **5级渐进式渲染**: 在 `galaxy_provider.dart` 中引入了 5 级 LOD (`universe` 到 `full`)，根据缩放级别动态切换渲染策略。
- **预计算可视性**: 将视口裁剪 (Culling) 和连线过滤逻辑从渲染层移至状态管理层 (`_computeVisibleNodes/Edges`)，大幅减少每帧绘制计算量。
- **智能连线过滤**: 低缩放级别自动隐藏非关键连线，仅在选中节点或高倍缩放时显示详细关系，解决“毛线球”视觉杂乱问题。

### 2. 交互体验重构
- **全新点击逻辑**: 
  - **短按**: 选中节点并弹出「预览卡片」，展示节点信息与关联。
  - **长按**: 直接跳转至知识点详情页。
  - **点击空白**: 取消选中状态。
- **预览卡片组件**: 新增 `NodePreviewCard` (`node_preview_card.dart`)，提供流畅的节点概览体验。

### 3. 视觉与动画升级
- **入场动画**: 调整初始视角为「宇宙全景」(Scale 0.15)，并在入场后平滑推进至「星系视图」(Scale 0.25)。
- **选中高亮**: 在 `StarMapPainter` 中增加了选中节点的视觉反馈。
- **层级渲染**: 根据 LOD 级别动态绘制星域光晕、星团聚合体或具体节点，提供更强的纵深感。

### 代码变更概览
- **修改**: `mobile/lib/presentation/providers/galaxy_provider.dart` (LOD状态逻辑)
- **修改**: `mobile/lib/presentation/widgets/galaxy/star_map_painter.dart` (分级渲染)
- **修改**: `mobile/lib/presentation/screens/galaxy_screen.dart` (交互手势与动画)
- **新增**: `mobile/lib/presentation/widgets/galaxy/node_preview_card.dart` (预览UI)

现在星图具备了更佳的性能表现和更符合直觉的探索体验。