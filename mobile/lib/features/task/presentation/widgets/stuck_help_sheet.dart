import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/shared/entities/task_model.dart';

class StuckHelpSheet extends StatelessWidget {
  const StuckHelpSheet({
    required this.task,
    super.key,
    this.onChatPressed,
  });

  final TaskModel task;
  final VoidCallback? onChatPressed;

  static const List<String> genericSuggestions = [
    '把卡住的具体位置写下来',
    '换一个更小的子问题',
    '先完成你确实会的部分',
    '给自己限时5分钟',
    '标记这个点，继续其他部分',
  ];

  @override
  Widget build(BuildContext context) {
    final fallbackLevels = _readFallbackLevels(
      task.guideJson?['fallback_if_stuck'],
    );
    final ifStuck = _readList(task.guideJson?['if_stuck']);
    final suggestions = ifStuck.isNotEmpty ? ifStuck : genericSuggestions;

    return DraggableScrollableSheet(
      initialChildSize: 0.68,
      minChildSize: 0.42,
      maxChildSize: 0.92,
      builder: (context, scrollController) => GraphiteModalSurface(
        title: '别担心，我们来看看卡在哪里',
        expandChild: true,
        child: SingleChildScrollView(
          controller: scrollController,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                task.title,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: DS.bodySmall.copyWith(
                  color: DS.textSecondary,
                  height: 1.45,
                ),
              ),
              const SizedBox(height: DS.spacing20),
              _SheetSection(
                title: fallbackLevels.isNotEmpty ? '卡住时按这个顺序救火' : '具体该怎么做',
                child: fallbackLevels.isNotEmpty
                    ? Column(
                        children: [
                          for (final level in fallbackLevels)
                            _FallbackLevelCard(level: level),
                        ],
                      )
                    : Column(
                        children: [
                          for (var index = 0;
                              index < suggestions.length;
                              index++)
                            _SuggestionRow(
                              number: index + 1,
                              text: suggestions[index],
                            ),
                        ],
                      ),
              ),
              const SizedBox(height: DS.spacing20),
              _SheetSection(
                title: '要不要让AI来看看？',
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '可以把当前任务和卡点一起带过去，让 Sparkle 先帮你拆成更小的问题。',
                      style: DS.bodySmall.copyWith(
                        color: DS.textSecondary,
                        height: 1.45,
                      ),
                    ),
                    const SizedBox(height: DS.spacing12),
                    SizedBox(
                      width: double.infinity,
                      child: SparkleButton(
                        label: '和Sparkle聊聊这个问题',
                        icon: const Icon(
                          Icons.forum_outlined,
                        ),
                        onPressed: onChatPressed,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: DS.spacing16),
            ],
          ),
        ),
      ),
    );
  }
}

class _SheetSection extends StatelessWidget {
  const _SheetSection({
    required this.title,
    required this.child,
  });

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: DS.titleMedium.copyWith(
              color: DS.textPrimary,
              fontWeight: DS.fontWeightBold,
            ),
          ),
          const SizedBox(height: DS.spacing12),
          child,
        ],
      );
}

class _SuggestionRow extends StatelessWidget {
  const _SuggestionRow({
    required this.number,
    required this.text,
  });

  final int number;
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: DS.spacing10),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 26,
              height: 26,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: DS.primaryBase.withValues(alpha: 0.10),
                shape: BoxShape.circle,
              ),
              child: Text(
                '$number',
                style: DS.bodySmall.copyWith(
                  color: DS.primaryBase,
                  fontWeight: DS.fontWeightBold,
                ),
              ),
            ),
            const SizedBox(width: DS.spacing10),
            Expanded(
              child: Text(
                text,
                style: DS.bodyMedium.copyWith(
                  color: DS.textPrimary,
                  height: 1.45,
                ),
              ),
            ),
          ],
        ),
      );
}

class _FallbackLevelCard extends StatelessWidget {
  const _FallbackLevelCard({required this.level});

  final _FallbackLevelData level;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        margin: const EdgeInsets.only(bottom: DS.spacing12),
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary.withValues(alpha: 0.72),
          borderRadius: BorderRadius.circular(DS.borderRadiusLG),
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Level ${level.level} · ${level.title}',
              style: DS.bodyMedium.copyWith(
                color: DS.textPrimary,
                fontWeight: DS.fontWeightBold,
              ),
            ),
            const SizedBox(height: DS.spacing8),
            for (var index = 0; index < level.guidance.length; index++)
              _SuggestionRow(
                number: index + 1,
                text: level.guidance[index],
              ),
          ],
        ),
      );
}

class _FallbackLevelData {
  const _FallbackLevelData({
    required this.level,
    required this.title,
    required this.guidance,
  });

  final int level;
  final String title;
  final List<String> guidance;
}

List<_FallbackLevelData> _readFallbackLevels(Object? value) {
  if (value is! Iterable) return const [];
  final levels = <_FallbackLevelData>[];
  for (final item in value) {
    if (item is! Map) continue;
    final title = (item['title'] ?? item['label'] ?? '').toString().trim();
    final level = item['level'] is num
        ? (item['level'] as num).toInt()
        : int.tryParse(item['level']?.toString() ?? '') ?? levels.length + 1;
    final guidance = _readList(item['guidance'] ?? item['content']);
    if (title.isEmpty || guidance.isEmpty) continue;
    levels.add(
      _FallbackLevelData(
        level: level,
        title: title,
        guidance: guidance,
      ),
    );
  }
  return levels;
}

List<String> _readList(Object? value) {
  if (value == null) return const [];
  if (value is Iterable) {
    return value
        .map((item) => item?.toString().trim() ?? '')
        .where((item) => item.isNotEmpty)
        .toList(growable: false);
  }
  final text = value.toString().trim();
  if (text.isEmpty) return const [];
  return text
      .split(RegExp(r'[\n；;]+'))
      .map((item) => item.trim())
      .where((item) => item.isNotEmpty)
      .toList(growable: false);
}
