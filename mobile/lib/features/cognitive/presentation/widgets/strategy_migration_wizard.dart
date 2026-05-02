import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/cognitive/data/models/strategy_migration_models.dart';
import 'package:sparkle/features/cognitive/data/repositories/strategy_migration_repository.dart';

class StrategyMigrationWizard extends ConsumerStatefulWidget {
  const StrategyMigrationWizard({
    required this.goalId,
    required this.belief,
    this.onMigrated,
    super.key,
  });

  final String goalId;
  final StrategyBeliefView? belief;
  final ValueChanged<StrategyMigrationResult>? onMigrated;

  @override
  ConsumerState<StrategyMigrationWizard> createState() =>
      _StrategyMigrationWizardState();
}

class _StrategyMigrationWizardState
    extends ConsumerState<StrategyMigrationWizard> {
  int _step = 0;
  String? _selectedStrategyId;
  bool _submitting = false;
  StrategyMigrationResult? _result;

  String _t(String zh, String en) => I18nService.instance.isChinese ? zh : en;

  @override
  Widget build(BuildContext context) {
    final belief = widget.belief;
    if (belief == null || !belief.shouldTrigger) {
      return const SizedBox.shrink();
    }

    final suggestions = ref.watch(alternativeStrategiesProvider(widget.goalId));
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: DS.warning100,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: DS.warning.withValues(alpha: 0.35)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.alt_route_rounded, color: DS.warning),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  _t('策略需要迁移', 'Strategy needs migration'),
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                ),
              ),
              _StepDots(currentStep: _step, count: 3),
            ],
          ),
          const SizedBox(height: 12),
          AnimatedSwitcher(
            duration: const Duration(milliseconds: 180),
            child: suggestions.when(
              data: (bundle) => _buildStep(context, bundle),
              loading: () => const Padding(
                padding: EdgeInsets.symmetric(vertical: 18),
                child: LinearProgressIndicator(minHeight: 4),
              ),
              error: (_, __) => _ErrorLine(
                label: _t('替代策略加载失败', 'Could not load alternatives'),
                onRetry: () => ref.invalidate(
                  alternativeStrategiesProvider(widget.goalId),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStep(BuildContext context, StrategySuggestionBundle bundle) {
    if (_result != null) {
      return _CompletedStep(result: _result!);
    }
    switch (_step) {
      case 0:
        return _EvidenceStep(
          belief: widget.belief!,
          bundle: bundle,
          onNext: () => setState(() => _step = 1),
        );
      case 1:
        return _AlternativeStep(
          alternatives: bundle.alternatives,
          selectedStrategyId: _selectedStrategyId,
          onSelected: (strategyId) =>
              setState(() => _selectedStrategyId = strategyId),
          onBack: () => setState(() => _step = 0),
          onNext: _selectedStrategyId == null
              ? null
              : () => setState(() => _step = 2),
        );
      default:
        final selected = bundle.alternatives.firstWhere(
          (item) => item.strategyId == _selectedStrategyId,
          orElse: () => bundle.alternatives.first,
        );
        return _ConfirmStep(
          selected: selected,
          submitting: _submitting,
          onBack: () => setState(() => _step = 1),
          onConfirm: () => unawaited(_submit(selected.strategyId)),
        );
    }
  }

  Future<void> _submit(String strategyId) async {
    setState(() => _submitting = true);
    try {
      final result = await ref
          .read(strategyMigrationRepositoryProvider)
          .migrateStrategy(goalId: widget.goalId, newStrategyId: strategyId);
      if (!mounted) return;
      setState(() {
        _submitting = false;
        _result = result;
      });
      widget.onMigrated?.call(result);
    } catch (_) {
      if (!mounted) return;
      setState(() => _submitting = false);
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(
        SnackBar(content: Text(_t('策略迁移失败', 'Migration failed'))),
      );
    }
  }
}

class _EvidenceStep extends StatelessWidget {
  const _EvidenceStep({
    required this.belief,
    required this.bundle,
    required this.onNext,
  });

  final StrategyBeliefView belief;
  final StrategySuggestionBundle bundle;
  final VoidCallback onNext;

  String _t(String zh, String en) => I18nService.instance.isChinese ? zh : en;

  @override
  Widget build(BuildContext context) {
    return Column(
      key: const ValueKey('strategy-evidence-step'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          _t('当前策略', 'Current strategy'),
          style: Theme.of(context).textTheme.labelLarge,
        ),
        const SizedBox(height: 6),
        Text(
          belief.title.isEmpty ? bundle.currentStrategyTitle : belief.title,
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.w700,
              ),
        ),
        const SizedBox(height: 10),
        LinearProgressIndicator(value: belief.confidence.clamp(0, 1)),
        const SizedBox(height: 10),
        for (final evidence in belief.counterEvidence.take(3))
          Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(Icons.report_problem_outlined,
                    size: 18, color: DS.warning),
                const SizedBox(width: 8),
                Expanded(child: Text(evidence.reason)),
              ],
            ),
          ),
        const SizedBox(height: 12),
        Align(
          alignment: Alignment.centerRight,
          child: FilledButton.icon(
            onPressed: onNext,
            icon: const Icon(Icons.arrow_forward_rounded),
            label: Text(_t('查看替代策略', 'View alternatives')),
          ),
        ),
      ],
    );
  }
}

class _AlternativeStep extends StatelessWidget {
  const _AlternativeStep({
    required this.alternatives,
    required this.selectedStrategyId,
    required this.onSelected,
    required this.onBack,
    required this.onNext,
  });

  final List<AlternativeStrategyModel> alternatives;
  final String? selectedStrategyId;
  final ValueChanged<String> onSelected;
  final VoidCallback onBack;
  final VoidCallback? onNext;

  String _t(String zh, String en) => I18nService.instance.isChinese ? zh : en;

  @override
  Widget build(BuildContext context) {
    return Column(
      key: const ValueKey('strategy-alternative-step'),
      children: [
        for (final strategy in alternatives)
          _StrategyOptionTile(
            strategy: strategy,
            selected: strategy.strategyId == selectedStrategyId,
            onSelected: () => onSelected(strategy.strategyId),
          ),
        Row(
          mainAxisAlignment: MainAxisAlignment.end,
          children: [
            TextButton(onPressed: onBack, child: Text(_t('返回', 'Back'))),
            const SizedBox(width: 8),
            FilledButton(
              onPressed: onNext,
              child: Text(_t('继续', 'Continue')),
            ),
          ],
        ),
      ],
    );
  }
}

class _StrategyOptionTile extends StatelessWidget {
  const _StrategyOptionTile({
    required this.strategy,
    required this.selected,
    required this.onSelected,
  });

  final AlternativeStrategyModel strategy;
  final bool selected;
  final VoidCallback onSelected;

  @override
  Widget build(BuildContext context) {
    final color = selected ? DS.warning : DS.textSecondary;
    return GestureDetector(
      onTap: onSelected,
      behavior: HitTestBehavior.opaque,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(
              selected
                  ? Icons.radio_button_checked_rounded
                  : Icons.radio_button_unchecked_rounded,
              color: color,
              size: 22,
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    strategy.title,
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w700,
                          color: DS.textPrimary,
                        ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    strategy.why,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: DS.textSecondary,
                          height: 1.35,
                        ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            Text(
              '+${(strategy.estimatedLift * 100).round()}%',
              style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    color: DS.warning,
                    fontWeight: FontWeight.w800,
                  ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ConfirmStep extends StatelessWidget {
  const _ConfirmStep({
    required this.selected,
    required this.submitting,
    required this.onBack,
    required this.onConfirm,
  });

  final AlternativeStrategyModel selected;
  final bool submitting;
  final VoidCallback onBack;
  final VoidCallback onConfirm;

  String _t(String zh, String en) => I18nService.instance.isChinese ? zh : en;

  @override
  Widget build(BuildContext context) {
    return Column(
      key: const ValueKey('strategy-confirm-step'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          selected.title,
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.w800,
              ),
        ),
        const SizedBox(height: 8),
        Text(selected.description),
        const SizedBox(height: 14),
        Row(
          mainAxisAlignment: MainAxisAlignment.end,
          children: [
            TextButton(
                onPressed: submitting ? null : onBack,
                child: Text(_t('返回', 'Back'))),
            const SizedBox(width: 8),
            FilledButton.icon(
              onPressed: submitting ? null : onConfirm,
              icon: submitting
                  ? const SizedBox(
                      height: 16,
                      width: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.check_rounded),
              label: Text(_t('确认迁移', 'Confirm migration')),
            ),
          ],
        ),
      ],
    );
  }
}

class _CompletedStep extends StatelessWidget {
  const _CompletedStep({required this.result});

  final StrategyMigrationResult result;

  String _t(String zh, String en) => I18nService.instance.isChinese ? zh : en;

  @override
  Widget build(BuildContext context) {
    return Row(
      key: const ValueKey('strategy-completed-step'),
      children: [
        Icon(Icons.check_circle_outline_rounded, color: DS.success),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            _t('已切换到 ${result.newStrategyTitle}',
                'Switched to ${result.newStrategyTitle}'),
          ),
        ),
      ],
    );
  }
}

class _StepDots extends StatelessWidget {
  const _StepDots({required this.currentStep, required this.count});

  final int currentStep;
  final int count;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        for (var index = 0; index < count; index++)
          Container(
            margin: const EdgeInsets.only(left: 4),
            height: 7,
            width: index == currentStep ? 18 : 7,
            decoration: BoxDecoration(
              color: index == currentStep ? DS.warning : DS.warning200,
              borderRadius: BorderRadius.circular(999),
            ),
          ),
      ],
    );
  }
}

class _ErrorLine extends StatelessWidget {
  const _ErrorLine({required this.label, required this.onRetry});

  final String label;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Row(
      key: const ValueKey('strategy-error-line'),
      children: [
        Expanded(child: Text(label)),
        TextButton(onPressed: onRetry, child: const Text('Retry')),
      ],
    );
  }
}
