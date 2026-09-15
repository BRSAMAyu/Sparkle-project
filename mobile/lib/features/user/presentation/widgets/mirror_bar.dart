import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/user/presentation/models/ws6_profile_mirror_models.dart';

class MirrorBar extends StatelessWidget {
  const MirrorBar({
    required this.model,
    super.key,
  });

  final Ws6MirrorBarModel model;

  @override
  Widget build(BuildContext context) {
    if (model.dimensions.isEmpty) {
      return _buildInertSurface(context);
    }

    final isDark = Theme.of(context).brightness == Brightness.dark;
    final presenceColor = _presenceColor(model.presenceValue, isDark);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            Color.alphaBlend(presenceColor.withValues(alpha: 0.08), DS.surfaceSecondary),
            DS.surfacePrimaryElevated,
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: presenceColor.withValues(alpha: 0.18)),
        boxShadow: [
          BoxShadow(
            color: presenceColor.withValues(alpha: 0.08),
            blurRadius: 20,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _PresenceDot(color: presenceColor),
              const SizedBox(width: DS.spacing8),
              Expanded(
                child: Text(
                  'Aurora Presence · ${model.presenceLabel}',
                  style: DS.labelLarge.copyWith(
                    color: DS.textPrimary,
                    fontWeight: DS.fontWeightSemibold,
                  ),
                ),
              ),
              Text(
                '${(model.presenceValue * 100).round()}%',
                style: DS.labelLarge.copyWith(
                  color: presenceColor,
                  fontWeight: DS.fontWeightBold,
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing12),
          LayoutBuilder(
            builder: (context, constraints) {
              final tileWidth = (constraints.maxWidth - DS.spacing10) / 2;
              return Wrap(
                spacing: DS.spacing10,
                runSpacing: DS.spacing10,
                children: model.dimensions
                    .map(
                      (dimension) => SizedBox(
                        width: tileWidth.isFinite && tileWidth > 0
                            ? tileWidth
                            : constraints.maxWidth,
                        child: _MirrorDimensionTile(dimension: dimension),
                      ),
                    )
                    .toList(),
              );
            },
          ),
          if (model.bindingNotes.isNotEmpty) ...[
            const SizedBox(height: DS.spacing4),
            Text(
              model.bindingNotes.join(' · '),
              style: DS.labelSmall.copyWith(
                color: DS.textSecondary,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildInertSurface(BuildContext context) => Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: DS.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Aurora Presence · gated',
            style: DS.labelLarge.copyWith(
              color: DS.textSecondary,
              fontWeight: DS.fontWeightSemibold,
            ),
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            'Mirror bar is installed but not yet wired to live profile data.',
            style: DS.bodySmall.copyWith(color: DS.textSecondary),
          ),
        ],
      ),
    );

  Color _presenceColor(double value, bool isDark) {
    if (value >= 0.7) {
      return isDark ? DS.success : const Color(0xFF73E0B9);
    }
    if (value >= 0.35) {
      return isDark ? DS.warning : const Color(0xFFF1C27A);
    }
    return isDark ? DS.textSecondary : const Color(0xFF8A8EA8);
  }
}

class _PresenceDot extends StatelessWidget {
  const _PresenceDot({required this.color});

  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        width: 12,
        height: 12,
        decoration: BoxDecoration(
          color: color,
          shape: BoxShape.circle,
          boxShadow: [
            BoxShadow(
              color: color.withValues(alpha: 0.35),
              blurRadius: 12,
              spreadRadius: 1,
            ),
          ],
        ),
      );
}

class _MirrorDimensionTile extends StatelessWidget {
  const _MirrorDimensionTile({
    required this.dimension,
  });

  final Ws6MirrorDimensionModel dimension;

  @override
  Widget build(BuildContext context) {
    final accent = ws6VisibilityColor(dimension.visibility);
    return Container(
      padding: const EdgeInsets.all(DS.spacing10),
      decoration: BoxDecoration(
        color: Color.alphaBlend(
          accent.withValues(alpha: 0.04),
          DS.surfacePrimary.withValues(alpha: 0.88),
        ),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: accent.withValues(alpha: 0.16)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            dimension.label,
            style: DS.bodyMedium.copyWith(
              color: DS.textPrimary,
              fontWeight: DS.fontWeightSemibold,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: DS.spacing2),
          Text(
            dimension.sourceLabel,
            style: DS.labelSmall.copyWith(color: DS.textSecondary),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: DS.spacing6),
          ClipRRect(
            borderRadius: BorderRadius.circular(999),
            child: LinearProgressIndicator(
              value: dimension.value.clamp(0.0, 1.0),
              minHeight: 8,
              backgroundColor: DS.borderSubtle.withValues(alpha: 0.35),
              valueColor: AlwaysStoppedAnimation<Color>(accent),
            ),
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            dimension.subtitle,
            style: DS.bodySmall.copyWith(
              color: DS.textSecondary,
            ),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: DS.spacing4),
          Text(
            [
              dimension.visibility.name,
              if (dimension.canEditDirectly) 'editable',
              if (dimension.canRevert) 'revertable',
            ].join(' · '),
            style: DS.labelSmall.copyWith(color: DS.textSecondary),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }
}
