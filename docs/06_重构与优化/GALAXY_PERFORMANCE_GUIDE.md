# 知识星图全面性能与显示效果优化指南

## 1. 核心原理回顾

Sparkle 的知识星图 (Galaxy) 是一个高性能的交互式数据可视化模块，其核心渲染与计算架构设计如下：

### 1.1 渲染管线 (Render Pipeline)
星图采用 Flutter 的 `CustomPainter` 进行直接画布 (Canvas) 绘制，而非构建大量的 Widget 树。这种“即时模式”渲染提供了最大的性能上限。

- **Layered Painting**: 分层绘制背景 (Void)、连线 (Edges)、节点 (Nodes) 和文本 (Labels)。
- **Batch Processing**: 对节点和连线进行预处理 (`ProcessedNode`, `ProcessedEdge`)，计算好颜色、位置和样式，避免在 `paint` 循环中进行逻辑运算。
- **Smart Caching**: 使用 `SmartCache` 和 `TextImageCache` 缓存计算昂贵的对象。
  - **LRU Eviction**: 对文本位图和 Gradient 实施 LRU (Least Recently Used) 淘汰，防止显存溢出。
  - **Centralized Disposal**: `TextImageCache` 负责管理 `ui.Image` 的生命周期，并在缓存淘汰或销毁时显式调用 `.dispose()`，而非由 Painter 负责。

### 1.2 布局引擎 (Layout Engine)
布局计算是星图最消耗 CPU 的环节。我们采用了 **力导向算法 (Force-Directed Graph)**，模拟物理引力和斥力。

- **Isolate Offloading**: `GalaxyLayoutEngine` 将繁重的迭代计算放入独立的 `Isolate` (后台线程) 执行，避免阻塞 UI 线程造成掉帧。
- **Quadtree Optimization**: 引入 **四叉树 (Quadtree)** 空间索引结构，将碰撞检测的时间复杂度从 $O(N^2)$ 降低到 $O(N \log N)$。
  - **Node Pooling**: 复用四叉树节点对象，减少 GC 压力。
  - **Displacement Threshold**: 统一策略（含 Ultra 模式），仅在节点位移超过阈值（如 2.0px）时重建四叉树，避免无意义的重建导致的抖动。
  - **Short-circuit**: 当视口内可见节点 N < 50 时，跳过四叉树构建，仅执行视口裁剪 + 轻量碰撞检查。

### 1.3 细节层次 (LOD - Level of Detail)
根据用户的缩放级别 (`scale`) 动态调整渲染内容的精细度。**LOD 策略全局统一**，不随设备 Tier 改变：

| 等级 | 语义名称 | Scale 范围 | 渲染策略 |
| :--- | :--- | :--- | :--- |
| **L0** | **Universe (全览)** | $< 0.2$ | **完全隐藏**所有节点和连线，仅渲染星域 (Cluster) 的**质心光晕**和**星域标签**。 |
| **L1** | **Galaxy (星系)** | $0.2 - 0.4$ | 显示大型节点 (Major Nodes)，隐藏小节点和连线，仅显示关键标签。 |
| **L2** | **Sector (星域)** | $0.4 - 0.6$ | 显示所有节点，显示父子连线，标准标签密度。 |
| **L3** | **Nebula (星云)** | $0.6 - 0.8$ | 增加关联连线，开启辉光 (Glow) 效果。 |
| **L4** | **Node (微观)** | $> 0.8$ | 完整细节，显示所有文本，开启流体特效和动态粒子。 |

---

## 2. 性能瓶颈矩阵

不同设备在不同缩放级别下面临的性能挑战如下表所示：

| 缩放级别 | 渲染对象数量 | 主要瓶颈 (Bottleneck) | 表现症状 |
| :--- | :--- | :--- | :--- |
| **L0 Universe** | 仅质心光晕 (极少) | **Draw Calls**<br>尽管数量少，但大面积光晕混合可能占用 Fill Rate | 整体流畅，但在低端机可能略有发热 |
| **L2 Sector** | 中等数量节点 + 标签 | **CPU/GPU Bus (带宽)**<br>大量文本绘制指令提交 | 滚动卡顿，文字闪烁 |
| **L4 Node** | 少量大节点 + 特效 | **Fragment Shader (片段着色器)**<br>高斯模糊 (Blur)、辉光 (Glow)、渐变 (Gradient) | 动画掉帧，GPU 负载高 |
| **布局计算阶段** | N/A | **CPU Compute (计算)**<br>物理模拟迭代 | UI 线程冻结 (若未用 Isolate)，加载时间长 |

---

## 3. 分级优化方案 (Tiered Strategy)

为了在从入门级 Android 手机到最新 iPhone Pro Max 上都能提供最佳体验，我们实施分级优化策略。

### 3.1 性能分级定义

我们放弃了难以在运行时准确获取的 Geekbench 分数，转而使用启发式设备分级 (Heuristic Device Grading)：

| 模式 | 判定标准 (满足其一即可) | 目标 FPS |
| :--- | :--- | :--- |
| **Lite (基础版)** | RAM < 4GB, CPU < 6核, GPU 为 Adreno 610/Mali-G52 以下 | 30 |
| **Standard (标准版)** | RAM 4-8GB, 主流中端芯片 (Snapdragon 7/855, Dimensity 1000) | 60 |
| **Ultra (极致版)** | RAM > 8GB, 旗舰芯片 (Snapdragon 8 Gen 2+, A15+), 支持 120Hz | 60/120 |

### 3.2 详细配置参数

| 优化维度 | Lite (基础版) | Standard (标准版) | Ultra (极致版) |
| :--- | :--- | :--- | :--- |
| **渲染特效** | **Shader**: 关闭 (使用纯色)<br>**Glow**: 关闭<br>**Blur**: 关闭 | **Shader**: 开启 (标准)<br>**Glow**: 仅选中/高亮节点<br>**Blur**: 静态层开启 | **Shader**: 全特效 (流体/噪点)<br>**Glow**: 全局动态辉光<br>**Blur**: 全局高斯模糊 |
| **LOD 策略** | **全局统一** (见 1.3) | **全局统一** (见 1.3) | **全局统一** (见 1.3) |
| **动画效果** | **过渡**: 极简 (150ms)<br>**粒子**: 关闭 | **过渡**: 标准 (300ms)<br>**粒子**: 少量 (Max 20) | **过渡**: 物理弹簧 (Spring)<br>**粒子**: 大量 (Max 100+) |
| **布局计算** | **迭代**: 仅初始布局 + 1次碰撞解决<br>**碰撞**: 根节点简单检测<br>**更新**: 停止滚动时更新 | **迭代**: Isolate 50次<br>**碰撞**: 标准四叉树<br>**频率**: 节流实时更新 | **迭代**: Isolate 持续模拟<br>**碰撞**: 高精度四叉树 (带位移阈值)<br>**频率**: 实时平滑插值 |
| **连线渲染** | **策略**: 仅显示父子关系<br>**样式**: 实线 (无渐变) | **策略**: 父子 + 选中关联<br>**样式**: 线性渐变 | **策略**: 全量关联显示<br>**样式**: 动态流光特效 |
| **背景装饰** | **星空**: 静态图片 | **星空**: 动态 Canvas 绘制<br>**视差**: 2层 | **星空**: 3D 粒子/Shader<br>**视差**: 3-4层多维视差 |

---

## 4. 进阶优化技术推荐

### 4.1 缓存管理强化 (Cache Management)
- **Centralized Disposal**: **关键修正**。Painter 不再负责直接 `dispose` 资源。所有 `ui.Image` 和复杂 Shader 对象的生命周期由 `SmartCacheManager` 统一管理。
- **LRU Eviction**: `TextImageCache` 必须实现 LRU 策略。设定硬性上限（如 50MB 或 200 个条目），当超出时淘汰最久未使用的位图，并在此时触发 `image.dispose()`。
- **TTL**: 为缓存条目设置 Time-To-Live，例如 60秒未访问则清除，防止内存泄漏。

### 4.2 离屏渲染与分片 (Offscreen & Tiling)
对于 Ultra 模式下的复杂背景（如动态星云），建议使用 `RepaintBoundary`。
- **Layer Separation**: 将静态背景（星星、网格）与动态前景（节点动画）分离到不同的 `CustomPaint` 组件中，并给静态层加上 `RepaintBoundary`。
- **Tiled Rendering**: 如果背景图非常大（超过 GPU 最大纹理尺寸，通常 4096px），必须进行分片绘制 (Tiling)，否则会导致崩溃或黑屏。
- **Limit DPR**: 限制离屏缓冲区的 `devicePixelRatio` 不超过 2.0，即使在 3.0 的屏幕上，以节省 55% 的显存。

### 4.3 自动性能降级与滞后 (Hysteresis & Cooldown)
系统应监控**过去 1 秒内的平均帧率**，而非固定帧数，以适应不同刷新率设备。降级顺序固定为 **DPR 降采样 → 特效降级 → Tier 降级**，升级顺序反向执行，确保体验稳定且可预测。

**降级逻辑 (Downgrade):**
- **检测窗口**: 过去 1 秒 (60Hz=60帧, 120Hz=120帧)。
- **触发条件**:
  - **120Hz 设备**: 平均 FPS < 80 (降至 60Hz 逻辑或降低 Tier)。
  - **60Hz 设备**: 平均 FPS < 35。
  - **30Hz 设备**: 平均 FPS < 20。
- **动作**: 按 “DPR 降采样 → 特效降级 → Tier 降级” 顺序执行，若已到最低级别则保持。
- **冷却**: 降级后锁定 10 秒，不检测升级。

**升级逻辑 (Upgrade):**
- **检测窗口**: 过去 5 秒。
- **触发条件**:
  - **60Hz 设备**: 平均 FPS > 58。
  - **120Hz 设备**: 平均 FPS > 115。
- **动作**: 按 “Tier 升级 → 特效升级 → DPR 恢复” 顺序执行，若已到最高级别则保持。
- **冷却**: 升级后锁定 20 秒。

### 4.4 状态级裁剪 (State-Level Culling)
除了 `ViewportCuller` 在绘制时裁剪，还应在 `GalaxyNotifier` 层面进行**逻辑裁剪**。
- 如果节点完全在屏幕外且没有活跃的物理模拟，不要向其发送 `tick` 更新。
- 仅计算视口内及周边缓冲区的节点位置更新。

---

## 5. 用户体验建议

### 5.1 "绽放" 加载动画 (Bloom Loading)
为了掩盖布局计算的延迟（通常需要 500ms - 2s），设计一个"宇宙大爆炸"风格的进场动画：
1.  **初始态**：所有节点聚集在屏幕中心一个极小的点。
2.  **计算中**：显示中心高亮的光晕呼吸动画，此时后台 Isolate 正在疯狂计算布局。
3.  **计算完成**：节点从中心向四周爆发式扩散 (`SpringSimulation`)，飞向计算好的目标位置。

### 5.2 交互反馈
- **点击响应**：点击节点时，优先绘制选中态圆圈，随后才触发相机移动，保证输入的瞬时响应。
- **阻尼感**：在拖拽平移和缩放时，通过 `PhysicsSimulation` 添加轻微的阻尼和惯性，使手感更加厚重、真实。
