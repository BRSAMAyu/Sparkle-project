// ignore_for_file: unawaited_futures, discarded_futures

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/features/knowledge/data/repositories/vocabulary_repository.dart';
import 'package:sparkle/features/knowledge/presentation/providers/vocabulary_provider.dart';
import 'package:sparkle/features/tools/models/tool_definition.dart';
import 'package:sparkle/features/tools/presentation/widgets/tool_shell.dart';
import 'package:sparkle/features/vocabulary/data/services/offline_dictionary_service.dart';

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
  bool _isDownloadingDictionary = false;
  int _installedPackageCount = 0;
  List<DictionaryPackageInfo> _availablePackages = const [];
  List<InstalledDictionaryPackage> _installedPackages = const [];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _focusNode.requestFocus();
      _refreshDictionaryPackages();
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  Future<void> _refreshDictionaryPackages() async {
    try {
      final repository = ref.read(vocabularyRepositoryProvider);
      final installed = await repository.getInstalledDictionaryPackageDetails();
      final available = await repository.getDictionaryPackages();
      if (!mounted) {
        return;
      }
      setState(() {
        _installedPackageCount = installed.length;
        _installedPackages = installed;
        _availablePackages = available;
      });
    } catch (_) {}
  }

  Future<void> _lookup() async {
    final word = _controller.text.trim();
    if (word.isEmpty) {
      AppFeedback.info(context, '请输入要查询的单词');
      return;
    }

    final notifier = ref.read(vocabularyProvider.notifier);
    await notifier.fetchWordbook();
    if (!mounted) {
      return;
    }
    final remoteWord = notifier.getWordbookEntryByWord(word);
    setState(() {
      _isInLocalWordbook = remoteWord != null;
    });

    await notifier.lookup(word);
    if (!mounted) {
      return;
    }
    notifier.fetchAssociations(word);
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

    final success = await ref.read(vocabularyProvider.notifier).addToWordbook(
          word: word,
          definition: definition,
          phonetic: result['phonetic'] as String?,
          contextSentence: state.exampleSentence,
          taskId: widget.taskId,
          partOfSpeech: result['pos'] as String?,
        );

    if (!mounted || !success) {
      return;
    }

    setState(() {
      _isInLocalWordbook = true;
    });

    if (mounted) {
      unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.success));
      AppFeedback.success(context, '已添加 "$word" 到生词本');
    }
  }

  Future<void> _removeFromWordbook() async {
    final word = _controller.text.trim().toLowerCase();
    if (word.isEmpty) {
      return;
    }
    final notifier = ref.read(vocabularyProvider.notifier);
    await notifier.fetchWordbook();
    if (!mounted) {
      return;
    }
    final remoteWord = notifier.getWordbookEntryByWord(word);

    if (remoteWord != null && remoteWord['id'] != null) {
      await notifier.deleteWordbookEntry(remoteWord['id'] as String);
      if (!mounted) {
        return;
      }
      setState(() => _isInLocalWordbook = false);
      unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.tap));
      AppFeedback.info(context, '已从生词本移除 "$word"');
    }
  }

  Future<void> _downloadStarterDictionary() async {
    final packageId = _preferredStarterPackageId();
    await _downloadDictionaryPackage(packageId);
  }

  Future<void> _downloadDictionaryPackage(String? packageId) async {
    setState(() {
      _isDownloadingDictionary = true;
    });
    try {
      final repository = ref.read(vocabularyRepositoryProvider);
      final targetId = packageId ??
          _preferredStarterPackageId() ??
          _firstAvailablePackageId();
      if (targetId == null) {
        throw Exception('暂无可下载的离线词典包');
      }
      await repository.downloadDictionaryPackage(targetId);
      await _refreshDictionaryPackages();
      if (mounted) {
        AppFeedback.success(context, '离线词典已下载，可优先本地查词');
      }
    } catch (e) {
      if (mounted) {
        AppFeedback.error(context, '离线词典下载失败: $e');
      }
    } finally {
      if (mounted) {
        setState(() {
          _isDownloadingDictionary = false;
        });
      }
    }
  }

  Future<void> _removeDictionaryPackage(String packageId) async {
    try {
      await ref
          .read(vocabularyRepositoryProvider)
          .removeDictionaryPackage(packageId);
      await _refreshDictionaryPackages();
      if (!mounted) {
        return;
      }
      AppFeedback.info(context, '已移除离线词典包');
    } catch (e) {
      if (!mounted) {
        return;
      }
      AppFeedback.error(context, '移除离线词典包失败: $e');
    }
  }

  Future<void> _openDictionaryPackageSheet() async {
    if (_availablePackages.isEmpty && !_isDownloadingDictionary) {
      await _refreshDictionaryPackages();
    }
    if (!mounted) {
      return;
    }

    final installedById = {
      for (final package in _installedPackages) package.id: package,
    };

    await showSensoryModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (context) {
        final theme = Theme.of(context);
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(
              DS.spacing16,
              DS.spacing16,
              DS.spacing16,
              DS.spacing24,
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '离线词典包',
                  style: theme.textTheme.titleLarge?.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
                ),
                const SizedBox(height: DS.spacing8),
                Text(
                  '优先使用本地 Oxford 词典，减少网络依赖，也能减轻云端服务器压力。',
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: DS.textSecondary,
                    height: 1.5,
                  ),
                ),
                const SizedBox(height: DS.spacing16),
                Flexible(
                  child: ListView.separated(
                    shrinkWrap: true,
                    itemCount: _availablePackages.length,
                    separatorBuilder: (_, __) =>
                        const SizedBox(height: DS.spacing12),
                    itemBuilder: (context, index) {
                      final package = _availablePackages[index];
                      final installed = installedById[package.id];
                      return DecoratedBox(
                        decoration: BoxDecoration(
                          color: DS.surfaceSecondary,
                          borderRadius: DS.borderRadius16,
                          border: Border.all(
                            color: installed != null
                                ? DS.prismBlue.withValues(alpha: 0.28)
                                : DS.border,
                          ),
                        ),
                        child: Padding(
                          padding: const EdgeInsets.all(DS.spacing16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  Expanded(
                                    child: Text(
                                      package.name,
                                      style:
                                          theme.textTheme.titleMedium?.copyWith(
                                        fontWeight: DS.fontWeightBold,
                                      ),
                                    ),
                                  ),
                                  if (installed != null)
                                    Container(
                                      padding: const EdgeInsets.symmetric(
                                        horizontal: DS.spacing8,
                                        vertical: DS.spacing4,
                                      ),
                                      decoration: BoxDecoration(
                                        color: DS.prismBlue
                                            .withValues(alpha: 0.12),
                                        borderRadius: DS.borderRadiusFull,
                                      ),
                                      child: Text(
                                        '已安装',
                                        style: theme.textTheme.labelSmall
                                            ?.copyWith(
                                          color: DS.prismBlue,
                                          fontWeight: DS.fontWeightBold,
                                        ),
                                      ),
                                    ),
                                ],
                              ),
                              const SizedBox(height: DS.spacing6),
                              Text(
                                package.description.isEmpty
                                    ? 'Oxford 优先离线词典包'
                                    : package.description,
                                style: theme.textTheme.bodyMedium?.copyWith(
                                  color: DS.textSecondary,
                                  height: 1.45,
                                ),
                              ),
                              const SizedBox(height: DS.spacing10),
                              Wrap(
                                spacing: DS.spacing8,
                                runSpacing: DS.spacing8,
                                children: [
                                  _buildMetaChip('${package.entryCount} 词条'),
                                  _buildMetaChip(package.packageScope),
                                  if (package.sizeBytes != null)
                                    _buildMetaChip(
                                        _formatBytes(package.sizeBytes!)),
                                  if (installed != null)
                                    _buildMetaChip(
                                      '安装于 ${_formatInstalledAt(installed.installedAt)}',
                                    ),
                                ],
                              ),
                              const SizedBox(height: DS.spacing12),
                              Row(
                                children: [
                                  Expanded(
                                    child: SparkleButton(
                                      label:
                                          installed != null ? '重新下载' : '下载到本地',
                                      onPressed: _isDownloadingDictionary
                                          ? null
                                          : () async {
                                              Navigator.of(context).pop();
                                              await _downloadDictionaryPackage(
                                                package.id,
                                              );
                                            },
                                      loading: _isDownloadingDictionary,
                                      icon: Icon(
                                        installed != null
                                            ? Icons.sync_rounded
                                            : Icons.download_rounded,
                                      ),
                                      expand: true,
                                    ),
                                  ),
                                  if (installed != null) ...[
                                    const SizedBox(width: DS.spacing10),
                                    Expanded(
                                      child: SparkleButton(
                                        label: '移除',
                                        variant: ButtonVariant.ghost,
                                        onPressed: () async {
                                          Navigator.of(context).pop();
                                          await _removeDictionaryPackage(
                                              package.id);
                                        },
                                        icon: const Icon(
                                            Icons.delete_outline_rounded),
                                        expand: true,
                                      ),
                                    ),
                                  ],
                                ],
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(vocabularyProvider);
    final accent = DS.prismBlue;
    final result = state.lookupResult;
    final definitions = result?['definitions'];
    final examples = result?['examples'];
    final error = state.error;

    return ToolShell(
      surface: widget.surface,
      icon: Icons.search_rounded,
      title: '查词',
      subtitle: '用来做快速词义确认、例句生成和关联词扩展，查询结果可以直接收进本地生词本。',
      accentColor: accent,
      compactHeader: true,
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
        ToolHeroChip(
          label: _installedPackageCount > 0
              ? '$_installedPackageCount 个离线词典包'
              : '未下载离线词典',
          accentColor: accent,
          icon: _installedPackageCount > 0
              ? Icons.download_done_rounded
              : Icons.cloud_download_rounded,
        ),
      ],
      body: Column(
        children: [
          ToolSectionCard(
            accentColor: accent,
            title: '查询输入',
            subtitle: '输入英文单词后回车或点击查询。Oxford 词典优先，本地离线包会先于网络命中。',
            trailing: SparkleButton(
              label: _installedPackageCount > 0 ? '管理离线词典' : '下载离线词典',
              onPressed: _isDownloadingDictionary
                  ? null
                  : (_installedPackageCount > 0
                      ? _openDictionaryPackageSheet
                      : _downloadStarterDictionary),
              icon: Icon(
                _installedPackageCount > 0
                    ? Icons.library_books_rounded
                    : Icons.download_rounded,
              ),
              variant: ButtonVariant.ghost,
              loading: _isDownloadingDictionary,
            ),
            child: LayoutBuilder(
              builder: (context, constraints) {
                final compact = constraints.maxWidth < 520;
                if (compact) {
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      TextField(
                        controller: _controller,
                        focusNode: _focusNode,
                        decoration: const InputDecoration(
                          hintText: '输入英文单词...',
                          prefixIcon: Icon(Icons.menu_book_rounded),
                        ),
                        textInputAction: TextInputAction.search,
                        onSubmitted: (_) => _lookup(),
                      ),
                      const SizedBox(height: DS.spacing12),
                      SparkleButton(
                        label: '查询',
                        onPressed: _lookup,
                        icon: const Icon(Icons.search_rounded),
                        loading: state.isLookingUp,
                        expand: true,
                      ),
                    ],
                  );
                }

                return Row(
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
                );
              },
            ),
          ),
          const SizedBox(height: DS.spacing16),
          ConstrainedBox(
            constraints: const BoxConstraints(minHeight: 200),
            child: ToolSectionCard(
              accentColor: accent,
              title: '查询结果',
              subtitle: '词义、例句、关联词和模型生成句都在这里。',
              child: result == null
                  ? ToolEmptyState(
                      icon: Icons.travel_explore_rounded,
                      title: error == null ? '输入单词开始查询' : '查询暂时失败',
                      description: error ?? '查询完成后可以直接收藏到生词本，并继续生成例句。',
                      accentColor: accent,
                    )
                  : SingleChildScrollView(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          LayoutBuilder(
                            builder: (context, constraints) {
                              final compact = constraints.maxWidth < 360;
                              final phonetic = result['phonetic'] as String?;
                              final partOfSpeech = result['pos'] as String?;

                              return Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    result['word'] as String? ?? '',
                                    maxLines: 2,
                                    overflow: TextOverflow.ellipsis,
                                    style: Theme.of(context)
                                        .textTheme
                                        .headlineMedium
                                        ?.copyWith(
                                          color: DS.textPrimary,
                                          fontWeight: DS.fontWeightBold,
                                        ),
                                  ),
                                  if (phonetic != null || partOfSpeech != null)
                                    Padding(
                                      padding: const EdgeInsets.only(
                                        top: DS.spacing8,
                                      ),
                                      child: Wrap(
                                        spacing: DS.spacing8,
                                        runSpacing: DS.spacing8,
                                        crossAxisAlignment:
                                            WrapCrossAlignment.center,
                                        children: [
                                          if (phonetic != null)
                                            Text(
                                              phonetic,
                                              style: Theme.of(context)
                                                  .textTheme
                                                  .bodyMedium
                                                  ?.copyWith(
                                                    color: DS.textSecondary,
                                                    fontStyle: FontStyle.italic,
                                                  ),
                                            ),
                                          if (partOfSpeech != null)
                                            DecoratedBox(
                                              decoration: BoxDecoration(
                                                color: accent.withValues(
                                                  alpha: 0.12,
                                                ),
                                                borderRadius:
                                                    DS.borderRadiusFull,
                                                border: Border.all(
                                                  color: accent.withValues(
                                                    alpha: 0.18,
                                                  ),
                                                ),
                                              ),
                                              child: Padding(
                                                padding:
                                                    const EdgeInsets.symmetric(
                                                  horizontal: DS.spacing8,
                                                  vertical: DS.spacing6,
                                                ),
                                                child: Text(
                                                  compact
                                                      ? partOfSpeech
                                                      : '词性 · $partOfSpeech',
                                                  maxLines: 1,
                                                  overflow:
                                                      TextOverflow.ellipsis,
                                                  style: Theme.of(context)
                                                      .textTheme
                                                      .labelSmall
                                                      ?.copyWith(
                                                        color: accent,
                                                        fontWeight:
                                                            DS.fontWeightBold,
                                                      ),
                                                ),
                                              ),
                                            ),
                                        ],
                                      ),
                                    ),
                                ],
                              );
                            },
                          ),
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
      footer: LayoutBuilder(
        builder: (context, constraints) {
          final compact = constraints.maxWidth < 520;
          final secondaryAction = _isInLocalWordbook
              ? SparkleButton(
                  label: '移出生词本',
                  variant: ButtonVariant.ghost,
                  onPressed: _removeFromWordbook,
                  icon: const Icon(Icons.remove_circle_outline_rounded),
                  expand: true,
                )
              : SparkleButton(
                  label: '加入生词本',
                  onPressed: result == null ? null : _addToWordbook,
                  icon: const Icon(Icons.bookmark_add_rounded),
                  expand: true,
                );

          if (compact) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                SparkleButton(
                  label: '生成例句',
                  variant: ButtonVariant.ghost,
                  onPressed: result == null ? null : _generateSentence,
                  icon: const Icon(Icons.auto_awesome_rounded),
                  expand: true,
                ),
                const SizedBox(height: DS.spacing12),
                secondaryAction,
              ],
            );
          }

          return Row(
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
              Expanded(child: secondaryAction),
            ],
          );
        },
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

  Widget _buildMetaChip(String label) => DecoratedBox(
        decoration: BoxDecoration(
          color: DS.surfaceTertiary,
          borderRadius: DS.borderRadiusFull,
        ),
        child: Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing8,
            vertical: DS.spacing6,
          ),
          child: Text(
            label,
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
                  color: DS.textSecondary,
                ),
          ),
        ),
      );

  String _formatBytes(int bytes) {
    if (bytes < 1024) {
      return '$bytes B';
    }
    if (bytes < 1024 * 1024) {
      return '${(bytes / 1024).toStringAsFixed(1)} KB';
    }
    return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  }

  String _formatInstalledAt(DateTime value) {
    final month = value.month.toString().padLeft(2, '0');
    final day = value.day.toString().padLeft(2, '0');
    return '${value.year}-$month-$day';
  }

  String? _preferredStarterPackageId() {
    for (final package in _availablePackages) {
      if (package.packageScope == 'starter') {
        return package.id;
      }
    }
    return null;
  }

  String? _firstAvailablePackageId() {
    if (_availablePackages.isEmpty) {
      return null;
    }
    return _availablePackages.first.id;
  }
}
