import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:path_provider/path_provider.dart';
import 'package:sparkle/core/services/universal_share_service.dart';
import 'package:sparkle/features/community/presentation/widgets/share_cards/share_cards.dart';

class SharePosterService {
  factory SharePosterService() => _instance;
  SharePosterService._internal();

  static final SharePosterService _instance = SharePosterService._internal();

  static const Size _posterSize = Size(396, 704);
  static const double _pixelRatio = 3;

  Future<File?> generatePoster(
    BuildContext context,
    UniversalSharePayload payload,
  ) async {
    return runWithoutDebugTextGuides(() async {
      final overlay = Overlay.maybeOf(context, rootOverlay: true);
      if (overlay == null) {
        return null;
      }

      final captureKey = GlobalKey();
      final mediaQuery = MediaQuery.of(context);
      final sanitizedPayload = _sanitizePayload(payload);

      late final OverlayEntry entry;
      entry = OverlayEntry(
        builder: (_) => Positioned.fill(
          child: IgnorePointer(
            child: ExcludeSemantics(
              child: Transform.translate(
                offset: Offset(mediaQuery.size.width * 2, 0),
                child: Align(
                  alignment: Alignment.topLeft,
                  child: MediaQuery(
                    data: mediaQuery.copyWith(
                      size: _posterSize,
                      padding: EdgeInsets.zero,
                      viewPadding: EdgeInsets.zero,
                      viewInsets: EdgeInsets.zero,
                      devicePixelRatio: 1,
                    ),
                    child: Theme(
                      data: Theme.of(context),
                      child: RepaintBoundary(
                        key: captureKey,
                        child: SizedBox(
                          width: _posterSize.width,
                          height: _posterSize.height,
                          child: _SharePosterCanvas(payload: sanitizedPayload),
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      );

      overlay.insert(entry);

      try {
        await WidgetsBinding.instance.endOfFrame;
        await Future<void>.delayed(const Duration(milliseconds: 40));
        await WidgetsBinding.instance.endOfFrame;

        final boundary = captureKey.currentContext?.findRenderObject()
            as RenderRepaintBoundary?;
        if (boundary == null) {
          return null;
        }

        final image = await boundary.toImage(pixelRatio: _pixelRatio);
        final byteData = await image.toByteData(format: ui.ImageByteFormat.png);
        image.dispose();

        if (byteData == null) {
          return null;
        }

        final tempDir = await getTemporaryDirectory();
        final file = File(
          '${tempDir.path}/${sanitizedPayload.contentType.stringValue}_${sanitizedPayload.resourceId}_${sanitizedPayload.templateId}_${DateTime.now().millisecondsSinceEpoch}.png',
        );

        await file.writeAsBytes(
          byteData.buffer.asUint8List(),
          flush: true,
        );

        return file;
      } finally {
        entry.remove();
      }
    });
  }

  @visibleForTesting
  static Future<T> runWithoutDebugTextGuides<T>(
    Future<T> Function() action,
  ) async {
    final previousBaselines = debugPaintBaselinesEnabled;
    debugPaintBaselinesEnabled = false;

    try {
      return await action();
    } finally {
      debugPaintBaselinesEnabled = previousBaselines;
    }
  }

  UniversalSharePayload _sanitizePayload(UniversalSharePayload payload) {
    final metadata = Map<String, dynamic>.from(payload.metadata ?? {});
    final settings = payload.privacySettings;

    if (!settings.showDetailedStats) {
      const detailedKeys = [
        'completed_tasks',
        'total_tasks',
        'milestones',
        'deadline',
        'word_count',
        'learning_time',
        'study_count',
        'share_count',
        'subtasks_completed',
        'subtasks_total',
        'quality_score',
      ];
      for (final key in detailedKeys) {
        metadata.remove(key);
      }
    }

    if (!settings.showProgressPercentage) {
      metadata.remove('progress');
      metadata.remove('mastery');
    }

    return payload.copyWith(metadata: metadata);
  }
}

class _SharePosterCanvas extends StatelessWidget {
  const _SharePosterCanvas({required this.payload});

  final UniversalSharePayload payload;

  @override
  Widget build(BuildContext context) {
    final posterTheme = _PosterThemeData.resolve(
      templateId: payload.templateId,
      contentType: payload.contentType,
    );
    final metrics = _buildMetrics();

    return DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: posterTheme.background,
        ),
      ),
      child: Stack(
        children: [
          ...posterTheme.buildDecorations(),
          Padding(
            padding: const EdgeInsets.fromLTRB(28, 28, 28, 26),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _PosterTopBar(
                  accent: posterTheme.accent,
                  textColor: posterTheme.textPrimary,
                  label: _contentLabel,
                ),
                const SizedBox(height: 24),
                Text(
                  payload.title,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 32,
                    height: 1.08,
                    fontWeight: FontWeight.w800,
                    color: posterTheme.textPrimary,
                    letterSpacing: -0.8,
                  ),
                ),
                if (_summaryText case final summary?)
                  Padding(
                    padding: const EdgeInsets.only(top: 12),
                    child: Text(
                      summary,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 15,
                        height: 1.45,
                        color: posterTheme.textSecondary,
                      ),
                    ),
                  ),
                const SizedBox(height: 20),
                Flexible(
                  fit: FlexFit.loose,
                  child: _PosterCardShell(
                    accent: posterTheme.accent,
                    child: FittedBox(
                      fit: BoxFit.scaleDown,
                      alignment: Alignment.topCenter,
                      child: SizedBox(
                        width: 220,
                        child: Center(
                          child: ShareCardFactory.fromPayload(payload),
                        ),
                      ),
                    ),
                  ),
                ),
                if (metrics.isNotEmpty) ...[
                  const SizedBox(height: 18),
                  Wrap(
                    spacing: 10,
                    runSpacing: 10,
                    children: metrics
                        .map(
                          (metric) => _PosterMetricChip(
                            label: metric.label,
                            value: metric.value,
                            textColor: posterTheme.textPrimary,
                            borderColor: posterTheme.border,
                          ),
                        )
                        .toList(),
                  ),
                ],
                const Spacer(),
                if (_displayName case final displayName?)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 14),
                    child: _PosterIdentity(
                      accent: posterTheme.accent,
                      displayName: displayName,
                      showAvatar: payload.privacySettings.showUserAvatar,
                    ),
                  ),
                Text(
                  '在 Sparkle 继续查看完整内容与成长轨迹',
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: posterTheme.textPrimary,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  payload.deepLink,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 12,
                    color: posterTheme.textSecondary,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  String get _contentLabel => switch (payload.contentType) {
        ShareableContentType.achievement => '成就海报',
        ShareableContentType.taskCompletion => '任务战报',
        ShareableContentType.planProgress => '计划进度',
        ShareableContentType.capsule => '思考胶囊',
        ShareableContentType.knowledgeNode => '知识星点',
        ShareableContentType.learningReport => '学习报告',
        ShareableContentType.cognitivePrism => '认知棱镜',
      };

  String? get _summaryText {
    final source = payload.subtitle?.trim().isNotEmpty == true
        ? payload.subtitle!.trim()
        : payload.description?.trim();
    if (source == null || source.isEmpty) {
      return null;
    }
    return source;
  }

  String? get _displayName {
    if (!payload.privacySettings.showUserName) {
      return null;
    }

    final customName = payload.privacySettings.customDisplayName?.trim();
    if (customName != null && customName.isNotEmpty) {
      return customName;
    }

    return 'Sparkle 学习者';
  }

  List<_PosterMetric> _buildMetrics() {
    final metadata = payload.metadata ?? const <String, dynamic>{};
    final metrics = <_PosterMetric>[];

    void addMetric(String label, Object? value) {
      final normalized = _normalizeMetricValue(value);
      if (normalized == null) {
        return;
      }
      metrics.add(_PosterMetric(label: label, value: normalized));
    }

    switch (payload.contentType) {
      case ShareableContentType.taskCompletion:
        addMetric('投入时长', _durationMinutes(metadata['duration']));
        addMetric('任务类型', metadata['task_type']);
        if (metadata['subtasks_total'] is int &&
            (metadata['subtasks_total'] as int) > 0) {
          addMetric(
            '拆解进度',
            '${metadata['subtasks_completed'] ?? 0}/${metadata['subtasks_total']}',
          );
        }
      case ShareableContentType.planProgress:
        addMetric('当前进度', _percentage(metadata['progress']));
        if (metadata['total_tasks'] is int &&
            (metadata['total_tasks'] as int) > 0) {
          addMetric(
            '任务推进',
            '${metadata['completed_tasks'] ?? 0}/${metadata['total_tasks']}',
          );
        }
        addMetric('学习主题', metadata['subject']);
        addMetric('目标日期', _dateLabel(metadata['deadline']));
      case ShareableContentType.capsule:
        addMetric('思考深度', metadata['depth_label'] ?? metadata['depth']);
        addMetric('字数', _wordCount(metadata['word_count']));
        addMetric('关联主题', metadata['related_subject']);
        addMetric('创建时间', _dateLabel(metadata['created_at']));
      case ShareableContentType.knowledgeNode:
        addMetric('掌握度', _percentage(metadata['mastery']));
        addMetric('所在星域', metadata['category']);
        addMetric('连接数', metadata['connections']);
        addMetric('学习时长', _durationMinutes(metadata['learning_time']));
      case ShareableContentType.achievement:
        addMetric('成就类型', metadata['rarity']);
        addMetric('累计解锁', metadata['unlocked_count']);
        addMetric('当前等级', metadata['flame_level']);
        addMetric('荣耀称号', metadata['equipped_title']);
      case ShareableContentType.learningReport:
        addMetric('报告类型', metadata['report_type']);
        addMetric('活跃计划', metadata['active_plans']);
        addMetric('已解锁成就', metadata['unlocked_achievements']);
        addMetric('成长亮度', metadata['flame_brightness']);
      case ShareableContentType.cognitivePrism:
        addMetric('模式类型', metadata['pattern_type']);
    }

    return metrics.take(3).toList();
  }

  String? _normalizeMetricValue(Object? value) {
    if (value == null) {
      return null;
    }

    if (value is String) {
      final trimmed = value.trim();
      return trimmed.isEmpty ? null : trimmed;
    }

    return value.toString();
  }

  String? _durationMinutes(Object? value) {
    if (value is int && value > 0) {
      return '$value 分钟';
    }
    return null;
  }

  String? _wordCount(Object? value) {
    if (value is int && value > 0) {
      return '$value 字';
    }
    return null;
  }

  String? _percentage(Object? value) {
    if (value is num) {
      final percent = value <= 1 ? value * 100 : value.toDouble();
      return '${percent.toStringAsFixed(0)}%';
    }
    return null;
  }

  String? _dateLabel(Object? value) {
    if (value is String) {
      final parsed = DateTime.tryParse(value);
      if (parsed != null) {
        return '${parsed.month}/${parsed.day}';
      }
    }
    if (value is DateTime) {
      return '${value.month}/${value.day}';
    }
    return null;
  }
}

class _PosterTopBar extends StatelessWidget {
  const _PosterTopBar({
    required this.accent,
    required this.textColor,
    required this.label,
  });

  final Color accent;
  final Color textColor;
  final String label;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        builder: (context, constraints) {
          final compact = constraints.maxWidth < 280;

          final leadingPill = Container(
            constraints: BoxConstraints(
              maxWidth: compact ? constraints.maxWidth : 156,
            ),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(999),
              border: Border.all(
                color: Colors.white.withValues(alpha: 0.18),
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 10,
                  height: 10,
                  decoration: BoxDecoration(
                    color: accent,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 8),
                Flexible(
                  child: Text(
                    'Sparkle Share',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                      color: textColor,
                    ),
                  ),
                ),
              ],
            ),
          );

          final labelPill = Container(
            constraints: BoxConstraints(
              maxWidth: compact ? constraints.maxWidth : 92,
            ),
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
            decoration: BoxDecoration(
              color: accent.withValues(alpha: 0.18),
              borderRadius: BorderRadius.circular(999),
            ),
            child: Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w700,
                color: accent,
              ),
            ),
          );

          if (compact) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                leadingPill,
                const SizedBox(height: 8),
                labelPill,
              ],
            );
          }

          return Row(
            children: [
              Expanded(
                child: Align(
                  alignment: Alignment.centerLeft,
                  child: leadingPill,
                ),
              ),
              const SizedBox(width: 12),
              labelPill,
            ],
          );
        },
      );
}

class _PosterCardShell extends StatelessWidget {
  const _PosterCardShell({
    required this.accent,
    required this.child,
  });

  final Color accent;
  final Widget child;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(28),
          color: Colors.white.withValues(alpha: 0.9),
          border: Border.all(color: accent.withValues(alpha: 0.2)),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.12),
              blurRadius: 28,
              offset: const Offset(0, 20),
            ),
          ],
        ),
        child: child,
      );
}

class _PosterMetricChip extends StatelessWidget {
  const _PosterMetricChip({
    required this.label,
    required this.value,
    required this.textColor,
    required this.borderColor,
  });

  final String label;
  final String value;
  final Color textColor;
  final Color borderColor;

  @override
  Widget build(BuildContext context) => Container(
        constraints: const BoxConstraints(minWidth: 112),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: borderColor),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              label,
              style: TextStyle(
                fontSize: 11,
                color: textColor.withValues(alpha: 0.72),
              ),
            ),
            const SizedBox(height: 4),
            Text(
              value,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w700,
                color: textColor,
              ),
            ),
          ],
        ),
      );
}

class _PosterIdentity extends StatelessWidget {
  const _PosterIdentity({
    required this.accent,
    required this.displayName,
    required this.showAvatar,
  });

  final Color accent;
  final String displayName;
  final bool showAvatar;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          if (showAvatar)
            Container(
              width: 34,
              height: 34,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: LinearGradient(
                  colors: [
                    accent.withValues(alpha: 0.92),
                    accent.withValues(alpha: 0.54),
                  ],
                ),
              ),
              child: Text(
                displayName.substring(0, 1).toUpperCase(),
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
          if (showAvatar) const SizedBox(width: 10),
          Text(
            displayName,
            style: const TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w700,
              color: Colors.white,
            ),
          ),
        ],
      );
}

class _PosterMetric {
  const _PosterMetric({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;
}

class _PosterThemeData {
  const _PosterThemeData({
    required this.background,
    required this.accent,
    required this.textPrimary,
    required this.textSecondary,
    required this.border,
  });

  final List<Color> background;
  final Color accent;
  final Color textPrimary;
  final Color textSecondary;
  final Color border;

  static _PosterThemeData resolve({
    required String templateId,
    required ShareableContentType contentType,
  }) {
    final accent = _accentForContent(contentType);

    return switch (templateId) {
      'minimal' => _PosterThemeData(
          background: const [
            Color(0xFFF8F4EA),
            Color(0xFFE4ECF5),
          ],
          accent: accent,
          textPrimary: const Color(0xFF1C2735),
          textSecondary: const Color(0xFF516172),
          border: const Color(0xFFD7DEE6),
        ),
      'neon' => _PosterThemeData(
          background: const [
            Color(0xFF09111F),
            Color(0xFF161330),
            Color(0xFF0B2533),
          ],
          accent: const Color(0xFF64F7D2),
          textPrimary: Colors.white,
          textSecondary: const Color(0xFFC2D3E0),
          border: Colors.white.withValues(alpha: 0.12),
        ),
      'elegant' => _PosterThemeData(
          background: const [
            Color(0xFF1A1410),
            Color(0xFF322116),
            Color(0xFF6E5430),
          ],
          accent: const Color(0xFFF0C676),
          textPrimary: const Color(0xFFFFF6E8),
          textSecondary: const Color(0xFFE8DAB8),
          border: Colors.white.withValues(alpha: 0.14),
        ),
      _ => _PosterThemeData(
          background: const [
            Color(0xFF121C3B),
            Color(0xFF33245B),
            Color(0xFF0F3B4B),
          ],
          accent: accent,
          textPrimary: Colors.white,
          textSecondary: const Color(0xFFD6E2F2),
          border: Colors.white.withValues(alpha: 0.14),
        ),
    };
  }

  List<Widget> buildDecorations() => [
        Positioned(
          top: -60,
          right: -30,
          child: _GlowBlob(
            size: 220,
            color: accent.withValues(alpha: 0.18),
          ),
        ),
        Positioned(
          bottom: -90,
          left: -50,
          child: _GlowBlob(
            size: 260,
            color: accent.withValues(alpha: 0.14),
          ),
        ),
        Positioned(
          top: 120,
          left: 34,
          child: _SparkDot(color: Colors.white.withValues(alpha: 0.42)),
        ),
        Positioned(
          top: 188,
          right: 38,
          child: _SparkDot(color: accent.withValues(alpha: 0.72), size: 8),
        ),
        Positioned(
          top: 84,
          right: 90,
          child:
              _SparkDot(color: Colors.white.withValues(alpha: 0.26), size: 6),
        ),
      ];

  static Color _accentForContent(ShareableContentType type) => switch (type) {
        ShareableContentType.achievement => const Color(0xFFF9B94B),
        ShareableContentType.taskCompletion => const Color(0xFF4ADE80),
        ShareableContentType.planProgress => const Color(0xFF60A5FA),
        ShareableContentType.capsule => const Color(0xFFD29BFF),
        ShareableContentType.knowledgeNode => const Color(0xFF22D3EE),
        ShareableContentType.learningReport => const Color(0xFFA78BFA),
        ShareableContentType.cognitivePrism => const Color(0xFFF472B6),
      };
}

class _GlowBlob extends StatelessWidget {
  const _GlowBlob({
    required this.size,
    required this.color,
  });

  final double size;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          boxShadow: [
            BoxShadow(
              color: color,
              blurRadius: 80,
              spreadRadius: 12,
            ),
          ],
        ),
      );
}

class _SparkDot extends StatelessWidget {
  const _SparkDot({
    required this.color,
    this.size = 10,
  });

  final Color color;
  final double size;

  @override
  Widget build(BuildContext context) => Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          color: color,
          shape: BoxShape.circle,
          boxShadow: [
            BoxShadow(
              color: color,
              blurRadius: 16,
            ),
          ],
        ),
      );
}
