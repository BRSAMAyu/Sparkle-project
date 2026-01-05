import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:sparkle/core/services/smart_cache.dart';

/// 文本位图缓存 - 避免重复TextPainter计算
///
/// 功能:
/// 1. 缓存渲染后的文本图像
/// 2. LRU淘汰策略
/// 3. 支持不同样式的文本
class TextImageCache {
  TextImageCache({
    this.maxSize = 100,
    this.maxAge = const Duration(minutes: 10),
  }) : _cache = SmartCache<String, _CachedTextImage>(
          maxSize: maxSize,
          maxAge: maxAge,
          onEvicted: (key, value) {
            // 释放图像资源
            value.image.dispose();
          },
        );

  final int maxSize;
  final Duration maxAge;
  final SmartCache<String, _CachedTextImage> _cache;

  /// 获取或创建文本图像
  Future<ui.Image?> getTextImage(
    String text,
    TextStyle style, {
    double maxWidth = double.infinity,
  }) async {
    final key = _generateKey(text, style, maxWidth);

    // 检查缓存
    final cached = _cache.get(key);
    if (cached != null) {
      return cached.image;
    }

    // 生成新图像
    final image = await _renderTextToImage(text, style, maxWidth);
    if (image != null) {
      _cache.set(key, _CachedTextImage(image: image));
    }

    return image;
  }

  /// 同步获取TextPainter（用于布局计算）
  TextPainter getTextPainter(
    String text,
    TextStyle style, {
    double maxWidth = double.infinity,
    TextDirection textDirection = TextDirection.ltr,
  }) {
    final textPainter = TextPainter(
      text: TextSpan(text: text, style: style),
      textDirection: textDirection,
    );
    textPainter.layout(maxWidth: maxWidth);
    return textPainter;
  }

  /// 渲染文本到图像
  Future<ui.Image?> _renderTextToImage(
    String text,
    TextStyle style,
    double maxWidth,
  ) async {
    try {
      final recorder = ui.PictureRecorder();
      final canvas = Canvas(recorder);

      final textPainter = TextPainter(
        text: TextSpan(text: text, style: style),
        textDirection: TextDirection.ltr,
      );
      textPainter.layout(maxWidth: maxWidth);
      textPainter.paint(canvas, Offset.zero);

      final picture = recorder.endRecording();

      // 添加一些padding避免裁剪
      final width = (textPainter.width + 2).ceil();
      final height = (textPainter.height + 2).ceil();

      if (width <= 0 || height <= 0) {
        return null;
      }

      final image = await picture.toImage(width, height);
      return image;
    } catch (e) {
      debugPrint('TextImageCache: Failed to render text image: $e');
      return null;
    }
  }

  /// 生成缓存key
  String _generateKey(String text, TextStyle style, double maxWidth) {
    // 包含影响渲染的所有属性
    return '${text.hashCode}_'
        '${style.fontSize}_'
        '${style.fontWeight?.index}_'
        '${style.fontStyle?.index}_'
        '${style.color?.value}_'
        '${style.fontFamily}_'
        '${maxWidth.toStringAsFixed(0)}';
  }

  /// 预热缓存
  Future<void> warmUp(List<TextCacheEntry> entries) async {
    for (final entry in entries) {
      await getTextImage(entry.text, entry.style, maxWidth: entry.maxWidth);
    }
  }

  /// 清空缓存
  void clear() {
    _cache.clear();
  }

  /// 获取缓存统计
  CacheStats get stats => _cache.stats;

  /// 释放资源
  void dispose() {
    clear();
  }
}

class _CachedTextImage {
  _CachedTextImage({required this.image});

  final ui.Image image;
}

/// 缓存预热条目
class TextCacheEntry {
  const TextCacheEntry({
    required this.text,
    required this.style,
    this.maxWidth = double.infinity,
  });

  final String text;
  final TextStyle style;
  final double maxWidth;
}

/// 批量文本渲染器 - 用于批量渲染节点标签
class BatchTextRenderer {
  BatchTextRenderer({
    this.cacheEnabled = true,
    this.maxCacheSize = 200,
  }) : _cache = cacheEnabled ? TextImageCache(maxSize: maxCacheSize) : null;

  final bool cacheEnabled;
  final int maxCacheSize;
  final TextImageCache? _cache;

  // TextPainter缓存（同步使用）
  final Map<String, TextPainter> _painterCache = {};

  /// 获取TextPainter（同步，用于绘制）
  TextPainter getTextPainter(
    String text,
    TextStyle style, {
    double maxWidth = double.infinity,
  }) {
    final key = '${text}_${style.hashCode}_$maxWidth';

    if (_painterCache.containsKey(key)) {
      return _painterCache[key]!;
    }

    final painter = TextPainter(
      text: TextSpan(text: text, style: style),
      textDirection: TextDirection.ltr,
    );
    painter.layout(maxWidth: maxWidth);

    // 限制缓存大小
    if (_painterCache.length >= maxCacheSize) {
      // 移除最早的条目
      final firstKey = _painterCache.keys.first;
      _painterCache.remove(firstKey);
    }

    _painterCache[key] = painter;
    return painter;
  }

  /// 直接绘制文本到Canvas
  void drawText(
    Canvas canvas,
    String text,
    Offset position,
    TextStyle style, {
    double maxWidth = double.infinity,
    TextAlign align = TextAlign.center,
  }) {
    final painter = getTextPainter(text, style, maxWidth: maxWidth);

    // 根据对齐调整位置
    var actualPosition = position;
    if (align == TextAlign.center) {
      actualPosition = Offset(
        position.dx - painter.width / 2,
        position.dy,
      );
    } else if (align == TextAlign.right) {
      actualPosition = Offset(
        position.dx - painter.width,
        position.dy,
      );
    }

    painter.paint(canvas, actualPosition);
  }

  /// 获取文本尺寸
  Size getTextSize(String text, TextStyle style,
      {double maxWidth = double.infinity,}) {
    final painter = getTextPainter(text, style, maxWidth: maxWidth);
    return Size(painter.width, painter.height);
  }

  /// 清空缓存
  void clear() {
    _painterCache.clear();
    _cache?.clear();
  }

  /// 释放资源
  void dispose() {
    clear();
    _cache?.dispose();
  }

  /// 获取统计信息
  Map<String, dynamic> get stats => {
        'painterCacheSize': _painterCache.length,
        'imageCacheStats': _cache?.stats.toString() ?? 'disabled',
      };
}

/// 全局文本缓存实例
class GlobalTextCache {
  GlobalTextCache._();

  static final GlobalTextCache instance = GlobalTextCache._();

  late final BatchTextRenderer _renderer = BatchTextRenderer();

  BatchTextRenderer get renderer => _renderer;

  void dispose() {
    _renderer.dispose();
  }
}
