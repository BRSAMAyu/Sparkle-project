import 'dart:async';
// ignore_for_file: prefer_expression_function_bodies, unused_element

import 'dart:math' as math;

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

/// WebAssembly布局加速器
///
/// 使用WebAssembly进行高性能的力导向布局计算
/// 在不支持WASM的平台上会优雅降级到Dart实现
class WasmLayoutAccelerator {
  WasmLayoutAccelerator._();

  static WasmLayoutAccelerator? _instance;
  static WasmLayoutAccelerator get instance {
    _instance ??= WasmLayoutAccelerator._();
    return _instance!;
  }

  /// WASM模块是否可用
  bool _isWasmAvailable = false;
  bool get isWasmAvailable => _isWasmAvailable;

  /// 是否已初始化
  bool _isInitialized = false;
  bool get isInitialized => _isInitialized;

  /// 初始化加速器
  Future<void> initialize() async {
    if (_isInitialized) return;

    try {
      // 尝试加载WASM模块
      _isWasmAvailable = await _loadWasmModule();
      _isInitialized = true;
      debugPrint(
          'WasmLayoutAccelerator initialized: WASM available = $_isWasmAvailable',);
    } catch (e) {
      debugPrint('Failed to initialize WASM: $e');
      _isWasmAvailable = false;
      _isInitialized = true;
    }
  }

  Future<bool> _loadWasmModule() async {
    // 在Web平台上尝试加载WASM
    if (kIsWeb) {
      try {
        // 这里会尝试加载并编译WASM模块
        // 实际实现需要使用package:wasm或js_interop
        // 目前先返回false，表示使用Dart fallback
        return false;
      } catch (e) {
        return false;
      }
    }
    // 非Web平台暂不支持WASM
    return false;
  }

  /// 计算力导向布局
  ///
  /// [nodes] - 节点列表，每个节点包含id和初始位置
  /// [edges] - 边列表，每条边包含source和target id
  /// [config] - 布局配置参数
  ///
  /// 返回优化后的节点位置
  Future<Map<String, Offset>> calculateForceDirectedLayout({
    required List<LayoutNode> nodes,
    required List<LayoutEdge> edges,
    LayoutConfig config = const LayoutConfig(),
  }) async {
    if (_isWasmAvailable) {
      return _calculateWithWasm(nodes, edges, config);
    } else {
      return _calculateWithDart(nodes, edges, config);
    }
  }

  /// WASM实现 (预留)
  Future<Map<String, Offset>> _calculateWithWasm(
    List<LayoutNode> nodes,
    List<LayoutEdge> edges,
    LayoutConfig config,
  ) async {
    // WASM调用预留
    // 在实际实现中，这里会：
    // 1. 将节点和边序列化为二进制格式
    // 2. 调用WASM模块的compute函数
    // 3. 解析返回的二进制位置数据

    // 目前使用Dart实现作为fallback
    return _calculateWithDart(nodes, edges, config);
  }

  /// Dart实现 (fallback)
  Future<Map<String, Offset>> _calculateWithDart(
    List<LayoutNode> nodes,
    List<LayoutEdge> edges,
    LayoutConfig config,
  ) async {
    // 使用isolate进行并行计算
    return compute(
      _forceDirectedLayoutCompute,
      _LayoutComputeData(
        nodes: nodes,
        edges: edges,
        config: config,
      ),
    );
  }

  /// 批量更新位置 (增量更新)
  Future<Map<String, Offset>> updatePositions({
    required Map<String, Offset> currentPositions,
    required List<LayoutEdge> edges,
    required Set<String> movedNodeIds,
    LayoutConfig config = const LayoutConfig(),
  }) async {
    // 转换为LayoutNode格式
    final nodes = currentPositions.entries
        .map(
          (e) => LayoutNode(
            id: e.key,
            x: e.value.dx,
            y: e.value.dy,
            fixed: !movedNodeIds.contains(e.key),
          ),
        )
        .toList();

    // 进行有限次数的迭代
    final updatedConfig = LayoutConfig(
      iterations: config.iterations ~/ 4, // 增量更新使用更少迭代
      repulsionStrength: config.repulsionStrength,
      attractionStrength: config.attractionStrength,
      damping: config.damping,
      minDistance: config.minDistance,
    );

    return calculateForceDirectedLayout(
      nodes: nodes,
      edges: edges,
      config: updatedConfig,
    );
  }

  /// 计算节点间的力
  static Offset _calculateRepulsion(
      Offset pos1, Offset pos2, double strength, double minDistance,) {
    final dx = pos1.dx - pos2.dx;
    final dy = pos1.dy - pos2.dy;
    var distance = math.sqrt(dx * dx + dy * dy);

    if (distance < minDistance) distance = minDistance;

    final force = strength / (distance * distance);
    return Offset(dx * force / distance, dy * force / distance);
  }

  /// 计算弹簧吸引力
  static Offset _calculateAttraction(
      Offset pos1, Offset pos2, double strength, double idealLength,) {
    final dx = pos2.dx - pos1.dx;
    final dy = pos2.dy - pos1.dy;
    final distance = math.sqrt(dx * dx + dy * dy);

    if (distance < 1) return Offset.zero;

    final displacement = distance - idealLength;
    final force = displacement * strength;

    return Offset(dx * force / distance, dy * force / distance);
  }
}

/// 布局节点
class LayoutNode {
  const LayoutNode({
    required this.id,
    required this.x,
    required this.y,
    this.fixed = false,
    this.mass = 1.0,
    this.radius = 20.0,
  });

  final String id;
  final double x;
  final double y;
  final bool fixed; // 固定节点不受力影响
  final double mass; // 质量，影响斥力计算
  final double radius; // 半径，影响碰撞检测
}

/// 布局边
class LayoutEdge {
  const LayoutEdge({
    required this.source,
    required this.target,
    this.weight = 1.0,
    this.idealLength = 100.0,
  });

  final String source;
  final String target;
  final double weight; // 边权重，影响吸引力
  final double idealLength; // 理想长度
}

/// 布局配置
class LayoutConfig {
  const LayoutConfig({
    this.iterations = 100,
    this.repulsionStrength = 500.0,
    this.attractionStrength = 0.1,
    this.damping = 0.9,
    this.minDistance = 30.0,
    this.idealEdgeLength = 100.0,
    this.theta = 0.5, // Barnes-Hut阈值
    this.cooling = 0.95, // 温度冷却系数
  });

  final int iterations;
  final double repulsionStrength;
  final double attractionStrength;
  final double damping;
  final double minDistance;
  final double idealEdgeLength;
  final double theta;
  final double cooling;
}

/// Isolate计算数据
class _LayoutComputeData {
  _LayoutComputeData({
    required this.nodes,
    required this.edges,
    required this.config,
  });

  final List<LayoutNode> nodes;
  final List<LayoutEdge> edges;
  final LayoutConfig config;
}

/// Isolate中执行的力导向布局计算
Map<String, Offset> _forceDirectedLayoutCompute(_LayoutComputeData data) {
  final nodes = data.nodes;
  final edges = data.edges;
  final config = data.config;

  if (nodes.isEmpty) return {};

  // 初始化位置
  final positions = <String, List<double>>{};
  final velocities = <String, List<double>>{};
  final fixed = <String, bool>{};

  for (final node in nodes) {
    positions[node.id] = [node.x, node.y];
    velocities[node.id] = [0.0, 0.0];
    fixed[node.id] = node.fixed;
  }

  // 构建边的邻接表
  final adjacency = <String, List<String>>{};
  final edgeMap = <String, LayoutEdge>{};

  for (final edge in edges) {
    adjacency.putIfAbsent(edge.source, () => []).add(edge.target);
    adjacency.putIfAbsent(edge.target, () => []).add(edge.source);
    edgeMap['${edge.source}_${edge.target}'] = edge;
    edgeMap['${edge.target}_${edge.source}'] = edge;
  }

  // 迭代计算
  var temperature = 1.0;

  for (var iteration = 0; iteration < config.iterations; iteration++) {
    final forces = <String, List<double>>{};

    // 初始化力
    for (final nodeId in positions.keys) {
      forces[nodeId] = [0.0, 0.0];
    }

    // 计算斥力 (O(n²) - 可优化为Barnes-Hut O(n log n))
    final nodeIds = positions.keys.toList();
    for (var i = 0; i < nodeIds.length; i++) {
      for (var j = i + 1; j < nodeIds.length; j++) {
        final id1 = nodeIds[i];
        final id2 = nodeIds[j];
        final pos1 = positions[id1]!;
        final pos2 = positions[id2]!;

        final dx = pos1[0] - pos2[0];
        final dy = pos1[1] - pos2[1];
        var distance = math.sqrt(dx * dx + dy * dy);

        if (distance < config.minDistance) {
          distance = config.minDistance;
        }

        // Coulomb's law: F = k * q1 * q2 / r²
        final force = config.repulsionStrength / (distance * distance);
        final fx = dx * force / distance;
        final fy = dy * force / distance;

        forces[id1]![0] += fx;
        forces[id1]![1] += fy;
        forces[id2]![0] -= fx;
        forces[id2]![1] -= fy;
      }
    }

    // 计算吸引力 (弹簧力)
    for (final edge in edges) {
      final pos1 = positions[edge.source];
      final pos2 = positions[edge.target];
      if (pos1 == null || pos2 == null) continue;

      final dx = pos2[0] - pos1[0];
      final dy = pos2[1] - pos1[1];
      final distance = math.sqrt(dx * dx + dy * dy);

      if (distance < 1) continue;

      // Hooke's law: F = k * (d - L)
      final displacement = distance - edge.idealLength;
      final force = displacement * config.attractionStrength * edge.weight;
      final fx = dx * force / distance;
      final fy = dy * force / distance;

      forces[edge.source]![0] += fx;
      forces[edge.source]![1] += fy;
      forces[edge.target]![0] -= fx;
      forces[edge.target]![1] -= fy;
    }

    // 应用力并更新位置
    for (final nodeId in positions.keys) {
      if (fixed[nodeId] ?? false) continue;

      final vel = velocities[nodeId]!;
      final force = forces[nodeId]!;

      // 更新速度
      vel[0] = (vel[0] + force[0]) * config.damping * temperature;
      vel[1] = (vel[1] + force[1]) * config.damping * temperature;

      // 限制最大速度
      final speed = math.sqrt(vel[0] * vel[0] + vel[1] * vel[1]);
      const maxSpeed = 50.0;
      if (speed > maxSpeed) {
        vel[0] = vel[0] * maxSpeed / speed;
        vel[1] = vel[1] * maxSpeed / speed;
      }

      // 更新位置
      positions[nodeId]![0] += vel[0];
      positions[nodeId]![1] += vel[1];
    }

    // 冷却
    temperature *= config.cooling;

    // 早期终止条件
    if (temperature < 0.01) break;
  }

  // 转换为Offset格式
  return positions.map((id, pos) => MapEntry(id, Offset(pos[0], pos[1])));
}

/// 布局结果统计
class LayoutStats {
  const LayoutStats({
    required this.iterations,
    required this.totalTime,
    required this.avgMoveDistance,
    required this.maxMoveDistance,
    required this.usedWasm,
  });

  final int iterations;
  final Duration totalTime;
  final double avgMoveDistance;
  final double maxMoveDistance;
  final bool usedWasm;

  @override
  String toString() =>
      'LayoutStats(iterations: $iterations, time: ${totalTime.inMilliseconds}ms, '
      'avgMove: ${avgMoveDistance.toStringAsFixed(2)}, maxMove: ${maxMoveDistance.toStringAsFixed(2)}, '
      'wasm: $usedWasm)';
}

/// WASM布局加速器扩展 - 提供便捷的转换方法
extension WasmLayoutAcceleratorX on WasmLayoutAccelerator {
  /// 从Galaxy模型转换
  List<LayoutNode> nodesFromPositions(Map<String, Offset> positions) =>
      positions.entries
          .map(
            (e) => LayoutNode(
              id: e.key,
              x: e.value.dx,
              y: e.value.dy,
            ),
          )
          .toList();

  /// 计算布局并返回统计
  Future<(Map<String, Offset>, LayoutStats)> calculateWithStats({
    required List<LayoutNode> nodes,
    required List<LayoutEdge> edges,
    LayoutConfig config = const LayoutConfig(),
  }) async {
    final stopwatch = Stopwatch()..start();

    final oldPositions = <String, Offset>{};
    for (final node in nodes) {
      oldPositions[node.id] = Offset(node.x, node.y);
    }

    final newPositions = await calculateForceDirectedLayout(
      nodes: nodes,
      edges: edges,
      config: config,
    );

    stopwatch.stop();

    // 计算移动距离
    var totalMove = 0.0;
    var maxMove = 0.0;
    for (final entry in newPositions.entries) {
      final oldPos = oldPositions[entry.key];
      if (oldPos != null) {
        final move = (entry.value - oldPos).distance;
        totalMove += move;
        if (move > maxMove) maxMove = move;
      }
    }

    final avgMove = nodes.isNotEmpty ? totalMove / nodes.length : 0.0;

    return (
      newPositions,
      LayoutStats(
        iterations: config.iterations,
        totalTime: stopwatch.elapsed,
        avgMoveDistance: avgMove,
        maxMoveDistance: maxMove,
        usedWasm: isWasmAvailable,
      ),
    );
  }
}
