// ignore_for_file: cascade_invocations

import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/services/quad_tree.dart';

void main() {
  group('QuadTree', () {
    late QuadTree<SimpleQuadTreeItem> tree;

    setUp(() {
      tree = QuadTree<SimpleQuadTreeItem>(
        bounds: const Rect.fromLTWH(-1000, -1000, 2000, 2000),
      );
    });

    test('inserts items correctly', () {
      final item = SimpleQuadTreeItem(
        id: 'item1',
        position: Offset.zero,
      );

      expect(tree.insert(item), isTrue);
      expect(tree.totalItemCount, equals(1));
    });

    test('rejects items outside bounds', () {
      final item = SimpleQuadTreeItem(
        id: 'item1',
        position: const Offset(5000, 5000), // 在边界外
      );

      expect(tree.insert(item), isFalse);
      expect(tree.totalItemCount, equals(0));
    });

    test('subdivides when capacity is exceeded', () {
      // 插入超过容量的节点
      for (var i = 0; i < 10; i++) {
        tree.insert(
          SimpleQuadTreeItem(
            id: 'item$i',
            position: Offset(i * 50.0, i * 50.0),
          ),
        );
      }

      expect(tree.isDivided, isTrue);
      expect(tree.totalItemCount, equals(10));
    });

    group('queryRange', () {
      setUp(() {
        // 在网格位置插入节点
        for (var x = -500; x <= 500; x += 100) {
          for (var y = -500; y <= 500; y += 100) {
            tree.insert(
              SimpleQuadTreeItem(
                id: 'item_${x}_$y',
                position: Offset(x.toDouble(), y.toDouble()),
              ),
            );
          }
        }
      });

      test('returns items in range', () {
        final results = tree.queryRange(
          const Rect.fromLTWH(-150, -150, 300, 300),
        );

        // 应该包含中心区域的节点
        expect(results.isNotEmpty, isTrue);

        // 所有结果应该在查询范围内
        for (final item in results) {
          expect(item.position.dx, greaterThanOrEqualTo(-150));
          expect(item.position.dx, lessThanOrEqualTo(150));
          expect(item.position.dy, greaterThanOrEqualTo(-150));
          expect(item.position.dy, lessThanOrEqualTo(150));
        }
      });

      test('returns empty for range with no items', () {
        final results = tree.queryRange(
          const Rect.fromLTWH(800, 800, 100, 100), // 没有节点的区域
        );

        expect(results, isEmpty);
      });

      test('returns all items for full bounds query', () {
        final results = tree.queryRange(
          const Rect.fromLTWH(-1000, -1000, 2000, 2000),
        );

        expect(results.length, equals(tree.totalItemCount));
      });
    });

    group('queryCircle', () {
      setUp(() {
        // 在原点周围插入节点
        for (var i = 0; i < 20; i++) {
          final angle = i * 3.14159 * 2 / 20;
          final radius = 100 + (i % 3) * 50;
          tree.insert(
            SimpleQuadTreeItem(
              id: 'item$i',
              position: Offset(
                radius * _cos(angle),
                radius * _sin(angle),
              ),
            ),
          );
        }
      });

      test('returns items in circle', () {
        final results = tree.queryCircle(Offset.zero, 120);

        // 所有结果应该在圆形范围内
        for (final item in results) {
          expect(item.position.distance, lessThanOrEqualTo(120));
        }
      });

      test('returns empty for circle with no items', () {
        final results = tree.queryCircle(const Offset(500, 500), 50);

        expect(results, isEmpty);
      });
    });

    group('findNearestNeighbors', () {
      setUp(() {
        // 插入已知位置的节点
        tree.insert(
          SimpleQuadTreeItem(
            id: 'a',
            position: Offset.zero,
          ),
        );
        tree.insert(
          SimpleQuadTreeItem(
            id: 'b',
            position: const Offset(10, 0),
          ),
        );
        tree.insert(
          SimpleQuadTreeItem(
            id: 'c',
            position: const Offset(20, 0),
          ),
        );
        tree.insert(
          SimpleQuadTreeItem(
            id: 'd',
            position: const Offset(100, 0),
          ),
        );
      });

      test('returns k nearest neighbors', () {
        final results = tree.findNearestNeighbors(const Offset(5, 0), 2);

        expect(results.length, equals(2));
        expect(results[0].id, equals('a')); // 距离 5
        expect(results[1].id, equals('b')); // 距离 5
      });

      test('respects maxDistance', () {
        final results = tree.findNearestNeighbors(
          const Offset(5, 0),
          10,
          maxDistance: 20,
        );

        // 不应该包含距离为100的节点'd'
        expect(results.any((item) => item.id == 'd'), isFalse);
      });

      test('returns empty for no neighbors in range', () {
        final results = tree.findNearestNeighbors(
          const Offset(500, 500),
          5,
          maxDistance: 50,
        );

        expect(results, isEmpty);
      });
    });

    test('removes items correctly', () {
      final item = SimpleQuadTreeItem(
        id: 'item1',
        position: Offset.zero,
      );

      tree.insert(item);
      expect(tree.totalItemCount, equals(1));

      expect(tree.remove(item), isTrue);
      expect(tree.totalItemCount, equals(0));
    });

    test('clears all items', () {
      for (var i = 0; i < 10; i++) {
        tree.insert(
          SimpleQuadTreeItem(
            id: 'item$i',
            position: Offset(i * 50.0, i * 50.0),
          ),
        );
      }

      expect(tree.totalItemCount, equals(10));

      tree.clear();

      expect(tree.totalItemCount, equals(0));
      expect(tree.isDivided, isFalse);
    });

    test('getAllItems returns all items', () {
      for (var i = 0; i < 10; i++) {
        tree.insert(
          SimpleQuadTreeItem(
            id: 'item$i',
            position: Offset(i * 50.0, i * 50.0),
          ),
        );
      }

      final allItems = tree.getAllItems();

      expect(allItems.length, equals(10));
    });

    test('getStats returns correct statistics', () {
      for (var i = 0; i < 20; i++) {
        tree.insert(
          SimpleQuadTreeItem(
            id: 'item$i',
            position: Offset(i * 50.0, i * 50.0),
          ),
        );
      }

      final stats = tree.getStats();

      expect(stats.totalItems, equals(20));
      expect(stats.nodeCount, greaterThan(0));
      expect(stats.leafCount, greaterThan(0));
    });
  });
}

// 简单的三角函数（测试用）
double _cos(double angle) {
  // 使用泰勒级数近似
  var result = 1.0;
  var term = 1.0;
  for (var i = 1; i <= 10; i++) {
    term *= -angle * angle / (2 * i * (2 * i - 1));
    result += term;
  }
  return result;
}

double _sin(double angle) {
  var result = angle;
  var term = angle;
  for (var i = 1; i <= 10; i++) {
    term *= -angle * angle / (2 * i * (2 * i + 1));
    result += term;
  }
  return result;
}
