import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

/// 必杀技 A: GraphRAG 检索可视化组件
///
/// 实时显示 AI 检索过程中访问的知识节点
/// - 角落小窗口（200x150px）
/// - 节点脉冲动画
/// - 颜色编码：蓝色(向量) / 紫色(图) / 绿色(用户兴趣)
/// - 自动淡出（3秒后）
class GraphRAGVisualizer extends StatefulWidget {

  const GraphRAGVisualizer({
    super.key,
    this.trace,
    this.alignment = Alignment.bottomRight,
    this.isVisible = true,
  });
  /// 检索追踪数据
  final GraphRAGTrace? trace;

  /// 位置（默认右下角）
  final Alignment alignment;

  /// 是否显示
  final bool isVisible;

  @override
  State<GraphRAGVisualizer> createState() => _GraphRAGVisualizerState();
}

class _GraphRAGVisualizerState extends State<GraphRAGVisualizer>
    with TickerProviderStateMixin {
  late AnimationController _pulseController;
  late AnimationController _fadeController;
  Timer? _autoHideTimer;

  @override
  void initState() {
    super.initState();

    // 脉冲动画（循环）
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat(reverse: true);

    // 淡出动画
    _fadeController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 500),
      value: 1.0,
    );
  }

  @override
  void didUpdateWidget(GraphRAGVisualizer oldWidget) {
    super.didUpdateWidget(oldWidget);

    // 新的追踪数据到达
    if (widget.trace != oldWidget.trace && widget.trace != null) {
      // 重置淡出动画
      _fadeController.value = 1.0;

      // 取消之前的自动隐藏
      _autoHideTimer?.cancel();

      // 3秒后自动淡出
      _autoHideTimer = Timer(const Duration(seconds: 3), () {
        if (mounted) {
          _fadeController.reverse();
        }
      });
    }
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _fadeController.dispose();
    _autoHideTimer?.cancel();
    super.dispose();
  }

  Color _getNodeColor(String source) {
    switch (source) {
      case 'vector':
        return DS.brandPrimary.shade400;
      case 'graph':
        return Colors.purple.shade400;
      case 'user_interest':
        return DS.success.shade400;
      default:
        return DS.brandPrimary.shade400;
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.isVisible || widget.trace == null) {
      return const SizedBox.shrink();
    }

    final trace = widget.trace!;

    return Align(
      alignment: widget.alignment,
      child: FadeTransition(
        opacity: _fadeController,
        child: Container(
          width: 200,
          height: 150,
          margin: const EdgeInsets.all(DS.lg),
          decoration: BoxDecoration(
            color: DS.brandPrimary.withOpacity(0.8),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: DS.brandPrimary.withOpacity(0.3),
            ),
            boxShadow: [
              BoxShadow(
                color: DS.brandPrimary.withOpacity(0.5),
                blurRadius: 10,
                spreadRadius: 2,
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 标题栏
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 8,
                ),
                decoration: BoxDecoration(
                  color: DS.brandPrimary.withOpacity(0.1),
                  borderRadius: const BorderRadius.only(
                    topLeft: Radius.circular(12),
                    topRight: Radius.circular(12),
                  ),
                ),
                child: Row(
                  children: [
                    Icon(
                      Icons.psychology,
                      size: 16,
                      color: DS.brandPrimary.withOpacity(0.8),
                    ),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        'AI 检索中...',
                        style: TextStyle(
                          color: DS.brandPrimary.withOpacity(0.8),
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                  ],
                ),
              ),

              // 节点可视化区域
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.all(DS.md),
                  child: _buildNodeVisualization(trace),
                ),
              ),

              // 统计信息
              Padding(
                padding: const EdgeInsets.fromLTRB(12, 0, 12, 8),
                child: _buildStats(trace),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildNodeVisualization(GraphRAGTrace trace) {
    // 显示最多5个节点
    final nodesToShow = trace.nodesRetrieved.take(5).toList();

    return CustomPaint(
      painter: _NodeGraphPainter(
        nodes: nodesToShow,
        nodeSources: trace.nodeSources,
        pulseAnimation: _pulseController,
        getColor: _getNodeColor,
      ),
      child: const SizedBox.expand(),
    );
  }

  Widget _buildStats(GraphRAGTrace trace) => Row(
      mainAxisAlignment: MainAxisAlignment.spaceAround,
      children: [
        _buildStatItem(
          '向量',
          trace.vectorSearchCount.toString(),
          DS.brandPrimary.shade400,
        ),
        _buildStatItem(
          '图谱',
          trace.graphSearchCount.toString(),
          Colors.purple.shade400,
        ),
        _buildStatItem(
          '时间',
          '${(trace.timing['total'] ?? 0).toStringAsFixed(2)}s',
          DS.brandPrimary70,
        ),
      ],
    );

  Widget _buildStatItem(String label, String value, Color color) => Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          value,
          style: TextStyle(
            color: color,
            fontSize: 14,
            fontWeight: FontWeight.bold,
          ),
        ),
        Text(
          label,
          style: TextStyle(
            color: DS.brandPrimary.withOpacity(0.6),
            fontSize: 10,
          ),
        ),
      ],
    );
}

/// 节点图绘制器
class _NodeGraphPainter extends CustomPainter {

  _NodeGraphPainter({
    required this.nodes,
    required this.nodeSources,
    required this.pulseAnimation,
    required this.getColor,
  }) : super(repaint: pulseAnimation);
  final List<NodeInfo> nodes;
  final Map<String, String> nodeSources;
  final Animation<double> pulseAnimation;
  final Color Function(String) getColor;

  @override
  void paint(Canvas canvas, Size size) {
    if (nodes.isEmpty) return;

    final centerX = size.width / 2;
    final centerY = size.height / 2;
    final radius = math.min(size.width, size.height) / 3;

    // 绘制节点
    for (var i = 0; i < nodes.length; i++) {
      final node = nodes[i];
      final source = nodeSources[node.id] ?? 'vector';
      final color = getColor(source);

      // 圆形布局
      final angle = (2 * math.pi / nodes.length) * i;
      final x = centerX + radius * math.cos(angle);
      final y = centerY + radius * math.sin(angle);

      // 脉冲效果
      final pulseScale = 1.0 + pulseAnimation.value * 0.3;

      // 绘制连接线
      if (i < nodes.length - 1) {
        final nextAngle = (2 * math.pi / nodes.length) * (i + 1);
        final nextX = centerX + radius * math.cos(nextAngle);
        final nextY = centerY + radius * math.sin(nextAngle);

        final linePaint = Paint()
          ..color = color.withOpacity(0.3)
          ..strokeWidth = 1.0
          ..style = PaintingStyle.stroke;

        canvas.drawLine(Offset(x, y), Offset(nextX, nextY), linePaint);
      }

      // 绘制节点圆圈（外圈脉冲）
      final outerPaint = Paint()
        ..color = color.withOpacity(0.3 * pulseAnimation.value)
        ..style = PaintingStyle.fill;

      canvas.drawCircle(
        Offset(x, y),
        8 * pulseScale,
        outerPaint,
      );

      // 绘制节点圆圈（内圈）
      final innerPaint = Paint()
        ..color = color
        ..style = PaintingStyle.fill;

      canvas.drawCircle(Offset(x, y), 5, innerPaint);

      // 绘制节点名称（简短）
      final textPainter = TextPainter(
        text: TextSpan(
          text: _truncateName(node.name),
          style: TextStyle(
            color: DS.brandPrimary.withOpacity(0.7),
            fontSize: 8,
          ),
        ),
        textDirection: TextDirection.ltr,
      );

      textPainter.layout();
      textPainter.paint(
        canvas,
        Offset(x - textPainter.width / 2, y + 8),
      );
    }
  }

  String _truncateName(String name) {
    if (name.length <= 6) return name;
    return '${name.substring(0, 5)}...';
  }

  @override
  bool shouldRepaint(_NodeGraphPainter oldDelegate) => oldDelegate.nodes != nodes ||
        oldDelegate.nodeSources != nodeSources;
}

/// GraphRAG 追踪数据模型
class GraphRAGTrace {

  GraphRAGTrace({
    required this.traceId,
    required this.query,
    required this.timestamp,
    required this.nodesRetrieved,
    required this.nodeSources,
    required this.vectorSearchCount,
    required this.graphSearchCount,
    required this.userInterestCount,
    required this.timing,
  });

  factory GraphRAGTrace.fromJson(Map<String, dynamic> json) => GraphRAGTrace(
      traceId: json['trace_id'] as String,
      query: json['query'] as String,
      timestamp: DateTime.parse(json['timestamp'] as String),
      nodesRetrieved: (json['nodes_retrieved'] as List)
          .map((node) => NodeInfo.fromJson(node))
          .toList(),
      nodeSources: Map<String, String>.from(json['node_sources'] ?? {}),
      vectorSearchCount: json['vector_search_count'] as int,
      graphSearchCount: json['graph_search_count'] as int,
      userInterestCount: json['user_interest_count'] as int,
      timing: Map<String, double>.from(
        (json['timing'] as Map).map(
          (key, value) => MapEntry(key as String, (value as num).toDouble()),
        ),
      ),
    );
  final String traceId;
  final String query;
  final DateTime timestamp;
  final List<NodeInfo> nodesRetrieved;
  final Map<String, String> nodeSources; // node_id -> source
  final int vectorSearchCount;
  final int graphSearchCount;
  final int userInterestCount;
  final Map<String, double> timing;
}

/// 节点信息
class NodeInfo {

  NodeInfo({
    required this.id,
    required this.name,
    this.description,
  });

  factory NodeInfo.fromJson(Map<String, dynamic> json) => NodeInfo(
      id: json['id'] as String,
      name: json['name'] as String,
      description: json['description'] as String?,
    );
  final String id;
  final String name;
  final String? description;
}
