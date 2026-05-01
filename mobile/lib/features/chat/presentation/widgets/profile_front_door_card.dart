import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/custom_button.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/features/memory/presentation/widgets/evidence_drawer.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

class ProfileFrontDoorCard extends StatelessWidget {
  const ProfileFrontDoorCard({
    required this.data,
    super.key,
    this.onAction,
  });

  final Map<String, dynamic> data;
  final Future<void> Function(String actionType, Map<String, dynamic> payload)?
      onAction;

  @override
  Widget build(BuildContext context) {
    final summary = data['summary']?.toString() ?? '';
    final claims = _mapList(data['claims']);
    final predictions = _mapList(data['predictions']);
    final unknowns = _mapList(data['unknowns']);
    final confirmation = _asMap(data['confirmation']);
    final calibration = _asMap(data['calibration']);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (summary.isNotEmpty) ...[
          Text(
            summary,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: DS.neutral700,
                  height: 1.45,
                ),
          ),
          const SizedBox(height: DS.spacing12),
        ],
        if (confirmation.isNotEmpty) ...[
          _SectionCard(
            color: const Color(0xFFE8F5EF),
            borderColor: const Color(0xFFB5DDC8),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  confirmation['title']?.toString() ??
                      context.l10n.chatProfileUpdated,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        fontWeight: DS.fontWeightSemibold,
                        color: DS.neutral900,
                      ),
                ),
                if ((confirmation['message']?.toString() ?? '').isNotEmpty) ...[
                  const SizedBox(height: DS.spacing4),
                  Text(
                    confirmation['message'].toString(),
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: DS.neutral700,
                          height: 1.4,
                        ),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: DS.spacing12),
        ],
        if (claims.isNotEmpty) ...[
          _SectionTitle(
            title: context.l10n.chatProfileCurrentJudgment,
            subtitle: context.l10n.chatProfileCurrentJudgmentDesc,
          ),
          const SizedBox(height: DS.spacing8),
          ...claims.map(
            (claim) => Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing10),
              child: _ClaimTile(
                claim: claim,
                onAction: onAction,
              ),
            ),
          ),
        ],
        if (predictions.isNotEmpty) ...[
          const SizedBox(height: DS.spacing8),
          _SectionTitle(
            title: context.l10n.chatProfileTrendJudgment,
            subtitle: context.l10n.chatProfileTrendDesc,
          ),
          const SizedBox(height: DS.spacing8),
          ...predictions.map(
            (item) => Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing8),
              child: _PredictionTile(item: item),
            ),
          ),
        ],
        if ((calibration['summary']?.toString() ?? '').isNotEmpty) ...[
          const SizedBox(height: DS.spacing8),
          _SectionCard(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(
                  Icons.track_changes_rounded,
                  size: DS.iconSizeSm,
                  color: DS.info,
                ),
                const SizedBox(width: DS.spacing8),
                Expanded(
                  child: Text(
                    calibration['summary'].toString(),
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: DS.neutral700,
                          height: 1.4,
                        ),
                  ),
                ),
              ],
            ),
          ),
        ],
        if (unknowns.isNotEmpty) ...[
          const SizedBox(height: DS.spacing12),
          _SectionTitle(
            title: context.l10n.chatProfileUnknownItems,
            subtitle: context.l10n.chatProfileUnknownDesc,
          ),
          const SizedBox(height: DS.spacing6),
          ...unknowns.map(
            (item) => Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing4),
              child: Text(
                '• ${item['description']?.toString() ?? ''}',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.neutral700,
                    ),
              ),
            ),
          ),
        ],
        if ((data['binding_note']?.toString() ?? '').isNotEmpty) ...[
          const SizedBox(height: DS.spacing12),
          Text(
            data['binding_note'].toString(),
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.neutral500,
                ),
          ),
        ],
      ],
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({
    required this.title,
    required this.subtitle,
  });

  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                fontWeight: DS.fontWeightSemibold,
                color: DS.neutral900,
              ),
        ),
        const SizedBox(height: DS.spacing2),
        Text(
          subtitle,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: DS.neutral600,
              ),
        ),
      ],
    );
  }
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({
    required this.child,
    this.color,
    this.borderColor,
  });

  final Widget child;
  final Color? color;
  final Color? borderColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        color: color ?? DS.surfaceSecondary,
        borderRadius: DS.borderRadius12,
        border: Border.all(color: borderColor ?? DS.neutral200),
      ),
      child: child,
    );
  }
}

class _ClaimTile extends StatelessWidget {
  const _ClaimTile({
    required this.claim,
    this.onAction,
  });

  final Map<String, dynamic> claim;
  final Future<void> Function(String actionType, Map<String, dynamic> payload)?
      onAction;

  @override
  Widget build(BuildContext context) {
    final actions = _mapList(claim['actions']);
    final evidenceRefs = _parseEvidenceRefs(claim['evidence_refs']);
    return _SectionCard(
      color: claim['highlighted'] == true
          ? DS.primaryBase.withValues(alpha: 0.06)
          : DS.surfaceSecondary,
      borderColor: claim['highlighted'] == true
          ? DS.primaryBase.withValues(alpha: 0.24)
          : DS.neutral200,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Text(
                  claim['label']?.toString() ?? '',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        fontWeight: DS.fontWeightSemibold,
                        color: DS.neutral900,
                      ),
                ),
              ),
              const SizedBox(width: DS.spacing8),
              _Badge(
                label: claim['evidence_label']?.toString() ??
                    context.l10n.chatProfileCompileConclusion,
                color: const Color(0xFF0F766E),
                background: const Color(0xFFE7F6F4),
              ),
            ],
          ),
          if ((claim['value']?.toString() ?? '').isNotEmpty) ...[
            const SizedBox(height: DS.spacing6),
            Text(
              claim['value'].toString(),
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: DS.fontWeightBold,
                    color: DS.neutral900,
                  ),
            ),
          ],
          if ((claim['summary']?.toString() ?? '').isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            Text(
              claim['summary'].toString(),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.neutral700,
                    height: 1.4,
                  ),
            ),
          ],
          const SizedBox(height: DS.spacing8),
          Wrap(
            spacing: DS.spacing6,
            runSpacing: DS.spacing6,
            children: [
              if ((claim['confidence_label']?.toString() ?? '').isNotEmpty)
                _Badge(
                  label: context.l10n.chatProfileConfidence(
                      claim['confidence_label'].toString()),
                  color: DS.primaryBase,
                  background: DS.primaryBase.withValues(alpha: 0.08),
                ),
              if ((claim['source']?.toString() ?? '').isNotEmpty)
                _Badge(
                  label: context.l10n
                      .chatProfileSource(claim['source'].toString()),
                  color: DS.neutral700,
                  background: DS.neutral100,
                ),
              if ((claim['freshness']?.toString() ?? '').isNotEmpty)
                _Badge(
                  label: context.l10n
                      .chatProfileFreshness(claim['freshness'].toString()),
                  color: DS.neutral700,
                  background: DS.neutral100,
                ),
            ],
          ),
          if ((claim['correction_hint']?.toString() ?? '').isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            Text(
              claim['correction_hint'].toString(),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.neutral600,
                  ),
            ),
          ],
          if (evidenceRefs.isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            Semantics(
              button: true,
              label: 'Chat profile front door card control 1',
              child: InkWell(
                onTap: () => unawaited(
                  EvidenceDrawer.show(
                    context,
                    refs: evidenceRefs,
                    evidenceMissing: false,
                  ),
                ),
                borderRadius: DS.borderRadius12,
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: DS.spacing2,
                    vertical: DS.spacing2,
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.dataset_linked_outlined,
                        size: DS.iconSizeSm,
                        color: DS.info,
                      ),
                      const SizedBox(width: DS.spacing6),
                      Flexible(
                        child: Text(
                          claim['evidence_cta']?.toString().isNotEmpty == true
                              ? '${claim['evidence_cta']} · ${claim['evidence_summary']}'
                              : claim['evidence_summary']?.toString() ??
                                  context.l10n.chatProfileViewEvidence,
                          style:
                              Theme.of(context).textTheme.bodySmall?.copyWith(
                                    color: DS.info,
                                    fontWeight: DS.fontWeightMedium,
                                  ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],
          if (actions.isNotEmpty && onAction != null) ...[
            const SizedBox(height: DS.spacing10),
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              children: actions.map((action) {
                final actionType = action['type']?.toString() ?? 'prompt';
                final payload = Map<String, dynamic>.from(action);
                return CustomButton.secondary(
                  text: action['label']?.toString() ?? '继续',
                  onPressed: () => unawaited(onAction!(actionType, payload)),
                  size: CustomButtonSize.small,
                );
              }).toList(),
            ),
          ],
        ],
      ),
    );
  }
}

class _PredictionTile extends StatelessWidget {
  const _PredictionTile({required this.item});

  final Map<String, dynamic> item;

  @override
  Widget build(BuildContext context) {
    final evidenceRefs = _parseEvidenceRefs(item['evidence_refs']);
    return _SectionCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  item['label']?.toString() ?? '',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        fontWeight: DS.fontWeightSemibold,
                        color: DS.neutral900,
                      ),
                ),
              ),
              _Badge(
                label: item['evidence_label']?.toString() ??
                    context.l10n.chatProfileInferencePrediction,
                color: const Color(0xFF7C3AED),
                background: const Color(0xFFF2EAFE),
              ),
            ],
          ),
          if ((item['summary']?.toString() ?? '').isNotEmpty) ...[
            const SizedBox(height: DS.spacing6),
            Text(
              item['summary'].toString(),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.neutral700,
                    height: 1.4,
                  ),
            ),
          ],
          if ((item['recommended_action']?.toString() ?? '').isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            Text(
              context.l10n.chatProfileSuggestedAction(
                  item['recommended_action'].toString()),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.neutral900,
                    fontWeight: DS.fontWeightSemibold,
                  ),
            ),
          ],
          if (evidenceRefs.isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            Semantics(
              button: true,
              label: 'Chat profile front door card control 2',
              child: InkWell(
                onTap: () => unawaited(
                  EvidenceDrawer.show(
                    context,
                    refs: evidenceRefs,
                    evidenceMissing: false,
                  ),
                ),
                borderRadius: DS.borderRadius12,
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: DS.spacing2,
                    vertical: DS.spacing2,
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.dataset_linked_outlined,
                        size: DS.iconSizeSm,
                        color: DS.info,
                      ),
                      const SizedBox(width: DS.spacing6),
                      Flexible(
                        child: Text(
                          item['evidence_cta']?.toString().isNotEmpty == true
                              ? '${item['evidence_cta']} · ${item['evidence_summary']}'
                              : item['evidence_summary']?.toString() ??
                                  context.l10n.chatProfileViewEvidence,
                          style:
                              Theme.of(context).textTheme.bodySmall?.copyWith(
                                    color: DS.info,
                                    fontWeight: DS.fontWeightMedium,
                                  ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _Badge extends StatelessWidget {
  const _Badge({
    required this.label,
    required this.color,
    required this.background,
  });

  final String label;
  final Color color;
  final Color background;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing8,
        vertical: DS.spacing4,
      ),
      decoration: BoxDecoration(
        color: background,
        borderRadius: DS.borderRadius20,
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: color,
              fontWeight: DS.fontWeightSemibold,
            ),
      ),
    );
  }
}

List<Map<String, dynamic>> _mapList(dynamic raw) {
  if (raw is List) {
    return raw
        .whereType<Map<dynamic, dynamic>>()
        .map(Map<String, dynamic>.from)
        .toList();
  }
  return const <Map<String, dynamic>>[];
}

Map<String, dynamic> _asMap(dynamic raw) {
  if (raw is Map<String, dynamic>) {
    return raw;
  }
  if (raw is Map) {
    return Map<String, dynamic>.from(raw);
  }
  return const <String, dynamic>{};
}

List<EvidenceRefModel> _parseEvidenceRefs(dynamic raw) {
  if (raw is List) {
    return raw
        .whereType<Map<dynamic, dynamic>>()
        .map((item) =>
            EvidenceRefModel.fromJson(Map<String, dynamic>.from(item)))
        .where((item) => item.type.isNotEmpty && item.id.isNotEmpty)
        .toList();
  }
  return const <EvidenceRefModel>[];
}
