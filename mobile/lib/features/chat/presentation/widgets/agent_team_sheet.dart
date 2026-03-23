import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/chat/data/models/chat_mode.dart';
import 'package:sparkle/features/chat/data/models/expert_catalog_model.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_mode_provider.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';
import 'package:sparkle/features/chat/presentation/providers/expert_catalog_provider.dart';

class AgentTeamSheet extends ConsumerStatefulWidget {
  const AgentTeamSheet({super.key});

  @override
  ConsumerState<AgentTeamSheet> createState() => _AgentTeamSheetState();
}

class _AgentTeamSheetState extends ConsumerState<AgentTeamSheet> {
  final Set<String> _selectedAgents = {};
  final Set<String> _answerAgents = {};
  String _collaborationMode = 'auto';

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final catalogAsync = ref.watch(multiAgentCatalogProvider);
    final maxSheetHeight = MediaQuery.of(context).size.height * 0.88;

    return DecoratedBox(
      decoration: BoxDecoration(
        color: isDark ? DS.surfaceSecondary : DS.surfacePrimaryElevated,
        borderRadius: const BorderRadius.vertical(
          top: Radius.circular(DS.spacing24),
        ),
      ),
      child: SafeArea(
        child: ConstrainedBox(
          constraints: BoxConstraints(maxHeight: maxSheetHeight),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: DS.spacing20),
            child: Column(
              children: [
              // Handle bar
              Container(
                width: DS.spacing40,
                height: DS.spacing4,
                margin: const EdgeInsets.symmetric(vertical: DS.spacing12),
                decoration: BoxDecoration(
                  color: isDark ? DS.neutral700 : DS.neutral300,
                  borderRadius: BorderRadius.circular(DS.spacing4 / 2),
                ),
              ),

              // Header
              Row(
                children: [
                  Icon(Icons.groups_rounded, color: DS.primaryBase),
                  const SizedBox(width: DS.spacing12),
                  Text(
                    context.l10n.chatTeamSheetTitle,
                    style: TextStyle(
                      fontSize: DS.fontSizeLg,
                      fontWeight: DS.fontWeightBold,
                      color: isDark ? DS.textPrimary : DS.neutral900,
                    ),
                  ),
                  const Spacer(),
                  SparkleIconButton(
                    icon: const Icon(Icons.person_add_alt_1_outlined),
                    onPressed: () => _showCreateExpertDialog(context),
                    variant: ButtonVariant.ghost,
                  ),
                  SparkleIconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.pop(context),
                    variant: ButtonVariant.ghost,
                  ),
                ],
              ),
              const SizedBox(height: DS.spacing16),

              Expanded(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.only(bottom: DS.spacing12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Align(
                        alignment: Alignment.centerLeft,
                        child: Text(
                          context.l10n.chatTeamSheetAvailableExperts,
                          style: TextStyle(
                            fontSize: DS.fontSizeSm,
                            fontWeight: DS.fontWeightSemibold,
                            color: DS.neutral500,
                          ),
                        ),
                      ),
                      const SizedBox(height: DS.spacing8),
                      catalogAsync.when(
                        data: (catalog) {
                          final experts = [
                            ...catalog.experts.where((e) => e.enabled),
                            ...catalog.customExperts.where((e) => e.enabled),
                          ];
                          if (experts.isEmpty) {
                            return _emptyHint(
                              context.l10n.chatTeamSheetNoExperts,
                            );
                          }
                          return Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              if (catalog.customTeams
                                  .where((e) => e.enabled)
                                  .isNotEmpty) ...[
                                Text(
                                  '已保存团队',
                                  style: TextStyle(
                                    fontSize: DS.fontSizeSm,
                                    fontWeight: DS.fontWeightSemibold,
                                    color: DS.neutral500,
                                  ),
                                ),
                                const SizedBox(height: DS.spacing8),
                                _buildSavedTeams(
                                  catalog.customTeams
                                      .where((e) => e.enabled)
                                      .toList(),
                                ),
                                const SizedBox(height: DS.spacing12),
                              ],
                              _buildExpertGrid(experts),
                            ],
                          );
                        },
                        loading: () =>
                            _emptyHint(context.l10n.chatTeamSheetLoading),
                        error: (_, __) =>
                            _emptyHint(context.l10n.chatTeamSheetLoadFailed),
                      ),
                      const SizedBox(height: DS.spacing16),
                      Align(
                        alignment: Alignment.centerLeft,
                        child: Text(
                          context.l10n.chatTeamSheetCollaborationMode,
                          style: TextStyle(
                            fontSize: DS.fontSizeSm,
                            fontWeight: DS.fontWeightSemibold,
                            color: DS.neutral500,
                          ),
                        ),
                      ),
                      const SizedBox(height: DS.spacing8),
                      _buildModeSelector(),
                      if (_selectedAgents.isNotEmpty) ...[
                        const SizedBox(height: DS.spacing16),
                        Align(
                          alignment: Alignment.centerLeft,
                          child: Text(
                            context.l10n.chatTeamSheetSelectedExperts(
                              _selectedAgents.length,
                            ),
                            style: TextStyle(
                              fontSize: DS.fontSizeSm,
                              fontWeight: DS.fontWeightSemibold,
                              color: DS.neutral600,
                            ),
                          ),
                        ),
                        const SizedBox(height: DS.spacing8),
                        _buildSelectedChips(),
                      ],
                      if (_selectedAgents.length > 1) ...[
                        const SizedBox(height: DS.spacing16),
                        Align(
                          alignment: Alignment.centerLeft,
                          child: Text(
                            '最终回答参与专家',
                            style: TextStyle(
                              fontSize: DS.fontSizeSm,
                              fontWeight: DS.fontWeightSemibold,
                              color: DS.neutral600,
                            ),
                          ),
                        ),
                        const SizedBox(height: DS.spacing8),
                        _buildAnswerExpertSelector(),
                      ],
                    ],
                  ),
                ),
              ),

              if (_selectedAgents.length > 1)
                Align(
                  alignment: Alignment.centerRight,
                  child: TextButton.icon(
                    onPressed: () => _showSaveTeamDialog(context),
                    icon: const Icon(Icons.bookmark_add_outlined),
                    label: const Text('保存团队'),
                  ),
                ),

              // Confirm button
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: _selectedAgents.isEmpty
                      ? null
                      : () {
                          final mode = _buildMode();
                          ref
                              .read(chatModeNotifierProvider.notifier)
                              .setMode(mode);
                          if (mode.apiValue != 'standard') {
                            ref
                                .read(lastMultiAgentModeProvider.notifier)
                                .state = mode;
                          }
                          Navigator.pop(context);
                        },
                  child: Text(
                    _selectedAgents.length <= 1
                        ? context.l10n.chatTeamSheetEnterExpert
                        : context.l10n.chatTeamSheetStartCollaboration,
                  ),
                ),
              ),
              const SizedBox(height: DS.spacing16),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _emptyHint(String text) => Padding(
        padding: const EdgeInsets.symmetric(vertical: DS.spacing12),
        child: Text(
          text,
          style: TextStyle(fontSize: DS.fontSizeSm, color: DS.neutral500),
        ),
      );

  Widget _buildExpertGrid(List<ExpertCatalogExpert> experts) => Wrap(
        spacing: DS.spacing8,
        runSpacing: DS.spacing8,
        children: experts.map((expert) {
          final color = _agentColor(expert.id);
          final isSelected = _selectedAgents.contains(expert.id);
          return FilterChip(
            selected: isSelected,
            label: Text(
              expert.official
                  ? expert.displayName
                  : '${expert.displayName} · 自定义',
            ),
            avatar: isSelected
                ? null
                : Icon(_agentIcon(expert.id), size: 16, color: color),
            backgroundColor: DS.surfacePrimary,
            selectedColor: color.withValues(alpha: 0.16),
            checkmarkColor: color,
            labelStyle: TextStyle(
              color: isSelected ? color : DS.textPrimary,
              fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
            ),
            onSelected: (selected) {
              setState(() {
                if (selected) {
                  _selectedAgents.add(expert.id);
                  _answerAgents.add(expert.id);
                } else {
                  _selectedAgents.remove(expert.id);
                  _answerAgents.remove(expert.id);
                }
              });
            },
          );
        }).toList(),
      );

  Widget _buildSavedTeams(List<ExpertCatalogTeam> teams) => Wrap(
        spacing: DS.spacing8,
        runSpacing: DS.spacing8,
        children: teams
            .map(
              (team) => ActionChip(
                label: Text(team.name),
                avatar:
                    const Icon(Icons.collections_bookmark_outlined, size: 16),
                onPressed: () {
                  setState(() {
                    _selectedAgents
                      ..clear()
                      ..addAll(team.expertIds);
                    _answerAgents
                      ..clear()
                      ..addAll(
                        team.answerExpertIds.isEmpty
                            ? team.expertIds
                            : team.answerExpertIds,
                      );
                    _collaborationMode = team.collaborationMode;
                  });
                },
              ),
            )
            .toList(),
      );

  Widget _buildModeSelector() => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: DS.spacing8,
            children: _collaborationModes(context).map((entry) {
              final isSelected = _collaborationMode == entry.value;
              return ChoiceChip(
                label: Text(entry.label),
                selected: isSelected,
                selectedColor: DS.brandPrimary.withValues(alpha: 0.16),
                labelStyle: TextStyle(
                  fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
                  color: isSelected ? DS.brandPrimary : DS.textPrimary,
                ),
                onSelected: (_) =>
                    setState(() => _collaborationMode = entry.value),
              );
            }).toList(),
          ),
          const SizedBox(height: DS.spacing6),
          Text(
            _collaborationModes(context)
                .firstWhere((e) => e.value == _collaborationMode)
                .description,
            style: TextStyle(fontSize: DS.fontSizeXs, color: DS.neutral500),
          ),
        ],
      );

  Widget _buildSelectedChips() => Wrap(
        spacing: DS.spacing6,
        runSpacing: DS.spacing6,
        children: _selectedAgents.map((agentId) {
          final color = _agentColor(agentId);
          return Chip(
            label: Text(
              _resolveLabel(agentId),
              style: TextStyle(color: color, fontSize: DS.fontSizeXs),
            ),
            backgroundColor: color.withValues(alpha: 0.12),
            deleteIconColor: color.withValues(alpha: 0.6),
            onDeleted: () => setState(() {
              _selectedAgents.remove(agentId);
              _answerAgents.remove(agentId);
            }),
          );
        }).toList(),
      );

  Widget _buildAnswerExpertSelector() => Wrap(
        spacing: DS.spacing8,
        runSpacing: DS.spacing8,
        children: _selectedAgents.map((agentId) {
          final selected = _answerAgents.contains(agentId);
          final color = _agentColor(agentId);
          return FilterChip(
            selected: selected,
            label: Text(_resolveLabel(agentId)),
            selectedColor: color.withValues(alpha: 0.18),
            onSelected: (value) {
              setState(() {
                if (value) {
                  _answerAgents.add(agentId);
                } else if (_answerAgents.length > 1) {
                  _answerAgents.remove(agentId);
                }
              });
            },
          );
        }).toList(),
      );

  /// Resolve display label: prefer catalog name, fallback to hardcoded map.
  String _resolveLabel(String agentId) {
    final catalog = ref.read(multiAgentCatalogProvider).valueOrNull;
    if (catalog != null) {
      for (final expert in [...catalog.experts, ...catalog.customExperts]) {
        if (expert.id == agentId) return expert.displayName;
      }
    }
    return _agentLabelFallback(agentId);
  }

  ChatMode _buildMode() {
    if (_selectedAgents.length <= 1) {
      final agentId =
          _selectedAgents.isNotEmpty ? _selectedAgents.first : 'study_buddy';
      return ChatModeExpert(
        expertId: agentId,
        displayName: _resolveLabel(agentId),
      );
    }
    return ChatModeTeam(
      selectedAgents: _selectedAgents.toList(),
      finalAnswerAgents: _answerAgents.toList(),
      collaborationMode: _collaborationMode,
    );
  }

  IconData _agentIcon(String agentId) {
    switch (agentId) {
      case 'galaxy_guide':
        return Icons.explore_outlined;
      case 'exam_oracle':
        return Icons.quiz_outlined;
      case 'time_tutor':
        return Icons.schedule_outlined;
      case 'deep_analyst':
        return Icons.psychology_outlined;
      case 'error_analyst':
        return Icons.bug_report_outlined;
      case 'math_agent':
        return Icons.functions_outlined;
      case 'code_agent':
        return Icons.code_outlined;
      case 'writing_agent':
        return Icons.edit_note_outlined;
      case 'science_agent':
        return Icons.science_outlined;
      case 'search_agent':
        return Icons.search_outlined;
      case 'study_buddy':
        return Icons.school_outlined;
      default:
        if (agentId.startsWith('custom_expert:')) {
          return Icons.tune_outlined;
        }
        return Icons.smart_toy_outlined;
    }
  }

  Color _agentColor(String agentId) {
    final colorName = _agentColorMapping[agentId] ?? 'neutral';
    return getAgentColor(colorName);
  }

  String _agentLabelFallback(String agentId) {
    final l10n = I18nService.instance.l10n;
    switch (agentId) {
      case 'galaxy_guide':
        return l10n.chatAgentNavigator;
      case 'exam_oracle':
        return l10n.chatAgentExamStrategist;
      case 'time_tutor':
        return l10n.chatAgentTimeCoach;
      case 'deep_analyst':
        return l10n.chatAgentDeepAnalyst;
      case 'error_analyst':
        return l10n.chatAgentCorrectionExpert;
      case 'math_agent':
        return l10n.chatAgentMathExpert;
      case 'code_agent':
        return l10n.chatAgentCodingExpert;
      case 'writing_agent':
        return l10n.chatAgentWritingExpert;
      case 'science_agent':
        return l10n.chatAgentScienceExpert;
      case 'search_agent':
        return l10n.chatAgentSearchExpert;
      case 'study_buddy':
        return l10n.chatAgentLearningBuddy;
      default:
        if (agentId.startsWith('custom_expert:')) {
          return '我的专家';
        }
        return agentId.replaceAll('_', ' ');
    }
  }

  /// Mapping from agent IDs to color names for getAgentColor()
  static const _agentColorMapping = <String, String>{
    'galaxy_guide': 'purple',
    'exam_oracle': 'orange',
    'time_tutor': 'green',
    'deep_analyst': 'blue',
    'error_analyst': 'red',
    'math_agent': 'purple',
    'code_agent': 'cyan',
    'writing_agent': 'pink',
    'science_agent': 'green',
    'search_agent': 'gray',
    'study_buddy': 'yellow',
  };

  Future<void> _showCreateExpertDialog(BuildContext context) async {
    final catalog = ref.read(multiAgentCatalogProvider).valueOrNull;
    final repository = ref.read(chatRepositoryProvider);
    final nameController = TextEditingController();
    final descriptionController = TextEditingController();
    final promptController = TextEditingController();
    final enabledExperts = catalog?.experts.where((e) => e.enabled).toList() ??
        const <ExpertCatalogExpert>[];
    final modelOptions = catalog?.modelOptions ?? const <ModelOption>[];
    var selectedBaseExpert =
        enabledExperts.isNotEmpty ? enabledExperts.first.id : null;
    var selectedModelKey =
        modelOptions.isNotEmpty ? modelOptions.first.key : null;
    var selectedReasoningMode = 'balanced';

    final created = await showSensoryDialog<ExpertCatalogExpert>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (context, setLocalState) => AlertDialog(
          title: const Text('创建自定义专家'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: nameController,
                  decoration: const InputDecoration(labelText: '专家名称'),
                ),
                TextField(
                  controller: descriptionController,
                  decoration: const InputDecoration(labelText: '简介'),
                ),
                DropdownButtonFormField<String>(
                  initialValue: selectedBaseExpert,
                  decoration: const InputDecoration(labelText: '基底专家'),
                  items: enabledExperts
                      .map(
                        (expert) => DropdownMenuItem<String>(
                          value: expert.id,
                          child: Text(expert.displayName),
                        ),
                      )
                      .toList(),
                  onChanged: (value) =>
                      setLocalState(() => selectedBaseExpert = value),
                ),
                DropdownButtonFormField<String>(
                  initialValue: selectedModelKey,
                  decoration: const InputDecoration(labelText: '模型'),
                  items: modelOptions
                      .map(
                        (item) => DropdownMenuItem<String>(
                          value: item.key,
                          child: Text('${item.modelName} · ${item.tier}'),
                        ),
                      )
                      .toList(),
                  onChanged: (value) =>
                      setLocalState(() => selectedModelKey = value),
                ),
                DropdownButtonFormField<String>(
                  initialValue: selectedReasoningMode,
                  decoration: const InputDecoration(labelText: '档位'),
                  items: const [
                    DropdownMenuItem(value: 'fast', child: Text('敏捷')),
                    DropdownMenuItem(value: 'balanced', child: Text('均衡')),
                    DropdownMenuItem(value: 'deep', child: Text('深思')),
                  ],
                  onChanged: (value) => setLocalState(
                    () => selectedReasoningMode = value ?? 'balanced',
                  ),
                ),
                TextField(
                  controller: promptController,
                  decoration: const InputDecoration(
                    labelText: '系统提示词',
                    alignLabelWithHint: true,
                  ),
                  minLines: 4,
                  maxLines: 8,
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: const Text('取消'),
            ),
            FilledButton(
              onPressed: () async {
                final expert = await repository.createCustomExpert(
                  name: nameController.text.trim(),
                  description: descriptionController.text.trim(),
                  systemPrompt: promptController.text.trim(),
                  baseExpertId: selectedBaseExpert,
                  preferredModelKey: selectedModelKey,
                  reasoningMode: selectedReasoningMode,
                );
                if (!dialogContext.mounted) return;
                Navigator.pop(dialogContext, expert);
              },
              child: const Text('创建'),
            ),
          ],
        ),
      ),
    );

    if (created != null) {
      ref.invalidate(multiAgentCatalogProvider);
      setState(() {
        _selectedAgents.add(created.id);
        _answerAgents.add(created.id);
      });
    }
  }

  Future<void> _showSaveTeamDialog(BuildContext context) async {
    final repository = ref.read(chatRepositoryProvider);
    final nameController = TextEditingController();
    final descriptionController = TextEditingController();
    final saved = await showSensoryDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('保存专家团队'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: nameController,
              decoration: const InputDecoration(labelText: '团队名称'),
            ),
            TextField(
              controller: descriptionController,
              decoration: const InputDecoration(labelText: '说明'),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('取消'),
          ),
          FilledButton(
            onPressed: () async {
              await repository.createCustomTeam(
                name: nameController.text.trim(),
                description: descriptionController.text.trim(),
                expertIds: _selectedAgents.toList(),
                answerExpertIds: _answerAgents.toList(),
                collaborationMode: _collaborationMode,
              );
              if (!dialogContext.mounted) return;
              Navigator.pop(dialogContext, true);
            },
            child: const Text('保存'),
          ),
        ],
      ),
    );
    if (saved ?? false) {
      ref.invalidate(multiAgentCatalogProvider);
    }
  }
}

/// Collaboration mode metadata for the UI.
class _CollaborationModeEntry {
  const _CollaborationModeEntry(this.label, this.value, this.description);
  final String label;
  final String value;
  final String description;
}

List<_CollaborationModeEntry> _collaborationModes(BuildContext context) {
  final l10n = context.l10n;
  return [
    _CollaborationModeEntry(
      l10n.chatCollabAuto,
      'auto',
      l10n.chatCollabAutoDesc,
    ),
    _CollaborationModeEntry(
      l10n.chatCollabSequentialShort,
      'sequential',
      l10n.chatCollabSequentialDesc,
    ),
    _CollaborationModeEntry(
      l10n.chatCollabParallelShort,
      'parallel',
      l10n.chatCollabParallelDesc,
    ),
    _CollaborationModeEntry(
      l10n.chatCollabDebateShort,
      'debate',
      l10n.chatCollabDebateDesc,
    ),
    _CollaborationModeEntry(
      l10n.chatCollabDelegationShort,
      'delegation',
      l10n.chatCollabDelegationDesc,
    ),
  ];
}
