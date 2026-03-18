import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/utils/formatters.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';

class PlanCreateScreen extends ConsumerStatefulWidget {
  const PlanCreateScreen({super.key, this.planType});
  final String? planType;

  @override
  ConsumerState<PlanCreateScreen> createState() => _PlanCreateScreenState();
}

class _PlanCreateScreenState extends ConsumerState<PlanCreateScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _descController = TextEditingController();
  final _subjectController = TextEditingController();

  late PlanType _selectedType;
  int _dailyMinutes = 60;
  PlanPriority _priority = PlanPriority.normal;
  DateTime? _targetDate;
  bool _isSubmitting = false;
  bool _didInitType = false;

  @override
  void initState() {
    super.initState();
    _selectedType = widget.planType == 'growth' ? PlanType.growth : PlanType.sprint;
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_didInitType) return;
    _didInitType = true;

    final typeParam = GoRouterState.of(context).uri.queryParameters['type'];
    if (typeParam != null) {
      _selectedType = typeParam == 'growth' ? PlanType.growth : PlanType.sprint;
    }
  }

  @override
  void dispose() {
    _nameController.dispose();
    _descController.dispose();
    _subjectController.dispose();
    super.dispose();
  }

  Future<void> _submitPlan() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isSubmitting = true);

    try {
      final planCreate = PlanCreate(
        name: _nameController.text.trim(),
        type: _selectedType,
        description: _descController.text.trim().isNotEmpty
            ? _descController.text.trim()
            : null,
        targetDate: _targetDate,
        subject: _subjectController.text.trim().isNotEmpty
            ? _subjectController.text.trim()
            : null,
        dailyAvailableMinutes: _dailyMinutes,
        priority: _priority,
      );

      await ref.read(planListProvider.notifier).createPlan(planCreate);

      if (mounted) {
        context.pop();
        AppFeedback.success(context, context.l10n.planCreateSuccess);
      }
    } catch (e) {
      if (mounted) {
        AppFeedback.error(context, context.l10n.planCreateFailed(e.toString()));
      }
    } finally {
      if (mounted) {
        setState(() => _isSubmitting = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        title: Text(
          _selectedType == PlanType.growth
              ? l10n.createGrowthPlan
              : l10n.createSprintPlan,
        ),
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      child: ContentConstraint(
        child: Form(
          key: _formKey,
          child: ListView(
            padding: const EdgeInsets.all(DS.lg),
            children: [
              // Plan Type Selector
              SegmentedButton<PlanType>(
                segments: [
                  ButtonSegment(
                    value: PlanType.sprint,
                    label: Text(l10n.planTypeSprint),
                    icon: const Icon(Icons.flash_on),
                  ),
                  ButtonSegment(
                    value: PlanType.growth,
                    label: Text(l10n.planTypeGrowth),
                    icon: const Icon(Icons.trending_up),
                  ),
                ],
                selected: {_selectedType},
                onSelectionChanged: (types) {
                  setState(() => _selectedType = types.first);
                },
              ),
              const SizedBox(height: DS.lg),

              // Name
              TextFormField(
                controller: _nameController,
                decoration: InputDecoration(
                  labelText: l10n.planNameLabel,
                  hintText: l10n.planNameHint,
                  border: const OutlineInputBorder(),
                  prefixIcon: const Icon(Icons.label_outline),
                ),
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return l10n.planNameRequired;
                  }
                  return null;
                },
              ),
              const SizedBox(height: DS.lg),

              // Description
              TextFormField(
                controller: _descController,
                decoration: InputDecoration(
                  labelText: l10n.planDescLabel,
                  hintText: l10n.planDescHint,
                  border: const OutlineInputBorder(),
                  prefixIcon: const Icon(Icons.description_outlined),
                ),
                maxLines: 3,
              ),
              const SizedBox(height: DS.lg),

              // Subject
              TextFormField(
                controller: _subjectController,
                decoration: InputDecoration(
                  labelText: l10n.planSubjectLabel,
                  hintText: l10n.planSubjectHint,
                  border: const OutlineInputBorder(),
                  prefixIcon: const Icon(Icons.school_outlined),
                ),
              ),
              const SizedBox(height: DS.lg),

              // Daily Available Minutes
              DropdownButtonFormField<int>(
                initialValue: _dailyMinutes,
                decoration: InputDecoration(
                  labelText: l10n.planDailyMinutesLabel,
                  border: const OutlineInputBorder(),
                  prefixIcon: const Icon(Icons.timer_outlined),
                ),
                items: [15, 30, 45, 60, 90, 120, 180, 240]
                    .map(
                      (m) => DropdownMenuItem(
                        value: m,
                        child: Text(l10n.taskMinutesOption(m)),
                      ),
                    )
                    .toList(),
                onChanged: (v) {
                  if (v != null) {
                    setState(() => _dailyMinutes = v);
                  }
                },
              ),
              const SizedBox(height: DS.lg),

              // Priority
              DropdownButtonFormField<PlanPriority>(
                initialValue: _priority,
                decoration: InputDecoration(
                  labelText: l10n.planPriorityLabel,
                  border: const OutlineInputBorder(),
                  prefixIcon: const Icon(Icons.flag_outlined),
                ),
                items: PlanPriority.values
                    .map(
                      (p) => DropdownMenuItem(
                        value: p,
                        child: Text(_getPriorityLabel(l10n, p)),
                      ),
                    )
                    .toList(),
                onChanged: (v) {
                  if (v != null) {
                    setState(() => _priority = v);
                  }
                },
              ),
              const SizedBox(height: DS.lg),

              // Target Date
              ListTile(
                title: Text(l10n.planTargetDateLabel),
                subtitle: Text(
                  _targetDate == null
                      ? l10n.planTargetDateUnset
                      : Formatters.formatDateShort(_targetDate!),
                ),
                leading: const Icon(Icons.calendar_today),
                shape: RoundedRectangleBorder(
                  side: BorderSide(
                    color: DS.brandPrimary.withValues(alpha: 0.4),
                  ),
                  borderRadius: BorderRadius.circular(4),
                ),
                onTap: () async {
                  final date = await showDatePicker(
                    context: context,
                    initialDate: _targetDate ?? DateTime.now(),
                    firstDate: DateTime.now(),
                    lastDate: DateTime.now().add(const Duration(days: 365)),
                  );
                  if (date != null) {
                    setState(() => _targetDate = date);
                  }
                },
                trailing: _targetDate != null
                    ? SparkleIconButton(
                        variant: ButtonVariant.ghost,
                        size: 32,
                        icon: const Icon(Icons.clear),
                        onPressed: () => setState(() => _targetDate = null),
                      )
                    : null,
              ),
              const SizedBox(height: DS.xxl),

              // Submit Button
              FilledButton.icon(
                onPressed: _isSubmitting ? null : _submitPlan,
                icon: _isSubmitting
                    ? SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: DS.textOnPrimary,
                        ),
                      )
                    : const Icon(Icons.check),
                label: Text(
                  _isSubmitting ? l10n.planCreating : l10n.planCreateAction,
                ),
                style: FilledButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _getPriorityLabel(AppLocalizations l10n, PlanPriority priority) {
    switch (priority) {
      case PlanPriority.critical:
        return l10n.planPriorityCritical;
      case PlanPriority.high:
        return l10n.planPriorityHigh;
      case PlanPriority.normal:
        return l10n.planPriorityNormal;
      case PlanPriority.low:
        return l10n.planPriorityLow;
    }
  }
}
