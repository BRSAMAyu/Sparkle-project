# 知识星图对齐文档

更新时间：2026-03-08

## 1. 文档目的
这份文档用于你后续重做知识星图时快速接手当前实现，明确：

- 当前前后端真实结构
- 这几轮改动过什么
- 现存问题和失败点
- 必须保留的业务能力
- 可以直接推倒重做的部分

这不是概念文档，是基于当前仓库代码的工程对齐文档。

---

## 2. 当前结论

### 2.1 当前状态
知识星图现在不是“功能不存在”，而是“架构混合且体验不达标”。

核心问题：

1. 交互层、渲染层、状态层没有彻底解耦
2. Provider 仍承担了过多视图态和渲染态职责
3. 画布缩放/拖拽虽然做过缓存，但相机同步与命中逻辑仍然互相牵扯
4. 页面视觉层被多轮改动污染，背景、控件、动画都不够稳定
5. 当前星图离 Obsidian 的工作台式流畅交互仍有明显差距

### 2.2 你的重做判断
你完全可以大刀阔斧重构。  
建议保留业务协议、节点详情链路和已有数据模型，不保留当前前端星图实现的多数视图组织方式。

---

## 3. 当前前后端结构

## 3.1 后端 API 入口
文件：

- [/Users/brsama/code/GitHub/Sparkle-project/backend/app/api/v1/galaxy.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/api/v1/galaxy.py)

当前主要接口：

1. `GET /api/v1/galaxy/graph`
- 获取完整图
- 支持 `zoom_level`
- 支持 `sector_code`
- 支持 `include_locked`

2. `POST /api/v1/galaxy/nodes/viewport`
- 获取 viewport 子图
- 当前前端高性能路径主要依赖这个接口

3. `GET /api/v1/galaxy/node/{node_id}`
- 获取知识节点详情
- 当前点击节点进入详情页依赖这个接口

4. `POST /api/v1/galaxy/node/{node_id}/spark`
- 点亮节点/提升掌握度

5. `POST /api/v1/galaxy/search`
- 星图搜索

6. `GET /api/v1/galaxy/review/suggestions`
- 复习建议

## 3.2 后端服务分层
文件：

- [/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/galaxy_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/galaxy_service.py)
- [/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/galaxy/structure_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/galaxy/structure_service.py)

当前实际职责：

### `GalaxyService`
Facade 层，负责：
- 图获取
- 视口图获取
- 语义搜索
- spark 行为
- 节点创建/边创建
- 对外聚合 `structure/retrieval/stats`

### `GraphStructureService`
负责：
- 节点/边 CRUD
- 视口节点查询
- 完整图查询
- 节点位置更新

### 当前后端已经具备的能力
- 节点有稳定持久化坐标 `position_x / position_y`
- viewport 查询已经存在
- 节点详情接口存在
- 节点位置回写存在

这意味着你重做前端时，不需要再自己在前端做完整布局求解。

---

## 4. 当前移动端结构

## 4.1 页面入口
文件：

- [/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/screens/galaxy_screen.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/screens/galaxy_screen.dart)

这是当前星图主页面，职责过重，实际同时做了：

- 相机控制
- 手势处理
- viewport 计算
- 中心定位
- 选中态/拖拽态
- painter 缓存
- 动画控制
- overlay 控件
- 节点详情跳转

这是当前最大结构问题之一。

## 4.2 Provider
文件：

- [/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/providers/galaxy_provider.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/providers/galaxy_provider.dart)

当前 `GalaxyState` 很重，包含：

- 全量 nodes / edges
- visibleNodes / visibleEdges
- visibleCompactNodes
- viewport
- scale
- aggregationLevel
- clusters
- interaction state
- focus/highlight state
- animation progress
- optimization config

问题：

1. 数据态和视图态混在一起
2. 可见性裁剪和交互状态都挂在 provider 上
3. 即使做了预计算，也仍容易让 rebuild 范围扩大

## 4.3 Repository
文件：

- [/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/data/repositories/enhanced_galaxy_repository.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/data/repositories/enhanced_galaxy_repository.dart)

当前能力：

- 完整图获取
- viewport 图获取
- 节点位置更新
- 节点详情获取
- spark
- 缓存与重试

这层整体可以保留，不是主要问题点。

## 4.4 渲染组件
关键文件：

- [/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/widgets/galaxy/star_map_painter.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/widgets/galaxy/star_map_painter.dart)
- [/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/widgets/galaxy/node_preview_card.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/widgets/galaxy/node_preview_card.dart)
- [/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/widgets/galaxy/zoom_controls.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/widgets/galaxy/zoom_controls.dart)

当前问题：

1. Painter 仍承担过多内容绘制
2. 控件层和画布层视觉语言不统一
3. 缩放倍率映射、拖拽命中阈值、点击与长按判定仍然不够稳

---

## 5. 这几轮已经改过的内容

下面是我已经动过的点，你重做时需要知道，避免踩旧路。

## 5.1 做过的正确方向

### 1. 引入 viewport 子图思路
不是全量图每次都重算，而是：
- 先拿 viewport 图
- 用局部子图渲染

### 2. 尝试做缓存
做过这些缓存：
- painter signature 缓存
- viewport 计算缓存
- scene snapshot 缓存

### 3. 把部分动画从主图层拆出来
做过：
- 选中态覆盖层
- 关系高亮层
- 轻量 preview card

### 4. 节点详情链路已打通
目标交互现在是：
- 单击节点 -> 进入知识详情页
- 长按节点 -> 显示预览卡

### 5. 节点位置持久化已打通
拖拽后位置可以回写后端，不是纯前端假交互。

## 5.2 做过但不成功的方向

### 1. 在现有页面里持续做小修补
结果：
- 缓存越来越多
- 状态越来越混
- 体感改善有限

### 2. 重背景/重装饰 + 继续追求品牌氛围
结果：
- 更容易掉帧
- 用户更在意卡顿而不是氛围

### 3. 把视觉问题和性能问题一起修
结果：
- 两边都不彻底
- 星图既不够快，也不够稳

---

## 6. 当前必须保留的业务能力

你重做时，下面这些能力不能丢：

1. 点击节点进入知识详情页
- 详情页入口仍是：
  - [/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/knowledge/presentation/screens/knowledge_detail_screen.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/knowledge/presentation/screens/knowledge_detail_screen.dart)

2. 节点详情数据获取
- 通过 `/api/v1/galaxy/node/{node_id}`

3. spark/点亮节点能力
- 通过 `/api/v1/galaxy/node/{node_id}/spark`

4. 节点位置可持久化
- 拖拽后需要能保存坐标

5. 星图搜索
- 搜索知识节点并定位

6. 节点关系展示
- 但不要求主图一次展开全部关系

7. 与任务/知识模块联动
- 任务完成可能点亮节点
- 详情页应能展示相关任务/前置关系/群组学习入口

8. 深浅色模式都必须可见
- 当前浅色模式已经出过严重不可见问题，重做时必须作为强约束

---

## 7. 当前明确存在的问题

这些问题是已经确认存在的，不需要再重新判断：

1. 缩放时存在漂移和抽动
2. 拖动时存在漂移和手感不稳
3. 缩放倍率组件逻辑不自然
4. 背景视觉不稳定，且你不满意
5. 右下角控件尺寸不一致
6. 初始进入动画/过渡动画会拖累体验
7. 页面内部状态过多，难以继续维护

---

## 8. 建议的重做边界

## 8.1 建议保留
- 后端接口
- Repository 层
- 节点详情页链路
- 持久化坐标
- 节点模型与基础字段

## 8.2 建议直接重写
- `GalaxyScreen`
- `GalaxyProvider` 的状态结构
- `StarMapPainter` 的职责边界
- 缩放/拖拽/点击/长按的交互系统
- 右下角控件组
- 背景系统
- 进入动画与选中动画

---

## 9. 我建议你重做时采用的目标架构

## 9.1 Data Layer
职责：
- 拉取 viewport 子图
- 拉取节点详情
- 更新节点位置
- 做缓存

建议状态对象：
- `GalaxySceneSnapshot`
- `GalaxyViewportQuery`
- `GalaxyNodeDetailCache`

## 9.2 Camera / Interaction Layer
职责：
- 只处理相机矩阵
- 只处理 pan/zoom/inertia
- 只处理命中测试
- 只处理点击/长按/拖拽冲突

不要让它知道业务节点详情内容。

## 9.3 Render Layer
拆成 4 层：

1. `BackgroundLayer`
2. `EdgeLayer`
3. `NodeLayer`
4. `OverlayLayer`

要求：
- 背景静态或近静态
- 节点选中与脉冲只能画在 overlay
- 拖拽中不重算整层内容

## 9.4 Detail / Preview Layer
职责：
- 轻量预览
- 详情跳转
- 相关节点扩展

不要把这层继续塞回画布 render path。

---

## 10. 你重做时的交互合同

建议固定为：

1. 单击节点
- 打开知识详情页

2. 长按节点
- 显示轻量 preview

3. 拖拽节点
- 只有在达到拖拽阈值后才生效
- 一旦进入拖拽，不再触发点击

4. 缩放
- 必须以手势焦点为中心
- 不允许明显漂移

5. 返回
- 恢复相机位置、缩放和选中态

6. 任务完成
- 不再自动跳转知识星图

---

## 11. 重做时的性能上线门槛

这是我建议你直接采用的门槛：

1. 首屏可交互时间
- Android 模拟器 `<= 400ms`

2. 连续拖拽/缩放
- P95 `<= 16ms`

3. 节点/边预算
- 300 可见节点
- 500 可见边
- 不出现持续卡顿

4. 动画
- 全部可中断
- 用户手势优先级高于动画

---

## 12. 当前相关文件清单

### 后端
- [/Users/brsama/code/GitHub/Sparkle-project/backend/app/api/v1/galaxy.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/api/v1/galaxy.py)
- [/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/galaxy_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/galaxy_service.py)
- [/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/galaxy/structure_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/galaxy/structure_service.py)
- [/Users/brsama/code/GitHub/Sparkle-project/backend/app/schemas/galaxy.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/schemas/galaxy.py)

### 移动端主链
- [/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/screens/galaxy_screen.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/screens/galaxy_screen.dart)
- [/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/providers/galaxy_provider.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/providers/galaxy_provider.dart)
- [/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/widgets/galaxy/star_map_painter.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/widgets/galaxy/star_map_painter.dart)
- [/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/widgets/galaxy/node_preview_card.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/widgets/galaxy/node_preview_card.dart)
- [/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/widgets/galaxy/zoom_controls.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/widgets/galaxy/zoom_controls.dart)
- [/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/data/repositories/enhanced_galaxy_repository.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/data/repositories/enhanced_galaxy_repository.dart)
- [/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/shared/entities/galaxy_model.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/shared/entities/galaxy_model.dart)

### 详情页链路
- [/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/knowledge/presentation/screens/knowledge_detail_screen.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/knowledge/presentation/screens/knowledge_detail_screen.dart)
- [/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/knowledge/presentation/providers/knowledge_detail_provider.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/knowledge/presentation/providers/knowledge_detail_provider.dart)

---

## 13. 最终建议

如果你要自己重新做，我的建议很明确：

1. 不要继续在当前 `GalaxyScreen + GalaxyProvider + StarMapPainter` 上修补
2. 保留后端协议和数据模型
3. 先做一版纯性能优先、极简背景、稳定点击详情的版本
4. 体感稳定以后，再逐步加回品牌意象

正确顺序应该是：

`稳定交互 -> 正确详情链路 -> 视图层级清晰 -> 再加美术表达`

不要反过来。
