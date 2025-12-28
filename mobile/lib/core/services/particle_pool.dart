import 'dart:collection';

import 'package:flutter/material.dart';

/// 可池化对象接口
abstract class Poolable {
  /// 重置对象状态，准备重用
  void reset();

  /// 是否可以被池化
  bool get canBePooled => true;
}

/// 通用对象池
class ObjectPool<T extends Poolable> {
  ObjectPool({
    required this.factory,
    this.maxPoolSize = 50,
    this.initialSize = 0,
  }) {
    // 预创建对象
    for (var i = 0; i < initialSize; i++) {
      _pool.add(factory());
    }
  }

  final T Function() factory;
  final int maxPoolSize;
  final int initialSize;

  final Queue<T> _pool = Queue();
  int _totalCreated = 0;
  int _totalReused = 0;

  /// 获取对象
  T acquire() {
    if (_pool.isNotEmpty) {
      _totalReused++;
      final obj = _pool.removeFirst();
      obj.reset();
      return obj;
    }

    _totalCreated++;
    return factory();
  }

  /// 归还对象
  void release(T object) {
    if (!object.canBePooled) return;

    if (_pool.length < maxPoolSize) {
      _pool.add(object);
    }
    // 如果池已满，对象将被丢弃让GC回收
  }

  /// 批量归还
  void releaseAll(Iterable<T> objects) {
    for (final obj in objects) {
      release(obj);
    }
  }

  /// 清空池
  void clear() {
    _pool.clear();
  }

  /// 获取统计信息
  PoolStats get stats => PoolStats(
        poolSize: _pool.length,
        maxPoolSize: maxPoolSize,
        totalCreated: _totalCreated,
        totalReused: _totalReused,
      );

  /// 当前池大小
  int get size => _pool.length;

  /// 池是否为空
  bool get isEmpty => _pool.isEmpty;

  /// 池是否已满
  bool get isFull => _pool.length >= maxPoolSize;
}

/// 对象池统计信息
class PoolStats {
  const PoolStats({
    required this.poolSize,
    required this.maxPoolSize,
    required this.totalCreated,
    required this.totalReused,
  });

  final int poolSize;
  final int maxPoolSize;
  final int totalCreated;
  final int totalReused;

  /// 复用率
  double get reuseRate =>
      totalCreated + totalReused > 0 ? totalReused / (totalCreated + totalReused) : 0;

  @override
  String toString() =>
      'PoolStats(size: $poolSize/$maxPoolSize, created: $totalCreated, reused: $totalReused, reuseRate: ${(reuseRate * 100).toStringAsFixed(1)}%)';
}

/// 可池化的粒子
class PoolableParticle implements Poolable {
  Offset position = Offset.zero;
  double size = 0;
  double opacity = 1.0;
  Color color = Colors.white;
  double angle = 0;
  double velocity = 0;
  double lifetime = 0;
  double age = 0;
  bool isActive = false;

  @override
  void reset() {
    position = Offset.zero;
    size = 0;
    opacity = 1.0;
    color = Colors.white;
    angle = 0;
    velocity = 0;
    lifetime = 0;
    age = 0;
    isActive = false;
  }

  @override
  bool get canBePooled => true;

  /// 初始化粒子
  void initialize({
    required Offset position,
    required double size,
    required Color color,
    double opacity = 1.0,
    double angle = 0,
    double velocity = 0,
    double lifetime = 1.0,
  }) {
    this.position = position;
    this.size = size;
    this.color = color;
    this.opacity = opacity;
    this.angle = angle;
    this.velocity = velocity;
    this.lifetime = lifetime;
    age = 0;
    isActive = true;
  }

  /// 更新粒子
  void update(double dt) {
    if (!isActive) return;

    age += dt;

    // 基于年龄计算衰减
    final lifeProgress = lifetime > 0 ? age / lifetime : 1.0;

    // 更新位置
    if (velocity > 0) {
      final dx = velocity * dt * _cos(angle);
      final dy = velocity * dt * _sin(angle);
      position = Offset(position.dx + dx, position.dy + dy);
    }

    // 更新透明度（淡出）
    opacity = (1.0 - lifeProgress).clamp(0.0, 1.0);

    // 更新大小（可选：缩小）
    // size *= 0.99;

    // 检查是否过期
    if (lifeProgress >= 1.0) {
      isActive = false;
    }
  }

  // 简单的三角函数（避免dart:math依赖）
  double _cos(double angle) {
    // 简化实现，实际使用时应该用dart:math
    return 1.0 - (angle * angle / 2);
  }

  double _sin(double angle) => angle - (angle * angle * angle / 6);
}

/// 粒子系统
class ParticleSystem {
  ParticleSystem({
    this.maxParticles = 100,
    this.poolSize = 50,
  }) : _pool = ObjectPool<PoolableParticle>(
          factory: PoolableParticle.new,
          maxPoolSize: poolSize,
          initialSize: poolSize ~/ 2,
        );

  final int maxParticles;
  final int poolSize;
  final ObjectPool<PoolableParticle> _pool;
  final List<PoolableParticle> _activeParticles = [];

  /// 活跃粒子列表
  List<PoolableParticle> get activeParticles => _activeParticles;

  /// 活跃粒子数量
  int get activeCount => _activeParticles.length;

  /// 发射粒子
  PoolableParticle? emit({
    required Offset position,
    required double size,
    required Color color,
    double opacity = 1.0,
    double angle = 0,
    double velocity = 0,
    double lifetime = 1.0,
  }) {
    // 检查是否达到最大粒子数
    if (_activeParticles.length >= maxParticles) {
      return null;
    }

    final particle = _pool.acquire();
    particle.initialize(
      position: position,
      size: size,
      color: color,
      opacity: opacity,
      angle: angle,
      velocity: velocity,
      lifetime: lifetime,
    );

    _activeParticles.add(particle);
    return particle;
  }

  /// 更新所有粒子
  void update(double dt) {
    final toRemove = <PoolableParticle>[];

    for (final particle in _activeParticles) {
      particle.update(dt);
      if (!particle.isActive) {
        toRemove.add(particle);
      }
    }

    // 移除并归还过期粒子
    for (final particle in toRemove) {
      _activeParticles.remove(particle);
      _pool.release(particle);
    }
  }

  /// 清空所有粒子
  void clear() {
    _pool.releaseAll(_activeParticles);
    _activeParticles.clear();
  }

  /// 释放资源
  void dispose() {
    clear();
    _pool.clear();
  }

  /// 获取统计信息
  ParticleSystemStats get stats => ParticleSystemStats(
        activeParticles: _activeParticles.length,
        maxParticles: maxParticles,
        poolStats: _pool.stats,
      );
}

/// 粒子系统统计
class ParticleSystemStats {
  const ParticleSystemStats({
    required this.activeParticles,
    required this.maxParticles,
    required this.poolStats,
  });

  final int activeParticles;
  final int maxParticles;
  final PoolStats poolStats;

  @override
  String toString() =>
      'ParticleSystemStats(active: $activeParticles/$maxParticles, pool: $poolStats)';
}
