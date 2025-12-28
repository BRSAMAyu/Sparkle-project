import 'dart:ui';

/// 四叉树节点数据接口
abstract class QuadTreeItem {
  Offset get position;
  String get id;
}

/// 四叉树实现 - 用于空间分区优化碰撞检测
///
/// 功能:
/// 1. O(log n) 空间查询
/// 2. 范围查询
/// 3. 最近邻查询
class QuadTree<T extends QuadTreeItem> {
  QuadTree({
    required this.bounds,
    this.capacity = 4,
    this.maxDepth = 8,
    this.depth = 0,
  });

  final Rect bounds;
  final int capacity;
  final int maxDepth;
  final int depth;

  final List<T> _items = [];

  QuadTree<T>? _northwest;
  QuadTree<T>? _northeast;
  QuadTree<T>? _southwest;
  QuadTree<T>? _southeast;

  bool _isDivided = false;

  /// 是否已分裂
  bool get isDivided => _isDivided;

  /// 当前节点的项目数
  int get itemCount => _items.length;

  /// 子树总项目数
  int get totalItemCount {
    var count = _items.length;
    if (_isDivided) {
      count += _northwest!.totalItemCount;
      count += _northeast!.totalItemCount;
      count += _southwest!.totalItemCount;
      count += _southeast!.totalItemCount;
    }
    return count;
  }

  /// 插入项目
  bool insert(T item) {
    // 检查是否在边界内
    if (!bounds.contains(item.position)) {
      return false;
    }

    // 如果未分裂且有容量，直接添加
    if (!_isDivided && _items.length < capacity) {
      _items.add(item);
      return true;
    }

    // 如果未分裂但已满，尝试分裂
    if (!_isDivided) {
      if (depth >= maxDepth) {
        // 达到最大深度，强制添加
        _items.add(item);
        return true;
      }
      _subdivide();
    }

    // 尝试插入子节点
    if (_northwest!.insert(item)) return true;
    if (_northeast!.insert(item)) return true;
    if (_southwest!.insert(item)) return true;
    if (_southeast!.insert(item)) return true;

    // 如果子节点都无法插入（边界问题），添加到当前节点
    _items.add(item);
    return true;
  }

  /// 分裂为四个子节点
  void _subdivide() {
    final x = bounds.left;
    final y = bounds.top;
    final w = bounds.width / 2;
    final h = bounds.height / 2;

    _northwest = QuadTree<T>(
      bounds: Rect.fromLTWH(x, y, w, h),
      capacity: capacity,
      maxDepth: maxDepth,
      depth: depth + 1,
    );
    _northeast = QuadTree<T>(
      bounds: Rect.fromLTWH(x + w, y, w, h),
      capacity: capacity,
      maxDepth: maxDepth,
      depth: depth + 1,
    );
    _southwest = QuadTree<T>(
      bounds: Rect.fromLTWH(x, y + h, w, h),
      capacity: capacity,
      maxDepth: maxDepth,
      depth: depth + 1,
    );
    _southeast = QuadTree<T>(
      bounds: Rect.fromLTWH(x + w, y + h, w, h),
      capacity: capacity,
      maxDepth: maxDepth,
      depth: depth + 1,
    );

    _isDivided = true;

    // 将现有项目重新分配到子节点
    final itemsToRedistribute = List<T>.from(_items);
    _items.clear();

    for (final item in itemsToRedistribute) {
      if (!_northwest!.insert(item) &&
          !_northeast!.insert(item) &&
          !_southwest!.insert(item) &&
          !_southeast!.insert(item)) {
        // 如果无法插入子节点，保留在当前节点
        _items.add(item);
      }
    }
  }

  /// 范围查询 - 返回在指定区域内的所有项目
  List<T> queryRange(Rect range, [List<T>? found]) {
    found ??= [];

    // 如果查询范围与边界不相交，直接返回
    if (!bounds.overlaps(range)) {
      return found;
    }

    // 检查当前节点的项目
    for (final item in _items) {
      if (range.contains(item.position)) {
        found.add(item);
      }
    }

    // 如果已分裂，递归查询子节点
    if (_isDivided) {
      _northwest!.queryRange(range, found);
      _northeast!.queryRange(range, found);
      _southwest!.queryRange(range, found);
      _southeast!.queryRange(range, found);
    }

    return found;
  }

  /// 圆形范围查询
  List<T> queryCircle(Offset center, double radius, [List<T>? found]) {
    found ??= [];

    // 使用包围盒进行初步筛选
    final boundingBox = Rect.fromCircle(center: center, radius: radius);

    if (!bounds.overlaps(boundingBox)) {
      return found;
    }

    // 检查当前节点的项目
    for (final item in _items) {
      final distance = (item.position - center).distance;
      if (distance <= radius) {
        found.add(item);
      }
    }

    // 递归查询子节点
    if (_isDivided) {
      _northwest!.queryCircle(center, radius, found);
      _northeast!.queryCircle(center, radius, found);
      _southwest!.queryCircle(center, radius, found);
      _southeast!.queryCircle(center, radius, found);
    }

    return found;
  }

  /// 查找最近的k个邻居
  List<T> findNearestNeighbors(Offset point, int k, {double maxDistance = double.infinity}) {
    final candidates = <_DistanceItem<T>>[];

    // 递归收集候选项
    _collectCandidates(point, maxDistance, candidates);

    // 按距离排序
    candidates.sort((a, b) => a.distance.compareTo(b.distance));

    // 返回前k个
    return candidates.take(k).map((e) => e.item).toList();
  }

  void _collectCandidates(Offset point, double maxDistance, List<_DistanceItem<T>> candidates) {
    // 检查边界是否可能包含更近的点
    final closestPointInBounds = _closestPointInRect(point, bounds);
    if ((closestPointInBounds - point).distance > maxDistance) {
      return;
    }

    // 检查当前节点的项目
    for (final item in _items) {
      final distance = (item.position - point).distance;
      if (distance <= maxDistance) {
        candidates.add(_DistanceItem(item, distance));
      }
    }

    // 递归子节点
    if (_isDivided) {
      _northwest!._collectCandidates(point, maxDistance, candidates);
      _northeast!._collectCandidates(point, maxDistance, candidates);
      _southwest!._collectCandidates(point, maxDistance, candidates);
      _southeast!._collectCandidates(point, maxDistance, candidates);
    }
  }

  /// 计算点到矩形最近点
  Offset _closestPointInRect(Offset point, Rect rect) {
    final x = point.dx.clamp(rect.left, rect.right);
    final y = point.dy.clamp(rect.top, rect.bottom);
    return Offset(x, y);
  }

  /// 移除项目
  bool remove(T item) {
    // 检查当前节点
    if (_items.remove(item)) {
      return true;
    }

    // 检查子节点
    if (_isDivided) {
      if (_northwest!.remove(item)) return true;
      if (_northeast!.remove(item)) return true;
      if (_southwest!.remove(item)) return true;
      if (_southeast!.remove(item)) return true;
    }

    return false;
  }

  /// 清空四叉树
  void clear() {
    _items.clear();
    if (_isDivided) {
      _northwest!.clear();
      _northeast!.clear();
      _southwest!.clear();
      _southeast!.clear();
      _northwest = null;
      _northeast = null;
      _southwest = null;
      _southeast = null;
      _isDivided = false;
    }
  }

  /// 获取所有项目（扁平化）
  List<T> getAllItems([List<T>? result]) {
    result ??= [];
    result.addAll(_items);

    if (_isDivided) {
      _northwest!.getAllItems(result);
      _northeast!.getAllItems(result);
      _southwest!.getAllItems(result);
      _southeast!.getAllItems(result);
    }

    return result;
  }

  /// 获取统计信息
  QuadTreeStats getStats() {
    var nodeCount = 1;
    var leafCount = _isDivided ? 0 : 1;
    var totalItems = _items.length;
    var maxItemsPerNode = _items.length;

    if (_isDivided) {
      final nwStats = _northwest!.getStats();
      final neStats = _northeast!.getStats();
      final swStats = _southwest!.getStats();
      final seStats = _southeast!.getStats();

      nodeCount += nwStats.nodeCount + neStats.nodeCount + swStats.nodeCount + seStats.nodeCount;
      leafCount += nwStats.leafCount + neStats.leafCount + swStats.leafCount + seStats.leafCount;
      totalItems += nwStats.totalItems + neStats.totalItems + swStats.totalItems + seStats.totalItems;
      maxItemsPerNode = [
        maxItemsPerNode,
        nwStats.maxItemsPerNode,
        neStats.maxItemsPerNode,
        swStats.maxItemsPerNode,
        seStats.maxItemsPerNode,
      ].reduce((a, b) => a > b ? a : b);
    }

    return QuadTreeStats(
      nodeCount: nodeCount,
      leafCount: leafCount,
      totalItems: totalItems,
      maxItemsPerNode: maxItemsPerNode,
      maxDepth: depth,
    );
  }
}

class _DistanceItem<T> {
  _DistanceItem(this.item, this.distance);

  final T item;
  final double distance;
}

/// 四叉树统计信息
class QuadTreeStats {
  const QuadTreeStats({
    required this.nodeCount,
    required this.leafCount,
    required this.totalItems,
    required this.maxItemsPerNode,
    required this.maxDepth,
  });

  final int nodeCount;
  final int leafCount;
  final int totalItems;
  final int maxItemsPerNode;
  final int maxDepth;

  double get averageItemsPerLeaf => leafCount > 0 ? totalItems / leafCount : 0;

  @override
  String toString() =>
      'QuadTreeStats(nodes: $nodeCount, leaves: $leafCount, items: $totalItems, maxPerNode: $maxItemsPerNode, depth: $maxDepth)';
}

/// 简单的四叉树节点包装器
class SimpleQuadTreeItem implements QuadTreeItem {
  SimpleQuadTreeItem({
    required this.id,
    required this.position,
    this.data,
  });

  @override
  final String id;

  @override
  final Offset position;

  final dynamic data;
}
