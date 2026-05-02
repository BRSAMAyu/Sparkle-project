import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/shared/entities/task_model.dart';

class SourceLifecycleBadgeGroup extends StatelessWidget {
  const SourceLifecycleBadgeGroup({
    required this.sources,
    super.key,
    this.compact = false,
    this.maxVisible = 3,
    this.onSwitchSource,
    this.onReselectSource,
    this.onFindSimilar,
  });

  final List<SourceAssetBinding> sources;
  final bool compact;
  final int maxVisible;
  final ValueChanged<SourceAssetBinding>? onSwitchSource;
  final ValueChanged<SourceAssetBinding>? onReselectSource;
  final ValueChanged<SourceAssetBinding>? onFindSimilar;

  @override
  Widget build(BuildContext context) {
    final visible = sources.take(maxVisible).toList();
    if (visible.isEmpty) {
      return const SizedBox.shrink();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (var i = 0; i < visible.length; i++) ...[
          if (i > 0) const SizedBox(height: DS.spacing8),
          SourceLifecycleBadge(
            source: visible[i],
            compact: compact,
            onSwitchSource: onSwitchSource == null
                ? null
                : () => onSwitchSource!(visible[i]),
            onReselectSource: onReselectSource == null
                ? null
                : () => onReselectSource!(visible[i]),
            onFindSimilar:
                onFindSimilar == null ? null : () => onFindSimilar!(visible[i]),
          ),
        ],
      ],
    );
  }
}

class SourceLifecycleBadge extends StatelessWidget {
  const SourceLifecycleBadge({
    required this.source,
    super.key,
    this.compact = false,
    this.onSwitchSource,
    this.onReselectSource,
    this.onFindSimilar,
  });

  final SourceAssetBinding source;
  final bool compact;
  final VoidCallback? onSwitchSource;
  final VoidCallback? onReselectSource;
  final VoidCallback? onFindSimilar;

  @override
  Widget build(BuildContext context) {
    final spec = _SourceLifecycleSpec.from(source.lifecycleStatus);
    final zh = I18nService.instance.isChinese;
    final title = source.title.trim().isEmpty
        ? (zh ? '未命名来源' : 'Untitled Source')
        : source.title.trim();
    final action = _actionForStatus(zh);

    return Semantics(
      label: '${spec.label(zh)} $title',
      child: Container(
        width: double.infinity,
        padding: EdgeInsets.all(compact ? DS.spacing10 : DS.spacing12),
        decoration: BoxDecoration(
          color: spec.color.withValues(alpha: 0.09),
          borderRadius: DS.borderRadius12,
          border: Border.all(color: spec.color.withValues(alpha: 0.24)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(spec.icon, size: compact ? 16 : 18, color: spec.color),
                const SizedBox(width: DS.spacing8),
                Expanded(
                  child: Wrap(
                    crossAxisAlignment: WrapCrossAlignment.center,
                    spacing: DS.spacing8,
                    runSpacing: DS.spacing4,
                    children: [
                      _StatusPill(spec: spec, zh: zh),
                      Text(
                        title,
                        maxLines: compact ? 1 : 2,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              color: DS.textPrimary,
                              fontWeight: DS.fontWeightBold,
                            ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            if (!compact && spec.warning(zh).isNotEmpty) ...[
              const SizedBox(height: DS.spacing8),
              Text(
                spec.warning(zh),
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.textSecondary,
                      height: 1.35,
                    ),
              ),
            ],
            if (!compact && action != null) ...[
              const SizedBox(height: DS.spacing10),
              Align(
                alignment: Alignment.centerLeft,
                child: SparkleButton(
                  label: action.label,
                  size: ButtonSize.small,
                  variant: ButtonVariant.ghost,
                  icon: Icon(action.icon),
                  onPressed: action.onPressed,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  _SourceAction? _actionForStatus(bool zh) {
    switch (source.lifecycleStatus) {
      case SourceLifecycleStatus.active:
        return null;
      case SourceLifecycleStatus.archived:
        return _SourceAction(
          label: zh ? '切换替代来源' : 'Switch Source',
          icon: Icons.swap_horiz_rounded,
          onPressed: onSwitchSource ?? () {},
        );
      case SourceLifecycleStatus.revoked:
        return _SourceAction(
          label: zh ? '重新选择' : 'Choose Again',
          icon: Icons.folder_open_rounded,
          onPressed: onReselectSource ?? () {},
        );
      case SourceLifecycleStatus.orphaned:
        return _SourceAction(
          label: zh ? '查找类似' : 'Find Similar',
          icon: Icons.manage_search_rounded,
          onPressed: onFindSimilar ?? () {},
        );
    }
  }
}

class _StatusPill extends StatelessWidget {
  const _StatusPill({required this.spec, required this.zh});

  final _SourceLifecycleSpec spec;
  final bool zh;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing4,
        ),
        decoration: BoxDecoration(
          color: spec.color.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: spec.color.withValues(alpha: 0.28)),
        ),
        child: Text(
          spec.label(zh),
          style: TextStyle(
            color: spec.color,
            fontSize: DS.fontSizeXs,
            fontWeight: DS.fontWeightBold,
          ),
        ),
      );
}

class _SourceLifecycleSpec {
  const _SourceLifecycleSpec({
    required this.color,
    required this.icon,
    required this.labelZh,
    required this.labelEn,
    this.warningZh = '',
    this.warningEn = '',
  });

  factory _SourceLifecycleSpec.from(SourceLifecycleStatus status) {
    switch (status) {
      case SourceLifecycleStatus.active:
        return _SourceLifecycleSpec(
          color: DS.success,
          icon: Icons.link_rounded,
          labelZh: '已绑定',
          labelEn: 'Bound',
        );
      case SourceLifecycleStatus.archived:
        return _SourceLifecycleSpec(
          color: DS.textSecondary,
          icon: Icons.archive_outlined,
          labelZh: '已归档',
          labelEn: 'Archived',
          warningZh: '这个任务引用的来源已归档，后续解释可能需要替代资料。',
          warningEn:
              'This task references an archived source and may need a replacement.',
        );
      case SourceLifecycleStatus.revoked:
        return _SourceLifecycleSpec(
          color: DS.error,
          icon: Icons.warning_amber_rounded,
          labelZh: '来源已撤销',
          labelEn: 'Source Revoked',
          warningZh: '这个来源不再可用，执行前建议重新选择可信资料。',
          warningEn:
              'This source is no longer available. Choose a trusted source before execution.',
        );
      case SourceLifecycleStatus.orphaned:
        return _SourceLifecycleSpec(
          color: DS.warning,
          icon: Icons.link_off_rounded,
          labelZh: '来源失联',
          labelEn: 'Source Missing',
          warningZh: '这个来源和原始文件失去关联，可以查找相似资料继续任务。',
          warningEn:
              'This source lost its original file link. Find similar material to continue.',
        );
    }
  }

  final Color color;
  final IconData icon;
  final String labelZh;
  final String labelEn;
  final String warningZh;
  final String warningEn;

  String label(bool zh) => zh ? labelZh : labelEn;
  String warning(bool zh) => zh ? warningZh : warningEn;
}

class _SourceAction {
  const _SourceAction({
    required this.label,
    required this.icon,
    required this.onPressed,
  });

  final String label;
  final IconData icon;
  final VoidCallback onPressed;
}
