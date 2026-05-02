// ignore_for_file: prefer_expression_function_bodies

import 'package:flutter/material.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/user/data/repositories/user_repository.dart';
import 'package:sparkle/features/user/presentation/models/ws6_profile_mirror_models.dart';
import 'package:sparkle/features/user/presentation/providers/profile_context_provider.dart';
import 'package:sparkle/features/user/presentation/providers/ws6_profile_mirror_provider.dart';
import 'package:sparkle/features/user/presentation/widgets/mirror_bar.dart';
import 'package:sparkle/features/user/presentation/ws6_flags.dart';

class ProfileTransparentScreen extends ConsumerWidget {
  const ProfileTransparentScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final viewAsync = ref.watch(ws6TransparentProfileViewProvider);
    Future<void> submitInsightControl({
      required String targetId,
      required String action,
      String? reason,
    }) async {
      await ref.read(userRepositoryProvider).submitInsightControl({
        'target_id': targetId,
        'action': action,
        if (reason != null && reason.trim().isNotEmpty) 'reason': reason.trim(),
      });
      ref.invalidate(profileContextProvider);
      ref.invalidate(ws6TransparentProfileViewProvider);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SparkleSnackBar.success(I18nService.instance.isChinese ? '已记录「$targetId」的画像调整。' : 'Recorded profile adjustment for "$targetId".'),
        );
      }
    }

    return GraphiteScaffold(
      role: SparklePageRole.settings,
      safeArea: false,
      child: viewAsync.when(
        data: (view) => RefreshIndicator(
          onRefresh: () async {
            ref.invalidate(ws6TransparentProfileViewProvider);
            await ref.read(ws6TransparentProfileViewProvider.future);
          },
          child: ListView(
            padding: const EdgeInsets.all(DS.spacing16),
            children: [
              _buildHeader(context, view),
              const SizedBox(height: DS.spacing12),
              MirrorBar(model: view.mirrorBar),
              const SizedBox(height: DS.spacing12),
              _buildSummaryCard(context, view),
              const SizedBox(height: DS.spacing12),
              _buildItemSection(
                context,
                title: context.l10n.userVisibleProfile,
                subtitle: context.l10n.userVisibleProfileHint,
                items: view.visibleItems,
                onMarkWrong: (item) => submitInsightControl(
                  targetId: item.key,
                  action: 'wrong',
                  reason: 'Submitted from transparent profile surface.',
                ),
                onExamModeOnly: (item) => submitInsightControl(
                  targetId: item.key,
                  action: 'exam_mode_only',
                ),
              ),
              const SizedBox(height: DS.spacing12),
              _buildItemSection(
                context,
                title: context.l10n.userMediatedProfile,
                subtitle: context.l10n.userMediatedProfileHint,
                items: view.mediatedItems,
                onMarkWrong: (item) => submitInsightControl(
                  targetId: item.key,
                  action: 'wrong',
                  reason: 'Submitted from transparent profile surface.',
                ),
              ),
              const SizedBox(height: DS.spacing12),
              _buildRevertSection(
                context,
                view,
                onMarkWrong: (action) => submitInsightControl(
                  targetId: action.key,
                  action: 'wrong',
                  reason: action.reason,
                ),
              ),
              const SizedBox(height: DS.spacing12),
              _buildCorrectionHistorySection(
                context,
                view,
                onUndo: (item) => submitInsightControl(
                  targetId: item.targetId,
                  action: 'reset_override',
                  reason: 'User reverted a previous Aurora correction.',
                ),
              ),
              const SizedBox(height: DS.spacing12),
              _buildBindingCard(context, view),
              const SizedBox(height: 24),
            ],
          ),
        ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => _buildOfflineFallback(context),
      ),
    );
  }

  Widget _buildHeader(
      BuildContext context, Ws6TransparentProfileViewModel view) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                context.l10n.userTransparentProfile,
                style: DS.titleLarge.copyWith(
                  color: DS.textPrimary,
                  fontWeight: DS.fontWeightBold,
                ),
              ),
              const SizedBox(height: DS.spacing4),
              Text(
                view.summary,
                style: DS.bodyMedium.copyWith(color: DS.textSecondary),
              ),
            ],
          ),
        ),
        const SizedBox(width: DS.spacing8),
        const _ModePill(
          label: kWs6ProfileSurfaceEnabled ? 'live' : 'gated',
          color:
              kWs6ProfileSurfaceEnabled ? Color(0xFF73E0B9) : Color(0xFF8A8EA8),
        ),
      ],
    );
  }

  Widget _buildSummaryCard(
    BuildContext context,
    Ws6TransparentProfileViewModel view,
  ) {
    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.panel,
      padding: const EdgeInsets.all(DS.spacing16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.userSummary,
            style: DS.labelLarge.copyWith(
              color: DS.textPrimary,
              fontWeight: DS.fontWeightSemibold,
            ),
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            view.summary,
            style: DS.bodyMedium.copyWith(color: DS.textPrimary),
          ),
          if (view.calibrationPosture.isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            Text(
              'Calibration posture: ${view.calibrationPosture}',
              style: DS.labelSmall.copyWith(color: DS.textSecondary),
            ),
          ],
          if (view.unknowns.isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            Text(
              context.l10n.userCurrentUnknowns,
              style: DS.labelSmall.copyWith(
                color: DS.textPrimary,
                fontWeight: DS.fontWeightSemibold,
              ),
            ),
            const SizedBox(height: DS.spacing4),
            ...view.unknowns.take(3).map(
                  (item) => Padding(
                    padding: const EdgeInsets.only(bottom: DS.spacing4),
                    child: Text(
                      '• $item',
                      style: DS.bodySmall.copyWith(color: DS.textSecondary),
                    ),
                  ),
                ),
          ],
          if (view.hiddenItemCount > 0) ...[
            const SizedBox(height: DS.spacing8),
            Text(
              I18nService.instance.isChinese ? '隐藏条目 ${view.hiddenItemCount} 条，未进入透明面板。' : '${view.hiddenItemCount} hidden items, not shown on transparent profile.',
              style: DS.labelSmall.copyWith(color: DS.textSecondary),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildItemSection(
    BuildContext context, {
    required String title,
    required String subtitle,
    required List<Ws6TransparentProfileItemModel> items,
    Future<void> Function(Ws6TransparentProfileItemModel item)? onMarkWrong,
    Future<void> Function(Ws6TransparentProfileItemModel item)? onExamModeOnly,
  }) {
    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.panel,
      padding: const EdgeInsets.all(DS.spacing16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: DS.labelLarge.copyWith(
              color: DS.textPrimary,
              fontWeight: DS.fontWeightSemibold,
            ),
          ),
          const SizedBox(height: DS.spacing4),
          Text(
            subtitle,
            style: DS.bodySmall.copyWith(color: DS.textSecondary),
          ),
          const SizedBox(height: DS.spacing12),
          if (items.isEmpty)
            Text(
              context.l10n.userNoContent,
              style: DS.bodySmall.copyWith(color: DS.textSecondary),
            )
          else
            ...items.map(
              (item) => Padding(
                padding: const EdgeInsets.only(bottom: DS.spacing10),
                child: _ProfileItemCard(
                  item: item,
                  onMarkWrong:
                      onMarkWrong == null ? null : () => onMarkWrong(item),
                  onExamModeOnly: onExamModeOnly == null
                      ? null
                      : () => onExamModeOnly(item),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildRevertSection(
    BuildContext context,
    Ws6TransparentProfileViewModel view, {
    Future<void> Function(Ws6ProfileRevertActionModel action)? onMarkWrong,
  }) {
    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.panel,
      padding: const EdgeInsets.all(DS.spacing16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.userRevertibleChanges,
            style: DS.labelLarge.copyWith(
              color: DS.textPrimary,
              fontWeight: DS.fontWeightSemibold,
            ),
          ),
          const SizedBox(height: DS.spacing4),
          Text(
            context.l10n.userRevertibleHint,
            style: DS.bodySmall.copyWith(color: DS.textSecondary),
          ),
          const SizedBox(height: DS.spacing12),
          if (view.revertActions.isEmpty)
            Text(
              context.l10n.userNoRevertibleActions,
              style: DS.bodySmall.copyWith(color: DS.textSecondary),
            )
          else
            ...view.revertActions.map(
              (action) => Padding(
                padding: const EdgeInsets.only(bottom: DS.spacing10),
                child: _RevertActionCard(
                  action: action,
                  onMarkWrong:
                      onMarkWrong == null ? null : () => onMarkWrong(action),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildBindingCard(
    BuildContext context,
    Ws6TransparentProfileViewModel view,
  ) {
    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      padding: const EdgeInsets.all(DS.spacing16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Binding notes',
            style: DS.labelLarge.copyWith(
              color: DS.textPrimary,
              fontWeight: DS.fontWeightSemibold,
            ),
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            view.bindingNotes.isEmpty
                ? 'provisional binding only'
                : view.bindingNotes.join(' · '),
            style: DS.bodySmall.copyWith(color: DS.textSecondary),
          ),
        ],
      ),
    );
  }

  Widget _buildCorrectionHistorySection(
    BuildContext context,
    Ws6TransparentProfileViewModel view, {
    Future<void> Function(Ws6ProfileCorrectionHistoryItemModel item)? onUndo,
  }) {
    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.panel,
      padding: const EdgeInsets.all(DS.spacing16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.userCorrectionHistoryTitle,
            style: DS.labelLarge.copyWith(
              color: DS.textPrimary,
              fontWeight: DS.fontWeightSemibold,
            ),
          ),
          const SizedBox(height: DS.spacing4),
          Text(
            context.l10n.userCorrectionHistoryHint,
            style: DS.bodySmall.copyWith(color: DS.textSecondary),
          ),
          const SizedBox(height: DS.spacing12),
          if (view.recentCorrections.isEmpty)
            Text(
              context.l10n.userCorrectionHistoryEmpty,
              style: DS.bodySmall.copyWith(color: DS.textSecondary),
            )
          else
            ...view.recentCorrections.map(
              (item) => Padding(
                padding: const EdgeInsets.only(bottom: DS.spacing10),
                child: _CorrectionHistoryCard(
                  item: item,
                  onUndo: item.canUndo && onUndo != null
                      ? () => onUndo(item)
                      : null,
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildOfflineFallback(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(DS.spacing24),
        child: GraphiteCardSurface(
          surfaceRole: SparkleSurfaceRole.panel,
          padding: const EdgeInsets.all(DS.spacing16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                context.l10n.userTransparentNotEnabled,
                style: DS.titleMedium.copyWith(
                  color: DS.textPrimary,
                  fontWeight: DS.fontWeightSemibold,
                ),
              ),
              const SizedBox(height: DS.spacing8),
              Text(
                context.l10n.userTransparentNotEnabledHint,
                style: DS.bodySmall.copyWith(color: DS.textSecondary),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ProfileItemCard extends StatelessWidget {
  const _ProfileItemCard({
    required this.item,
    this.onMarkWrong,
    this.onExamModeOnly,
  });

  final Ws6TransparentProfileItemModel item;
  final Future<void> Function()? onMarkWrong;
  final Future<void> Function()? onExamModeOnly;

  @override
  Widget build(BuildContext context) {
    final accent = ws6VisibilityColor(item.visibility);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        color: Color.alphaBlend(
          accent.withValues(alpha: 0.05),
          DS.surfacePrimary,
        ),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: accent.withValues(alpha: 0.14)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  item.label,
                  style: DS.bodyMedium.copyWith(
                    color: DS.textPrimary,
                    fontWeight: DS.fontWeightSemibold,
                  ),
                ),
              ),
              _ModePill(label: item.projectionPolicy, color: accent),
            ],
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            item.summary,
            style: DS.bodySmall.copyWith(color: DS.textSecondary),
          ),
          const SizedBox(height: DS.spacing6),
          Text(
            item.evidenceSummary,
            style: DS.labelSmall.copyWith(color: DS.textSecondary),
          ),
          const SizedBox(height: DS.spacing8),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              if (item.canEditDirectly)
                const _ModePill(label: 'editable', color: Color(0xFF73E0B9)),
              if (item.canRevert)
                const _ModePill(label: 'revertable', color: Color(0xFFF1C27A)),
            ],
          ),
          if (item.supportsExamModeOnly || item.canRevert) ...[
            const SizedBox(height: DS.spacing10),
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              children: [
                if (item.supportsExamModeOnly)
                  OutlinedButton(
                    onPressed:
                        onExamModeOnly == null ? null : () => onExamModeOnly!(),
                    child: Text(context.l10n.userExamModeOnly),
                  ),
                if (item.canRevert)
                  OutlinedButton(
                    onPressed:
                        onMarkWrong == null ? null : () => onMarkWrong!(),
                    child: Text(context.l10n.userMarkInaccurate),
                  ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class _RevertActionCard extends StatelessWidget {
  const _RevertActionCard({
    required this.action,
    this.onMarkWrong,
  });

  final Ws6ProfileRevertActionModel action;
  final Future<void> Function()? onMarkWrong;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        color: DS.surfacePrimaryElevated,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: DS.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  action.label,
                  style: DS.bodyMedium.copyWith(
                    color: DS.textPrimary,
                    fontWeight: DS.fontWeightSemibold,
                  ),
                ),
              ),
              _ModePill(
                  label: action.projectionPolicy,
                  color: const Color(0xFFF1C27A)),
            ],
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            action.currentSummary,
            style: DS.bodySmall.copyWith(color: DS.textSecondary),
          ),
          const SizedBox(height: DS.spacing4),
          Text(
            I18nService.instance.isChinese ? '建议：${action.suggestedSummary}' : 'Suggestion: ${action.suggestedSummary}',
            style: DS.bodySmall.copyWith(color: DS.textSecondary),
          ),
          const SizedBox(height: DS.spacing4),
          Text(
            action.reason,
            style: DS.labelSmall.copyWith(color: DS.textSecondary),
          ),
          const SizedBox(height: DS.spacing10),
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: onMarkWrong == null ? null : () => onMarkWrong!(),
                  child: Text(action.requiresDialogue
                      ? context.l10n.userMarkNeedsRecalibration
                      : context.l10n.userMarkInaccurate),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _CorrectionHistoryCard extends StatelessWidget {
  const _CorrectionHistoryCard({
    required this.item,
    this.onUndo,
  });

  final Ws6ProfileCorrectionHistoryItemModel item;
  final Future<void> Function()? onUndo;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        color: DS.surfacePrimaryElevated,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: DS.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  item.fieldName,
                  style: DS.bodyMedium.copyWith(
                    color: DS.textPrimary,
                    fontWeight: DS.fontWeightSemibold,
                  ),
                ),
              ),
              if (item.createdAtLabel.isNotEmpty)
                Text(
                  item.createdAtLabel,
                  style: DS.labelSmall.copyWith(color: DS.textTertiary),
                ),
            ],
          ),
          const SizedBox(height: DS.spacing6),
          Text(
            item.summary,
            style: DS.bodySmall.copyWith(color: DS.textSecondary),
          ),
          const SizedBox(height: DS.spacing8),
          Row(
            children: [
              _ModePill(label: item.action, color: const Color(0xFF78D1C0)),
              const Spacer(),
              if (item.canUndo)
                TextButton(
                  onPressed: onUndo == null ? null : () => onUndo!(),
                  child: Text(context.l10n.userCorrectionHistoryUndo),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ModePill extends StatelessWidget {
  const _ModePill({
    required this.label,
    required this.color,
  });

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing10,
        vertical: DS.spacing4,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.22)),
      ),
      child: Text(
        label,
        style: DS.labelSmall.copyWith(
          color: color,
          fontWeight: DS.fontWeightMedium,
        ),
      ),
    );
  }
}
