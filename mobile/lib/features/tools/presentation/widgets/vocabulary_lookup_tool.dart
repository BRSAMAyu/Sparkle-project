// ignore_for_file: unawaited_futures, discarded_futures

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/knowledge/presentation/providers/vocabulary_provider.dart';
import 'package:sparkle/features/tools/models/tool_definition.dart';
import 'package:sparkle/features/tools/presentation/widgets/tool_shell.dart';
import 'package:sparkle/features/vocabulary/presentation/providers/local_vocabulary_provider.dart';

class VocabularyLookupTool extends ConsumerStatefulWidget {
  const VocabularyLookupTool({
    super.key,
    this.taskId,
    this.surface = ToolSurface.page,
  });

  final String? taskId;
  final ToolSurface surface;

  @override
  ConsumerState<VocabularyLookupTool> createState() =>
      _VocabularyLookupToolState();
}

class _VocabularyLookupToolState extends ConsumerState<VocabularyLookupTool> {
  final TextEditingController _controller = TextEditingController();
  final FocusNode _focusNode = FocusNode();
  bool _isInLocalWordbook = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _focusNode.requestFocus();
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  Future<void> _lookup() async {
    final word = _controller.text.trim();
    if (word.isEmpty) {
      AppFeedback.info(context, '请输入要查询的单词');
      return;
    }

    final localWord =
        await ref.read(localVocabularyProvider.notifier).getByWord(word);
    setState(() {
      _isInLocalWordbook = localWord != null;
    });

    ref.read(vocabularyProvider.notifier).lookup(word);
    ref.read(vocabularyProvider.notifier).fetchAssociations(word);
  }

  Future<void> _generateSentence() async {
    final word = _controller.text.trim();
    if (word.isEmpty) {
      return;
    }
    await ref.read(vocabularyProvider.notifier).generateSentence(word);
  }

  Future<void> _addToWordbook() async {
    final state = ref.read(vocabularyProvider);
    final result = state.lookupResult;
    if (result == null) {
      return;
    }

    final word = result['word'] as String? ?? _controller.text;
    final definitions = result['definitions'];
    var definition = '';

    if (definitions is List && definitions.isNotEmpty) {
      definition = definitions.join('; ');
    } else if (definitions is String) {
      definition = definitions;
    }

    await ref.read(localVocabularyProvider.notifier).addWord(
          word: word,
          definition: definition,
          phonetic: result['phonetic'] as String?,
          exampleSentence: state.exampleSentence,
          taskId: widget.taskId,
        );

    setState(() {
      _isInLocalWordbook = true;
    });

    if (mounted) {
      HapticFeedback.mediumImpact();
      AppFeedback.success(context, '已添加 "$word" 到生词本');
    }
  }

  Future<void> _removeFromWordbook() async {
    final state = ref.read(vocabularyProvider);
    final result = state.lookupResult;
    if (result == null) {
      return;
    }

    final word = result['word'] as String? ?? _controller.text;
    final localWord =
        await ref.read(localVocabularyProvider.notifier).getByWord(word);

    if (localWord != null) {
      await ref.read(localVocabularyProvider.notifier).delete(localWord.id);
      setState(() {
        _isInLocalWordbook = false;
      });
      if (mounted) {
        HapticFeedback.lightImpact();
        AppFeedback.info(context, '已从生词本移除 "$word"');
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(vocabularyProvider);
    final accent = DS.prismBlue;
    final result = state.lookupResult;
    final definitions = result?['definitions'];
    final examples = result?['examples'];

    return ToolShell(
      surface: widget.surface,
      icon: Icons.search_rounded,
      title: '查词',
      subtitle: '用来做快速词义确认、例句生成和关联词扩展，查询结果可以直接收进本地生词本。',
      accentColor: accent,
      fillHeight: true,
      heroChips: [
        ToolHeroChip(
          label: _isInLocalWordbook ? '已在生词本中' : '可加入生词本',
          accentColor: accent,
          icon: _isInLocalWordbook
              ? Icons.bookmark_added_rounded
              : Icons.bookmark_border_rounded,
        ),
        ToolHeroChip(
          label: state.associations.isEmpty
              ? '等待关联词'
              : '${state.associations.length} 个关联词',
          accentColor: accent,
          icon: Icons.hub_rounded,
        ),
      ],
      body: Column(
        children: [
          ToolSectionCard(
            accentColor: accent,
            title: '查询输入',
            subtitle: '输入英文单词后回车或点击查询。',
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _controller,
                    focusNode: _focusNode,
                    decoration: const InputDecoration(
                      hintText: '输入英文单词...',
                      prefixIcon: Icon(Icons.menu_book_rounded),
                    ),
                    textInputAction: TextInputAction.search,
                    onSubmitted: (_) => _lookup(),
                  ),
                ),
                const SizedBox(width: DS.spacing12),
                SparkleButton(
                  label: '查询',
                  onPressed: _lookup,
                  icon: const Icon(Icons.search_rounded),
                  loading: state.isLookingUp,
                ),
              ],
            ),
          ),
          const SizedBox(height: DS.spacing16),
          Expanded(
            child: ToolSectionCard(
              accentColor: accent,
              fillHeight: true,
              title: '查询结果',
              subtitle: '词义、例句、关联词和模型生成句都在这里。',
              child: result == null
                  ? ToolEmptyState(
                      icon: Icons.travel_explore_rounded,
                      title: '输入单词开始查询',
                      description: '查询完成后可以直接收藏到生词本，并继续生成例句。',
                      accentColor: accent,
                    )
                  : SingleChildScrollView(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            result['word'] as String? ?? '',
                            style: Theme.of(context)
                                .textTheme
                                .headlineMedium
                                ?.copyWith(
                                  color: DS.textPrimary,
                                  fontWeight: DS.fontWeightBold,
                                ),
                          ),
                          if ((result['phonetic'] as String?) != null) ...[
                            const SizedBox(height: DS.spacing6),
                            Text(
                              result['phonetic'] as String,
                              style: Theme.of(context)
                                  .textTheme
                                  .bodyLarge
                                  ?.copyWith(
                                    color: DS.textSecondary,
                                    fontStyle: FontStyle.italic,
                                  ),
                            ),
                          ],
                          if ((result['pos'] as String?) != null) ...[
                            const SizedBox(height: DS.spacing8),
                            ToolHeroChip(
                              label: result['pos'] as String,
                              accentColor: accent,
                              icon: Icons.sell_rounded,
                            ),
                          ],
                          const SizedBox(height: DS.spacing16),
                          if (definitions != null) ...[
                            Text(
                              '释义',
                              style: Theme.of(context)
                                  .textTheme
                                  .titleSmall
                                  ?.copyWith(
                                    color: DS.textPrimary,
                                    fontWeight: DS.fontWeightBold,
                                  ),
                            ),
                            const SizedBox(height: DS.spacing8),
                            ..._buildDefinitions(definitions),
                          ],
                          if (examples is List && examples.isNotEmpty) ...[
                            const SizedBox(height: DS.spacing16),
                            Text(
                              '词典例句',
                              style: Theme.of(context)
                                  .textTheme
                                  .titleSmall
                                  ?.copyWith(
                                    color: DS.textPrimary,
                                    fontWeight: DS.fontWeightBold,
                                  ),
                            ),
                            const SizedBox(height: DS.spacing8),
                            ...examples.take(3).map(
                                  (example) => Padding(
                                    padding: const EdgeInsets.only(
                                      bottom: DS.spacing8,
                                    ),
                                    child: Text(
                                      '• $example',
                                      style: Theme.of(context)
                                          .textTheme
                                          .bodyMedium
                                          ?.copyWith(
                                            color: DS.textSecondary,
                                            height: 1.55,
                                          ),
                                    ),
                                  ),
                                ),
                          ],
                          if (state.exampleSentence != null) ...[
                            const SizedBox(height: DS.spacing16),
                            Text(
                              '模型生成例句',
                              style: Theme.of(context)
                                  .textTheme
                                  .titleSmall
                                  ?.copyWith(
                                    color: DS.textPrimary,
                                    fontWeight: DS.fontWeightBold,
                                  ),
                            ),
                            const SizedBox(height: DS.spacing8),
                            Text(
                              state.exampleSentence!,
                              style: Theme.of(context)
                                  .textTheme
                                  .bodyMedium
                                  ?.copyWith(
                                    color: DS.textSecondary,
                                    height: 1.6,
                                  ),
                            ),
                          ],
                          if (state.associations.isNotEmpty) ...[
                            const SizedBox(height: DS.spacing16),
                            Text(
                              '关联词汇',
                              style: Theme.of(context)
                                  .textTheme
                                  .titleSmall
                                  ?.copyWith(
                                    color: DS.textPrimary,
                                    fontWeight: DS.fontWeightBold,
                                  ),
                            ),
                            const SizedBox(height: DS.spacing8),
                            Wrap(
                              spacing: DS.spacing10,
                              runSpacing: DS.spacing10,
                              children: state.associations
                                  .map(
                                    (association) => ToolChoiceChip(
                                      label: association,
                                      selected: false,
                                      onTap: () {
                                        _controller.text = association;
                                        _lookup();
                                      },
                                      accentColor: accent,
                                    ),
                                  )
                                  .toList(),
                            ),
                          ],
                        ],
                      ),
                    ),
            ),
          ),
        ],
      ),
      footer: Row(
        children: [
          Expanded(
            child: SparkleButton(
              label: '生成例句',
              variant: ButtonVariant.ghost,
              onPressed: result == null ? null : _generateSentence,
              icon: const Icon(Icons.auto_awesome_rounded),
            ),
          ),
          const SizedBox(width: DS.spacing12),
          Expanded(
            child: _isInLocalWordbook
                ? SparkleButton(
                    label: '移出生词本',
                    variant: ButtonVariant.ghost,
                    onPressed: _removeFromWordbook,
                    icon: const Icon(Icons.remove_circle_outline_rounded),
                  )
                : SparkleButton(
                    label: '加入生词本',
                    onPressed: result == null ? null : _addToWordbook,
                    icon: const Icon(Icons.bookmark_add_rounded),
                  ),
          ),
        ],
      ),
    );
  }

  List<Widget> _buildDefinitions(dynamic definitions) {
    if (definitions is List) {
      return definitions
          .asMap()
          .entries
          .map(
            (entry) => Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing6),
              child: Text(
                '${entry.key + 1}. ${entry.value}',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: DS.textSecondary,
                      height: 1.55,
                    ),
              ),
            ),
          )
          .toList();
    }

    return [
      Text(
        definitions.toString(),
        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: DS.textSecondary,
              height: 1.55,
            ),
      ),
    ];
  }
}
