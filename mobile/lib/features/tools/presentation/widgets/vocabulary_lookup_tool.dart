// ignore_for_file: unawaited_futures, discarded_futures

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/knowledge/data/repositories/vocabulary_repository.dart';
import 'package:sparkle/features/knowledge/presentation/providers/vocabulary_provider.dart';
import 'package:sparkle/features/tools/models/tool_definition.dart';
import 'package:sparkle/features/tools/presentation/widgets/tool_shell.dart';
import 'package:sparkle/features/vocabulary/data/services/offline_dictionary_service.dart';
import 'package:sparkle/core/services/i18n_service.dart';

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
  bool _loadError = false;
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
    if (mounted && _loadError) {
      setState(() {
        _loadError = false;
      });
    }
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
        _loadError = false;
      });
    } catch (e) {
      if (mounted) {
        setState(() {
          _loadError = true;
        });
      }
    }
  }

  Future<void> _lookup() async {
    final word = _controller.text.trim();
    if (word.isEmpty) {
      AppFeedback.info(context, context.l10n.vocabularyLookupEnterWord);
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
      AppFeedback.success(
          context, context.l10n.vocabularyLookupAddedToWordbook(word));
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
      AppFeedback.info(
          context, context.l10n.vocabularyLookupRemovedFromWordbook(word));
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
        throw Exception(context.l10n.vocabularyLookupNoPackage);
      }
      await repository.downloadDictionaryPackage(targetId);
      await _refreshDictionaryPackages();
      if (mounted) {
        AppFeedback.success(
            context, context.l10n.vocabularyLookupOfflineDownloaded);
      }
    } catch (e) {
      if (mounted) {
        AppFeedback.error(context,
            context.l10n.vocabularyLookupOfflineDownloadFailed(e.toString()));
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
      AppFeedback.info(context, context.l10n.vocabularyLookupOfflineRemoved);
    } catch (e) {
      if (!mounted) {
        return;
      }
      AppFeedback.error(context,
          context.l10n.vocabularyLookupOfflineRemoveFailed(e.toString()));
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
                  I18nService.instance.isChinese
                      ? '离线词典包'
                      : 'Offline Dictionary Packages',
                  style: theme.textTheme.titleLarge?.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
                ),
                const SizedBox(height: DS.spacing8),
                Text(
                  I18nService.instance.isChinese
                      ? '优先使用本地 Oxford 词典，减少网络依赖，也能减轻云端服务器压力。'
                      : 'Prefer local Oxford dictionary to reduce network dependency and cloud server load.',
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
                                        I18nService.instance.isChinese
                                            ? '已安装'
                                            : 'Installed',
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
                                    ? (I18nService.instance.isChinese
                                        ? 'Oxford 优先离线词典包'
                                        : 'Oxford Preferred Offline Dictionary Package')
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
                                  _buildMetaChip(context.l10n
                                      .toolsVocabEntryCount(
                                          package.entryCount)),
                                  _buildMetaChip(package.packageScope),
                                  if (package.sizeBytes != null)
                                    _buildMetaChip(
                                      _formatBytes(package.sizeBytes!),
                                    ),
                                  if (installed != null)
                                    _buildMetaChip(
                                      '${I18nService.instance.isChinese ? '安装于' : 'Installed'} ${_formatInstalledAt(installed.installedAt)}',
                                    ),
                                ],
                              ),
                              const SizedBox(height: DS.spacing12),
                              Row(
                                children: [
                                  Expanded(
                                    child: SparkleButton(
                                      label: installed != null
                                          ? (I18nService.instance.isChinese
                                              ? '重新下载'
                                              : 'Redownload')
                                          : (I18nService.instance.isChinese
                                              ? '下载到本地'
                                              : 'Download Locally'),
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
                                        label: context.l10n.toolsVocabRemove,
                                        variant: ButtonVariant.ghost,
                                        onPressed: () async {
                                          Navigator.of(context).pop();
                                          await _removeDictionaryPackage(
                                            package.id,
                                          );
                                        },
                                        icon: const Icon(
                                          Icons.delete_outline_rounded,
                                        ),
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
      title: context.l10n.toolsVocabTitle,
      subtitle: context.l10n.toolsVocabSubtitle,
      accentColor: accent,
      compactHeader: true,
      heroChips: [
        ToolHeroChip(
          label: _isInLocalWordbook
              ? context.l10n.toolsVocabInWordbook
              : context.l10n.toolsVocabAddToWordbook,
          accentColor: accent,
          icon: _isInLocalWordbook
              ? Icons.bookmark_added_rounded
              : Icons.bookmark_border_rounded,
        ),
        ToolHeroChip(
          label: state.associations.isEmpty
              ? (I18nService.instance.isChinese
                  ? '等待关联词'
                  : 'Waiting for associations')
              : '${state.associations.length} ${I18nService.instance.isChinese ? '个关联词' : 'associations'}',
          accentColor: accent,
          icon: Icons.hub_rounded,
        ),
        ToolHeroChip(
          label: _installedPackageCount > 0
              ? '$_installedPackageCount ${I18nService.instance.isChinese ? '个离线词典包' : 'offline dictionaries'}'
              : (I18nService.instance.isChinese
                  ? '未下载离线词典'
                  : 'No offline dictionary'),
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
            title: context.l10n.toolsVocabInput,
            subtitle: context.l10n.toolsVocabInputDesc,
            trailing: SparkleButton(
              label: _installedPackageCount > 0
                  ? context.l10n.toolsVocabManageOffline
                  : context.l10n.toolsVocabDownloadOffline,
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
                      if (_loadError) ...[
                        _buildOfflineDictionaryError(context),
                        const SizedBox(height: DS.spacing12),
                      ],
                      TextField(
                        controller: _controller,
                        focusNode: _focusNode,
                        decoration: InputDecoration(
                          hintText: context.l10n.toolsVocabInputHint,
                          prefixIcon: Icon(Icons.menu_book_rounded),
                        ),
                        textInputAction: TextInputAction.search,
                        onSubmitted: (_) => _lookup(),
                      ),
                      const SizedBox(height: DS.spacing12),
                      SparkleButton(
                        label: context.l10n.toolsVocabSearch,
                        onPressed: _lookup,
                        icon: const Icon(Icons.search_rounded),
                        loading: state.isLookingUp,
                        expand: true,
                      ),
                    ],
                  );
                }

                return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          if (_loadError) ...[
                            _buildOfflineDictionaryError(context),
                            const SizedBox(height: DS.spacing12),
                          ],
                          TextField(
                            controller: _controller,
                            focusNode: _focusNode,
                            decoration: InputDecoration(
                              hintText: context.l10n.toolsVocabInputHint,
                              prefixIcon: Icon(Icons.menu_book_rounded),
                            ),
                            textInputAction: TextInputAction.search,
                            onSubmitted: (_) => _lookup(),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: DS.spacing12),
                    SparkleButton(
                      label: context.l10n.toolsVocabSearch,
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
              title: context.l10n.toolsVocabResult,
              subtitle: context.l10n.toolsVocabResultDesc,
              child: result == null
                  ? ToolEmptyState(
                      icon: Icons.travel_explore_rounded,
                      title: error == null
                          ? context.l10n.toolsVocabStartHint
                          : context.l10n.toolsVocabSearchFailed,
                      description: error ?? context.l10n.toolsVocabResultHint,
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
                                                      : '${I18nService.instance.isChinese ? '词性' : 'Part of Speech'} · $partOfSpeech',
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
                              I18nService.instance.isChinese
                                  ? '释义'
                                  : 'Definitions',
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
                              I18nService.instance.isChinese
                                  ? '词典例句'
                                  : 'Dictionary Examples',
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
                                    child: Row(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        Container(
                                          width: 5,
                                          height: 5,
                                          margin: const EdgeInsets.only(
                                              top: 8, right: 8),
                                          decoration: BoxDecoration(
                                            color: DS.textSecondary,
                                            shape: BoxShape.circle,
                                          ),
                                        ),
                                        Expanded(
                                          child: Text(
                                            example.toString(),
                                            style: Theme.of(context)
                                                .textTheme
                                                .bodyMedium
                                                ?.copyWith(
                                                  color: DS.textSecondary,
                                                  height: 1.55,
                                                ),
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ),
                          ],
                          if (state.exampleSentence != null) ...[
                            const SizedBox(height: DS.spacing16),
                            Text(
                              I18nService.instance.isChinese
                                  ? '模型生成例句'
                                  : 'Model Generated Example',
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
                              I18nService.instance.isChinese
                                  ? '关联词汇'
                                  : 'Related Words',
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
                  label: context.l10n.toolsVocabRemoveFromWordbook,
                  variant: ButtonVariant.ghost,
                  onPressed: _removeFromWordbook,
                  icon: const Icon(Icons.remove_circle_outline_rounded),
                  expand: true,
                )
              : SparkleButton(
                  label: context.l10n.toolsVocabAddToWordbookAction,
                  onPressed: result == null ? null : _addToWordbook,
                  icon: const Icon(Icons.bookmark_add_rounded),
                  expand: true,
                );

          if (compact) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                SparkleButton(
                  label: context.l10n.toolsVocabGenerateExample,
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
                  label: context.l10n.toolsVocabGenerateExample,
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

  Widget _buildOfflineDictionaryError(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: DS.semanticError.withValues(alpha: 0.08),
        borderRadius: DS.borderRadius12,
        border: Border.all(
          color: DS.semanticError.withValues(alpha: 0.2),
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(DS.spacing12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(
              Icons.error_outline_rounded,
              color: DS.semanticError,
              size: 18,
            ),
            const SizedBox(width: DS.spacing10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    context.l10n.networkErrorRetry,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: DS.textPrimary,
                          fontWeight: DS.fontWeightBold,
                        ),
                  ),
                  const SizedBox(height: DS.spacing4),
                  Text(
                    context.l10n.vocabularyLookupOfflineDesc,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: DS.textSecondary,
                          height: 1.45,
                        ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: DS.spacing8),
            TextButton(
              onPressed: _refreshDictionaryPackages,
              child: Text(context.l10n.retry),
            ),
          ],
        ),
      ),
    );
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
