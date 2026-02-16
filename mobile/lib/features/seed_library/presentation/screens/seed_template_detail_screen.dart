import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';
import 'package:sparkle/features/seed_library/data/models/seed_template_model.dart';
import 'package:sparkle/features/seed_library/presentation/providers/seed_template_provider.dart';

class SeedTemplateDetailScreen extends ConsumerStatefulWidget {
  const SeedTemplateDetailScreen({
    required this.templateId,
    required this.scenarioType,
    super.key,
  });

  final String templateId;
  final String scenarioType;

  @override
  ConsumerState<SeedTemplateDetailScreen> createState() =>
      _SeedTemplateDetailScreenState();
}

class _SeedTemplateDetailScreenState
    extends ConsumerState<SeedTemplateDetailScreen> {
  final TextEditingController _variablesController = TextEditingController(
    text:
        '{\n  "goal": "",\n  "constraints": "",\n  "milestones": "",\n  "acceptance_criteria": "",\n  "risks": ""\n}',
  );
  String? _selectedVersionId;

  @override
  void dispose() {
    _variablesController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final detailAsync =
        ref.watch(seedTemplateDetailProvider(widget.templateId));
    final versionsAsync =
        ref.watch(seedTemplateVersionsProvider(widget.templateId));
    final instantiateState = ref.watch(seedTemplateInstantiateProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('模板详情')),
      body: detailAsync.when(
        data: (detail) => versionsAsync.when(
          data: (versions) {
            final selectedVersionId = _selectedVersionId ??
                detail.currentVersionId ??
                (versions.isNotEmpty ? versions.first.id : null);
            SeedTemplateVersion? selectedVersion;
            for (final version in versions) {
              if (version.id == selectedVersionId) {
                selectedVersion = version;
                break;
              }
            }
            return ContentConstraint(
              child: ListView(
                padding: const EdgeInsets.all(DS.spacing16),
                children: [
                  Text(
                    detail.name,
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: DS.spacing8),
                  Text(
                    '角色: ${detail.templateRole}',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: DS.spacing16),
                  DropdownButtonFormField<String>(
                    initialValue: selectedVersionId,
                    decoration: const InputDecoration(
                      labelText: '模板版本',
                      border: OutlineInputBorder(),
                    ),
                    items: versions
                        .map(
                          (v) => DropdownMenuItem<String>(
                            value: v.id,
                            child: Text('v${v.versionNo} · ${v.status}'),
                          ),
                        )
                        .toList(),
                    onChanged: (value) =>
                        setState(() => _selectedVersionId = value),
                  ),
                  const SizedBox(height: DS.spacing12),
                  TextField(
                    controller: _variablesController,
                    minLines: 8,
                    maxLines: 14,
                    decoration: const InputDecoration(
                      labelText: '参数注入（JSON）',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: DS.spacing12),
                  Row(
                    children: [
                      Expanded(
                        child: SparkleButton(
                          label: '实例化模板',
                          onPressed: instantiateState.isLoading
                              ? null
                              : () => _instantiateTemplate(selectedVersionId),
                          icon: instantiateState.isLoading
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child:
                                      CircularProgressIndicator(strokeWidth: 2),
                                )
                              : const Icon(Icons.auto_fix_high),
                        ),
                      ),
                    ],
                  ),
                  if (selectedVersion != null &&
                      selectedVersion.changeLog != null) ...[
                    const SizedBox(height: DS.spacing16),
                    Text('变更说明: ${selectedVersion.changeLog}'),
                  ],
                  if (instantiateState.error != null) ...[
                    const SizedBox(height: DS.spacing16),
                    Text(
                      instantiateState.error!,
                      style:
                          TextStyle(color: Theme.of(context).colorScheme.error),
                    ),
                  ],
                  if (instantiateState.result != null) ...[
                    const SizedBox(height: DS.spacing16),
                    if (instantiateState.result!.unresolvedVariables.isNotEmpty)
                      Text(
                        '未解析变量: ${instantiateState.result!.unresolvedVariables.join(", ")}',
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.error,
                        ),
                      ),
                    const SizedBox(height: DS.spacing8),
                    SelectableText(
                      instantiateState.result!.renderedBody,
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    const SizedBox(height: DS.spacing12),
                    SparkleButton(
                      label: '发送到 AI 对话',
                      icon: const Icon(Icons.send),
                      onPressed: () => _sendToChat(instantiateState.result!),
                    ),
                  ],
                ],
              ),
            );
          },
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (error, _) => Center(child: Text('版本加载失败: $error')),
        ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => Center(child: Text('模板加载失败: $error')),
      ),
    );
  }

  Future<void> _instantiateTemplate(String? versionId) async {
    final variables = _parseVariables(_variablesController.text);
    if (variables == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('参数 JSON 格式不正确')),
      );
      return;
    }
    await ref.read(seedTemplateInstantiateProvider.notifier).instantiate(
      templateId: widget.templateId,
      versionId: versionId,
      variables: variables,
      context: <String, dynamic>{
        'scenario_type': widget.scenarioType,
        'entry_source': 'seed_template_screen',
      },
    );
  }

  Future<void> _sendToChat(SeedTemplateInstantiateResult result) async {
    final chatMode = _chatModeForScenario(widget.scenarioType);
    await ref.read(chatProvider.notifier).sendMessage(
          result.renderedBody,
          extraContextOverride: result.metadata,
          chatModeOverride: chatMode,
        );
    if (!mounted) {
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('已发送到 AI 对话')),
    );
    Navigator.pop(context);
  }
}

Map<String, dynamic>? _parseVariables(String raw) {
  if (raw.trim().isEmpty) {
    return const <String, dynamic>{};
  }
  try {
    final decoded = jsonDecode(raw);
    if (decoded is Map<String, dynamic>) {
      return decoded;
    }
  } catch (_) {}
  return null;
}

String _chatModeForScenario(String scenarioType) {
  switch (scenarioType) {
    case 'study_plan':
      return 'study_plan';
    case 'deep_analysis':
      return 'deep_analysis';
    case 'writing':
      return 'expert::writing_agent';
    default:
      return 'expert_auto';
  }
}
