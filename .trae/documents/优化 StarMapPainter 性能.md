# 优化 StarMapPainter 性能

## 重构计划

### 1. 拆分 StarMapPainter

**创建 StarMapStaticPainter**
- 负责绘制静态内容：连线、节点本体、扇区视图、标签等
- 包含方法：`_drawEdges`, `_drawNodes`, `_drawSectorView`, `_drawClusterLabel`, `_drawNodeLabel`
- 保持现有的缓存机制和数据预处理逻辑

**创建 StarMapDynamicPainter**
- 负责绘制动态内容：选中光圈、证据高亮、动画粒子等
- 包含方法：`_drawSelectionHighlight`, `_drawEvidenceHighlights`
- 只接收与动态效果相关的参数

### 2. 重构 GalaxyScreen

**修改布局结构**
- 使用 Stack 组合两个 Painter
- 静态 Painter 在下，动态 Painter 在上
- 给静态 Painter 的父级添加 RepaintBoundary

**更新 Painter 创建逻辑**
- 分别创建 StarMapStaticPainter 和 StarMapDynamicPainter
- 将相应的参数传递给各自的 Painter
- 确保动态 Painter 只在需要时重绘

### 3. 性能优化

**RepaintBoundary 使用**
- 在 StarMapStaticPainter 外层添加 RepaintBoundary
- 确保静态内容不会因为动态效果（如脉冲动画）而重绘

**参数优化**
- 静态 Painter 只接收静态相关参数
- 动态 Painter 只接收动态相关参数，减少不必要的重绘触发

## 实现步骤

1. **创建 StarMapStaticPainter 类**
   - 从 StarMapPainter 复制静态绘制相关代码
   - 移除动态绘制相关代码和参数

2. **创建 StarMapDynamicPainter 类**
   - 从 StarMapPainter 复制动态绘制相关代码
   - 简化构造函数，只保留动态相关参数

3. **修改 GalaxyScreen**
   - 更新 CustomPaint 部分，使用 Stack 组合两个 Painter
   - 为静态 Painter 添加 RepaintBoundary
   - 更新 Painter 创建逻辑

4. **测试性能**
   - 确保拆分后的代码功能正常
   - 验证性能是否有所提升
   - 检查是否存在布局问题

## 预期效果

- 脉冲动画不会导致整个星图重绘
- 静态内容（如连线、节点）只在必要时重绘
- 动态效果（如选中高亮）可以独立流畅运行
- 整体性能得到显著提升，特别是在复杂星图场景中