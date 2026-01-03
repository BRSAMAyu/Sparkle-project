import 'dart:math';
import 'package:flutter/foundation.dart';

/// A simple point data structure for QuadTree
class QTPoint {

  QTPoint(this.x, this.y, this.data);
  final double x;
  final double y;
  final dynamic data;
}

/// A boundary region for QuadTree
class QTRect { // half height

  QTRect(this.x, this.y, this.w, this.h);
  final double x; // center x
  final double y; // center y
  final double w; // half width
  final double h;

  bool contains(QTPoint point) => (point.x >= x - w &&
        point.x <= x + w &&
        point.y >= y - h &&
        point.y <= y + h);

  bool intersects(QTRect range) => !(range.x - range.w > x + w ||
        range.x + range.w < x - w ||
        range.y - range.h > y + h ||
        range.y + range.h < y - h);
}

/// QuadTree implementation for spatial indexing
class QuadTree {

  QuadTree(this.boundary, this.capacity, [this.depth = 0]);
  static const int MAX_DEPTH = 10; // Prevent infinite recursion
  
  final QTRect boundary;
  final int capacity;
  final int depth;
  final List<QTPoint> points = [];
  bool divided = false;
  
  QuadTree? northwest;
  QuadTree? northeast;
  QuadTree? southwest;
  QuadTree? southeast;

  /// Insert a point into the QuadTree
  bool insert(QTPoint point) {
    if (!boundary.contains(point)) {
      return false;
    }

    // Stop subdividing if capacity reached BUT max depth also reached
    // This handles "stacking" points at same coordinate gracefully
    if (points.length < capacity || depth >= MAX_DEPTH) {
      points.add(point);
      return true;
    } else {
      if (!divided) {
        subdivide();
      }

      if (northwest!.insert(point)) return true;
      if (northeast!.insert(point)) return true;
      if (southwest!.insert(point)) return true;
      if (southeast!.insert(point)) return true;
      
      return false; // Should not happen
    }
  }

  /// Subdivide the tree into 4 quadrants
  void subdivide() {
    var x = boundary.x;
    var y = boundary.y;
    var w = boundary.w / 2;
    var h = boundary.h / 2;

    northwest = QuadTree(QTRect(x - w, y - h, w, h), capacity, depth + 1);
    northeast = QuadTree(QTRect(x + w, y - h, w, h), capacity, depth + 1);
    southwest = QuadTree(QTRect(x - w, y + h, w, h), capacity, depth + 1);
    southeast = QuadTree(QTRect(x + w, y + h, w, h), capacity, depth + 1);
    
    divided = true;
  }

  /// Query points within a range
  List<QTPoint> query(QTRect range, [List<QTPoint>? found]) {
    found ??= [];

    if (!boundary.intersects(range)) {
      return found;
    }

    for (final p in points) {
      if (range.contains(p)) {
        found.add(p);
      }
    }

    if (divided) {
      northwest!.query(range, found);
      northeast!.query(range, found);
      southwest!.query(range, found);
      southeast!.query(range, found);
    }

    return found;
  }
  
  /// Find closest point to target within maxDistance
  QTPoint? queryClosest(double x, double y, double maxDistance) {
    // Optimization: First query a range
    final range = QTRect(x, y, maxDistance, maxDistance);
    final candidates = query(range);
    
    QTPoint? closest;
    var minDstSq = maxDistance * maxDistance;
    
    for (final p in candidates) {
      final dstSq = pow(p.x - x, 2) + pow(p.y - y, 2);
      if (dstSq <= minDstSq) {
        minDstSq = dstSq;
        closest = p;
      }
    }
    
    return closest;
  }
  
  /// Clear the tree
  void clear() {
    points.clear();
    divided = false;
    northwest = null;
    northeast = null;
    southwest = null;
    southeast = null;
  }
}
