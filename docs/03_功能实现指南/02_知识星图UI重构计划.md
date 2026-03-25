知识星图 (Knowledge Galaxy) UI 重构计划

 目标概述

 重构知识星图模块的 UI 和交互，解决以下核心问题：
 1. 中心火焰固定不动、视觉效果差
 2. 节点重叠、缩放不丝滑
 3. 节点无法点击交互
 4. 星域分类未可视化
 5. 缺少知识卡详情页面

 ---
 用户确认的设计决策

 | 决策点   | 选择                                          |
 |----------|-----------------------------------------------|
 | 火焰位置 | 跟随画布中心 (2000,2000)，随拖拽移动          |
 | 详情界面 | 全屏页面，包含完整信息                        |
 | 布局算法 | 混合方案：快速算法首次渲染 + 空闲时力导向优化 |

 ---
 实现阶段

 Phase 1: 火焰跟随画布 & 星域配置 (优先级: 高)

 目标: 将 FlameCore 移入画布，创建星域配置

 需修改的文件

 | 文件                                                      |
 操作                                                   |
 |-----------------------------------------------------------|--
 ------------------------------------------------------|
 | mobile/lib/presentation/screens/galaxy_screen.dart        |
 修改 - 将 FlameCore 放入 InteractiveViewer 的 Stack 中 |
 | mobile/lib/presentation/widgets/galaxy/flame_core.dart    |
 修改 - 移除 IgnorePointer 依赖，调整尺寸               |
 | mobile/lib/presentation/widgets/galaxy/sector_config.dart |
 新建 - 7个星域的颜色和配置                             |

 关键代码变更

 galaxy_screen.dart:
 // 之前: FlameCore 在 Stack 外层用 Center 包裹
 // 之后: FlameCore 在 InteractiveViewer 内部，使用 Positioned
 InteractiveViewer(
   child: SizedBox(
     width: _canvasSize,
     height: _canvasSize,
     child: Stack(
       children: [
         // 背景星云
         CustomPaint(painter: SectorBackgroundPainter()),
         // 火焰在画布中心
         Positioned(
           left: _canvasCenter - _flameCoreSize/2,
           top: _canvasCenter - _flameCoreSize/2,
           child: FlameCore(intensity:
 state.userFlameIntensity),
         ),
         // 星图
         CustomPaint(painter: StarMapPainter(...)),
       ],
     ),
   ),
 )

 sector_config.dart (新建):
 class SectorConfig {
   static const Map<SectorEnum, SectorStyle> styles = {
     SectorEnum.COSMOS: SectorStyle(
       name: '理性星域',
       primaryColor: Color(0xFF00BFFF),
       glowColor: Color(0xFF87CEEB),
       baseAngle: 0.0,
       sweepAngle: 51.4, // 360/7
     ),
     SectorEnum.TECH: SectorStyle(
       name: '造物星域',
       primaryColor: Color(0xFFC0C0C0),
       glowColor: Color(0xFFE8E8E8),
       baseAngle: 51.4,
       sweepAngle: 51.4,
     ),
     // ... 其他5个星域
   };
 }

 ---
 Phase 2: 智能布局算法 (优先级: 高)

 目标: 防止节点重叠，实现星域分区布局

 需修改的文件

 | 文件                                                   | 操作
                               |
 |--------------------------------------------------------|-----
 ------------------------------|
 | mobile/lib/presentation/providers/galaxy_provider.dart | 修改
  - 新的 _calculateLayout 算法 |

 混合布局算法设计

 // 第一步: 快速螺旋布局 (立即渲染)
 Map<String, Offset> _calculateQuickLayout(List<GalaxyNodeModel>
  nodes) {
   // 1. 按星域分组
   Map<SectorEnum, List<GalaxyNodeModel>> sectorGroups =
 groupBySector(nodes);

   // 2. 每个星域内使用螺旋布局，避免重叠
   for (sector in sectorGroups) {
     final style = SectorConfig.styles[sector];
     int index = 0;
     for (node in sectorGroups[sector]) {
       // 螺旋公式: r = a + b*theta
       double radius = 180 + index * 25; // 基础半径 + 增量
       double angle = style.baseAngle + (index * 15) %
 style.sweepAngle;
       positions[node.id] = polarToCartesian(radius, angle);
       index++;
     }
   }
   return positions;
 }

 // 第二步: 空闲时力导向优化 (后台计算)
 Future<Map<String, Offset>> _optimizeWithForceDirected(
   Map<String, Offset> initial,
   List<GalaxyNodeModel> nodes,
 ) async {
   return compute(_forceDirectedLayout, (initial, nodes));
 }

 // 力导向核心算法 (在 isolate 中运行)
 Map<String, Offset> _forceDirectedLayout(data) {
   var positions = data.initial;
   for (int iter = 0; iter < 100; iter++) {
     // 斥力: 节点之间互斥
     for (nodeA in nodes) {
       for (nodeB in nodes) {
         if (nodeA.id == nodeB.id) continue;
         final delta = positions[nodeA.id] -
 positions[nodeB.id];
         final distance = delta.distance.clamp(10.0, 500.0);
         final repulsion = 1000 / (distance * distance);
         positions[nodeA.id] += delta.normalize() * repulsion;
       }
     }
     // 引力: 同星域节点聚集
     // 约束: 保持在星域扇形区域内
   }
   return positions;
 }

 GalaxyState 扩展

 class GalaxyState {
   // ... 现有字段
   final bool isOptimizing;  // 是否正在后台优化布局
 }

 ---
 Phase 3: 星域可视化 & 背景 (优先级: 中)

 目标: 绘制 7 个星域的星云背景和标签

 需新建的文件

 | 文件
          | 操作                |
 |--------------------------------------------------------------
 ---------|---------------------|
 | mobile/lib/presentation/widgets/galaxy/sector_background_pain
 ter.dart | 新建 - 星域背景渲染 |

 渲染设计

 class SectorBackgroundPainter extends CustomPainter {
   @override
   void paint(Canvas canvas, Size size) {
     final center = Offset(size.width/2, size.height/2);

     for (final entry in SectorConfig.styles.entries) {
       final sector = entry.key;
       final style = entry.value;

       // 1. 绘制扇形星云 (径向渐变)
       final path = _createSectorPath(center, style.baseAngle,
 style.sweepAngle);
       final gradient = RadialGradient(
         colors: [
           style.primaryColor.withOpacity(0.06),
           style.primaryColor.withOpacity(0.02),
           Colors.transparent,
         ],
       );
       canvas.drawPath(path, Paint()..shader =
 gradient.createShader(bounds));

       // 2. 绘制星域名称标签 (在边缘)
       final labelAngle = style.baseAngle + style.sweepAngle /
 2;
       final labelPos = polarToCartesian(800, labelAngle) +
 center;
       _drawLabel(canvas, style.name, labelPos,
 style.glowColor);
     }
   }
 }

 ---
 Phase 4: 节点点击交互 (优先级: 高)

 目标: 实现节点点击检测，跳转到详情页

 需修改的文件

 | 文件                                               | 操作
                                 |
 |----------------------------------------------------|---------
 --------------------------------|
 | mobile/lib/presentation/screens/galaxy_screen.dart | 修改 -
 添加 GestureDetector 和 hit 检测 |
 | mobile/lib/app/routes.dart                         | 修改 -
 添加 /galaxy/node/:id 路由       |

 Hit 检测实现

 // galaxy_screen.dart
 GestureDetector(
   onTapUp: (details) {
     // 1. 屏幕坐标 → 画布坐标
     final matrix =
 _transformationController.value.clone()..invert();
     final canvasTap = MatrixUtils.transformPoint(matrix,
 details.localPosition);

     // 2. 查找点击的节点 (考虑缩放后的点击半径)
     final scale =
 _transformationController.value.getMaxScaleOnAxis();
     final hitRadius = 30 / scale; // 缩放越小，点击区域相对越大

     final galaxyState = ref.read(galaxyProvider);
     for (final node in galaxyState.nodes) {
       final nodePos = galaxyState.nodePositions[node.id]! +
 Offset(_canvasCenter, _canvasCenter);
       if ((canvasTap - nodePos).distance < hitRadius) {
         // 3. 跳转到详情页
         context.push('/galaxy/node/${node.id}');
         return;
       }
     }
   },
   child: InteractiveViewer(...),
 )

 ---
 Phase 5: 知识详情页 (优先级: 高)

 目标: 创建完整的知识节点详情页面

 需新建的文件

 | 文件
           | 操作                |
 |--------------------------------------------------------------
 ----------|---------------------|
 | mobile/lib/presentation/screens/knowledge/knowledge_detail_sc
 reen.dart | 新建 - 详情页 UI    |
 | mobile/lib/presentation/providers/knowledge_detail_provider.d
 art       | 新建 - 详情页状态   |
 | mobile/lib/data/models/knowledge_detail_model.dart
           | 新建 - 详情数据模型 |

 详情页布局

 class KnowledgeDetailScreen extends ConsumerWidget {
   final String nodeId;

   @override
   Widget build(context, ref) {
     final detailAsync =
 ref.watch(knowledgeDetailProvider(nodeId));

     return Scaffold(
       body: CustomScrollView(
         slivers: [
           // 1. Hero 头部 (星域颜色渐变背景)
           SliverAppBar(
             expandedHeight: 200,
             flexibleSpace: _NodeHeader(node: detail.node),
           ),

           // 2. 掌握度卡片
           SliverToBoxAdapter(
             child: _MasteryCard(
               mastery: detail.node.masteryScore,
               studyMinutes: detail.totalStudyMinutes,
               nextReview: detail.nextReviewAt,
             ),
           ),

           // 3. 节点描述
           SliverToBoxAdapter(child:
 _DescriptionSection(detail.description)),

           // 4. 相关知识节点 (迷你图谱)
           SliverToBoxAdapter(
             child: _RelatedNodesSection(relations:
 detail.relations),
           ),

           // 5. 相关任务卡列表
           SliverToBoxAdapter(
             child: _RelatedTasksSection(tasks:
 detail.relatedTasks),
           ),

           // 6. 相关计划列表
           SliverToBoxAdapter(
             child: _RelatedPlansSection(plans:
 detail.relatedPlans),
           ),
         ],
       ),

       // 底部操作栏
       bottomNavigationBar: _BottomActions(
         onStartStudy: () => _startStudy(context, detail.node),
         onSparkNode: () => _sparkNode(ref, detail.node),
       ),
     );
   }
 }

 API 端点使用

 后端已有 GET /galaxy/node/{node_id} 返回节点详情。需添加：

 // api_endpoints.dart
 static String galaxyNodeDetail(String id) =>
 '/galaxy/node/$id';

 // galaxy_repository.dart
 Future<KnowledgeDetailResponse> getNodeDetail(String nodeId)
 async {
   final response = await
 _apiClient.get(ApiEndpoints.galaxyNodeDetail(nodeId));
   return KnowledgeDetailResponse.fromJson(response.data);
 }

 ---
 Phase 6: 缩放聚合 (优先级: 中)

 目标: 缩小时节点智能聚合，放大时展开

 需修改的文件

 | 文件
 | 操作                         |
 |--------------------------------------------------------------
 |------------------------------|
 | mobile/lib/presentation/providers/galaxy_provider.dart
 | 修改 - 添加 aggregationLevel |
 | mobile/lib/presentation/widgets/galaxy/star_map_painter.dart
 | 修改 - 根据聚合级别渲染      |

 聚合策略

 // 缩放阈值
 const SCALE_FULL = 0.8;      // 显示所有节点
 const SCALE_CLUSTER = 0.4;   // 按父节点聚合
 const SCALE_SECTOR = 0.2;    // 只显示星域中心

 // star_map_painter.dart
 void _drawNodes(Canvas canvas) {
   if (scale >= SCALE_FULL) {
     _drawAllNodes(canvas);
   } else if (scale >= SCALE_CLUSTER) {
     _drawClusteredNodes(canvas);
   } else {
     _drawSectorCentroids(canvas);
   }
 }

 void _drawClusteredNodes(Canvas canvas) {
   // 1. 按父节点分组
   // 2. 绘制父节点为大圆，显示子节点数量
   // 3. 子节点用小点围绕表示
 }

 ---
 Phase 7: 视觉增强 (优先级: 低)

 目标: 改进动画效果和视觉细节

 可选增强

 1. 星域星云动态效果 - 使用 Shader 实现流动星云
 2. 节点涌现动画 - LLM 扩展新节点时的渐显效果
 3. 连接线能量流动 - 动态渐变表示知识关联强度
 4. 背景繁星 - 装饰性的小光点

 ---
 文件变更汇总

 新建文件 (7个)

 | 路径
           | 用途              |
 |--------------------------------------------------------------
 ----------|-------------------|
 | mobile/lib/presentation/widgets/galaxy/sector_config.dart
           | 星域配置常量      |
 | mobile/lib/presentation/widgets/galaxy/sector_background_pain
 ter.dart  | 星域背景渲染      |
 | mobile/lib/presentation/screens/knowledge/knowledge_detail_sc
 reen.dart | 知识详情页        |
 | mobile/lib/presentation/providers/knowledge_detail_provider.d
 art       | 详情页状态管理    |
 | mobile/lib/data/models/knowledge_detail_model.dart
           | 详情数据模型      |
 | mobile/lib/data/models/knowledge_detail_model.g.dart
           | (生成) JSON序列化 |
 | mobile/lib/presentation/providers/knowledge_detail_provider.g
 .dart     | (生成) Riverpod   |

 修改文件 (6个)

 | 路径
 | 变更说明                         |
 |--------------------------------------------------------------
 |----------------------------------|
 | mobile/lib/presentation/screens/galaxy_screen.dart
 | FlameCore 移入画布、添加点击检测 |
 | mobile/lib/presentation/providers/galaxy_provider.dart
 | 新布局算法、聚合状态             |
 | mobile/lib/presentation/widgets/galaxy/star_map_painter.dart
 | 星域颜色、聚合渲染               |
 | mobile/lib/presentation/widgets/galaxy/flame_core.dart
 | 移除 IgnorePointer 依赖          |
 | mobile/lib/app/routes.dart
 | 添加 /galaxy/node/:id 路由       |
 | mobile/lib/core/network/api_endpoints.dart
 | 添加 galaxyNodeDetail            |

 ---
 实施顺序

 Phase 1: 火焰跟随画布 + 星域配置
     ↓
 Phase 2: 智能布局算法 (防重叠)
     ↓
 Phase 4: 节点点击交互 ──→ Phase 5: 知识详情页
     ↓
 Phase 3: 星域背景可视化
     ↓
 Phase 6: 缩放聚合
     ↓
 Phase 7: 视觉增强 (可选)

 建议优先完成: Phase 1 → 2 → 4 → 5 (核心功能)

 ---
 技术风险 & 缓解

 | 风险              | 缓解措施
    |
 |-------------------|------------------------------------------
 ---|
 | 力导向计算慢      | 使用 compute() 在 isolate 中计算，不阻塞
 UI |
 | 500+ 节点渲染卡顿 | 视口裁剪，只渲染可见区域的节点
    |
 | 点击检测不准      | 动态调整点击半径 (30/scale)
    |
 | Shader 不兼容     | 保留 Flutter fallback 实现
    |

 ---
 代码生成提醒

 修改以下文件后需运行代码生成：
 cd mobile
 flutter pub run build_runner build --delete-conflicting-outputs

 - knowledge_detail_model.dart (添加 @JsonSerializable())
 - knowledge_detail_provider.dart (添加 @riverpod)