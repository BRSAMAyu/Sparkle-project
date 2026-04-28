// ignore_for_file: inference_failure_on_instance_creation

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:isar/isar.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/knowledge/data/repositories/vocabulary_repository.dart';
import 'package:sparkle/features/tools/models/tool_definition.dart';
import 'package:sparkle/features/tools/presentation/widgets/tool_shell.dart';
import 'package:sparkle/features/translation/data/services/translation_service.dart';
import 'package:sparkle/features/translation/presentation/providers/translation_history_provider.dart';
import 'package:sparkle/features/translation/translation_routes.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

class Language {
  const Language({
    required this.code,
    required this.name,
    this.flag,
  });

  final String code;
  final String name;
  final String? flag;

  @override
  String toString() => name;
}

const supportedLanguages = [
  Language(code: 'auto', name: '自动检测', flag: '🔍'),
  Language(code: 'zh', name: '中文', flag: '🇨🇳'),
  Language(code: 'en', name: 'English', flag: '🇺🇸'),
  Language(code: 'ja', name: '日本語', flag: '🇯🇵'),
  Language(code: 'ko', name: '한국어', flag: '🇰🇷'),
  Language(code: 'fr', name: 'Français', flag: '🇫🇷'),
  Language(code: 'de', name: 'Deutsch', flag: '🇩🇪'),
  Language(code: 'es', name: 'Español', flag: '🇪🇸'),
  Language(code: 'ru', name: 'Русский', flag: '🇷🇺'),
];

class TranslatorTool extends ConsumerStatefulWidget {
  const TranslatorTool({
    super.key,
    this.surface = ToolSurface.page,
  });

  final ToolSurface surface;

  @override
  ConsumerState<TranslatorTool> createState() => _TranslatorToolState();
}

class _TranslatorToolState extends ConsumerState<TranslatorTool> {
  final TextEditingController _inputController = TextEditingController();
  String _output = '';
  bool _isLoading = false;
  String? _errorMessage;
  Id? _currentTranslationId;
  int _currentRating = 3;
  bool _isFavorited = false;
  bool _isAddingToWordbook = false;

  Language _sourceLanguage = supportedLanguages[0];
  Language _targetLanguage = supportedLanguages[2];

  @override
  void dispose() {
    _inputController.dispose();
    super.dispose();
  }

  Future<void> _translate() async {
    if (_inputController.text.trim().isEmpty) {
      AppFeedback.info(context, '请输入要翻译的文本');
      return;
    }

    setState(() {
      _isLoading = true;
      _output = '';
      _errorMessage = null;
    });

    try {
      final translationService = ref.read(translationServiceProvider);
      final result = await translationService.translate(
        text: _inputController.text,
        sourceLang: _sourceLanguage.code,
        targetLang: _targetLanguage.code,
      );
      if (!mounted) return;
      if (result.success) {
        final translatedText = result.translation;
        setState(() {
          _output = translatedText;
          _currentRating = 3;
          _isFavorited = false;
        });
        await _saveTranslation(translatedText);
      } else {
        setState(() {
          _errorMessage = result.meta['error'] as String? ?? context.l10n.toolsTransFailed;
        });
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _errorMessage = context.l10n.toolsTransError(e.toString());
      });
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  void _swapLanguages() {
    if (_sourceLanguage.code == 'auto') {
      setState(() {
        _targetLanguage = supportedLanguages[1];
      });
      return;
    }
    setState(() {
      final temp = _sourceLanguage;
      _sourceLanguage = _targetLanguage;
      _targetLanguage = temp;
      if (_output.isNotEmpty) {
        _inputController.text = _output;
        _output = '';
      }
    });
  }

  Future<void> _saveTranslation(String translatedText) async {
    try {
      if (!mounted) return;
      final historyNotifier = ref.read(translationHistoryProvider.notifier);
      final similar =
          await historyNotifier.findSimilar(
                originalText: _inputController.text,
                sourceLanguage: _sourceLanguage.code,
                targetLanguage: _targetLanguage.code,
              );

      if (!mounted) return;
      if (similar != null) {
        setState(() {
          _currentTranslationId = similar.id;
          _currentRating = similar.rating;
          _isFavorited = similar.isFavorited;
        });
        return;
      }

      final id =
          await historyNotifier.saveTranslation(
                originalText: _inputController.text,
                translatedText: translatedText,
                sourceLanguage: _sourceLanguage.code,
                targetLanguage: _targetLanguage.code,
                rating: _currentRating,
                isFavorited: _isFavorited,
              );
      if (!mounted) return;
      setState(() {
        _currentTranslationId = id;
      });
    } catch (e) {
      debugPrint('Error auto-saving translation: $e');
    }
  }

  void _updateRating(int rating) {
    setState(() {
      _currentRating = rating;
    });
    if (_currentTranslationId != null && mounted) {
      unawaited(
        ref
            .read(translationHistoryProvider.notifier)
            .updateRating(_currentTranslationId!, rating),
      );
    }
  }

  Future<void> _toggleFavorite() async {
    final newValue = !_isFavorited;
    setState(() {
      _isFavorited = newValue;
    });
    if (_currentTranslationId != null && mounted) {
      await ref
          .read(translationHistoryProvider.notifier)
          .toggleFavorite(_currentTranslationId!);
    }
  }

  void _copyToClipboard() {
    unawaited(Clipboard.setData(ClipboardData(text: _output)));
    AppFeedback.info(context, '已复制到剪贴板');
  }

  bool get _canAddToWordbook {
    final text = _inputController.text.trim();
    return RegExp(r"^[A-Za-z][A-Za-z'-]{0,48}$").hasMatch(text) &&
        _output.trim().isNotEmpty;
  }

  Future<void> _addToWordbook() async {
    if (!_canAddToWordbook || _isAddingToWordbook) {
      return;
    }

    setState(() {
      _isAddingToWordbook = true;
    });
    try {
      if (!mounted) return;
      final repository = ref.read(vocabularyRepositoryProvider);
      final word = _inputController.text.trim().toLowerCase();
      var definition = _output.trim();
      String? phonetic;
      String? partOfSpeech;

      try {
        final lookup = await repository.lookup(word);
        if (!mounted) return;
        final definitions = lookup['definitions'];
        if (definitions is List && definitions.isNotEmpty) {
          definition = definitions.join('; ');
        }
        phonetic = lookup['phonetic'] as String?;
        partOfSpeech = lookup['pos'] as String?;
      } catch (_) {}

      await repository.addToWordbook(
        word: word,
        definition: definition,
        phonetic: phonetic,
        contextSentence: _output.trim(),
        partOfSpeech: partOfSpeech,
      );
      if (mounted) {
        AppFeedback.success(context, '已加入单词本');
      }
    } catch (e) {
      if (mounted) {
        AppFeedback.error(context, context.l10n.toolsTransAddWordFailed(e.toString()));
      }
    } finally {
      if (mounted) {
        setState(() {
          _isAddingToWordbook = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final accent = DS.prismPurple;
    final inputLength = _inputController.text.trim().length;
    final outputLength = _output.trim().length;

    return ToolShell(
      surface: widget.surface,
      icon: Icons.translate_rounded,
      title: context.l10n.toolsTransTitle,
      subtitle: context.l10n.toolsTransSubtitle,
      accentColor: accent,
      compactHeader: true,
      headerAction: SparkleIconButton(
        onPressed: () {
          if (context.mounted) {
            unawaited(context.push(TranslationRoutes.history));
          }
        },
        icon: const Icon(Icons.history_rounded),
        variant: ButtonVariant.ghost,
      ),
      heroChips: [
        ToolHeroChip(
          label: '${_sourceLanguage.name} → ${_targetLanguage.name}',
          accentColor: accent,
          icon: Icons.swap_horiz_rounded,
        ),
        ToolHeroChip(
          label: _isFavorited ? context.l10n.toolsTransFavorited : context.l10n.toolsTransAutoSave,
          accentColor: accent,
          icon: _isFavorited ? Icons.favorite_rounded : Icons.archive_rounded,
        ),
      ],
      body: Column(
        children: [
          ToolMetricRow(
            children: [
              ToolMetricCard(
                label: context.l10n.toolsTransInputLen,
                value: '$inputLength',
                accentColor: accent,
                icon: Icons.edit_note_rounded,
                caption: '建议控制在可读段落内',
              ),
              ToolMetricCard(
                label: context.l10n.toolsTransOutputLen,
                value: '$outputLength',
                accentColor: accent,
                icon: Icons.auto_fix_high_rounded,
                caption: _isLoading ? '翻译生成中' : '翻译完成后可复制',
              ),
            ],
          ),
          const SizedBox(height: DS.spacing16),
          ToolSectionCard(
            accentColor: accent,
            title: context.l10n.toolsTransDirection,
            subtitle: context.l10n.toolsTransDirectionDesc,
            trailing: SparkleButton(
              label: context.l10n.toolsTransSwap,
              variant: ButtonVariant.ghost,
              onPressed: _swapLanguages,
              icon: const Icon(Icons.swap_horiz_rounded),
            ),
            child: LayoutBuilder(
              builder: (context, constraints) {
                final compact = constraints.maxWidth < 560;
                final sourceDropdown = _LanguageDropdown(
                  value: _sourceLanguage,
                  items: supportedLanguages,
                  onChanged: (lang) => setState(() => _sourceLanguage = lang),
                );
                final targetDropdown = _LanguageDropdown(
                  value: _targetLanguage,
                  items: supportedLanguages
                      .where((language) => language.code != 'auto')
                      .toList(),
                  onChanged: (lang) => setState(() => _targetLanguage = lang),
                );

                if (compact) {
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      sourceDropdown,
                      const SizedBox(height: DS.spacing12),
                      targetDropdown,
                    ],
                  );
                }

                return Row(
                  children: [
                    Expanded(child: sourceDropdown),
                    const SizedBox(width: DS.spacing12),
                    Expanded(child: targetDropdown),
                  ],
                );
              },
            ),
          ),
          const SizedBox(height: DS.spacing16),
          LayoutBuilder(
            builder: (context, constraints) {
              final compact = constraints.maxWidth < 720;
              final inputCard = ToolSectionCard(
                accentColor: accent,
                title: context.l10n.toolsTransSource,
                subtitle: context.l10n.toolsTransSourceDesc,
                trailing: IconButton(
                  onPressed: () {
                    setState(() {
                      _inputController.clear();
                      _output = '';
                    });
                  },
                  icon: const Icon(Icons.close_rounded),
                ),
                child: SizedBox(
                  height: (MediaQuery.sizeOf(context).height * 0.2).clamp(140.0, 250.0),
                  child: TextField(
                    controller: _inputController,
                    maxLines: null,
                    expands: true,
                    textAlignVertical: TextAlignVertical.top,
                    decoration: const InputDecoration(
                      hintText: context.l10n.toolsTransInputHint,
                      border: InputBorder.none,
                    ),
                  ),
                ),
              );
              final outputCard = ToolSectionCard(
                accentColor: accent,
                title: context.l10n.toolsTransTarget,
                subtitle: context.l10n.toolsTransTargetDesc,
                trailing: _output.isEmpty
                    ? null
                    : IconButton(
                        onPressed: _toggleFavorite,
                        icon: Icon(
                          _isFavorited
                              ? Icons.favorite_rounded
                              : Icons.favorite_border_rounded,
                          color: _isFavorited ? DS.error : DS.textSecondary,
                        ),
                      ),
                child: _isLoading
                    ? Center(
                        child: CircularProgressIndicator(color: accent),
                      )
                    : _errorMessage != null
                        ? ToolEmptyState(
                            icon: Icons.error_outline_rounded,
                            title: context.l10n.toolsTransIncomplete,
                            description: _errorMessage!,
                            accentColor: DS.error,
                          )
                        : _output.isEmpty
                            ? ToolEmptyState(
                                icon: Icons.translate_rounded,
                                title: context.l10n.toolsTransWaiting,
                                description: context.l10n.toolsTransWaitingDesc,
                                accentColor: accent,
                              )
                            : Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  ConstrainedBox(
                                    constraints: const BoxConstraints(maxHeight: 200),
                                    child: SingleChildScrollView(
                                      child: SelectableText(
                                        _output,
                                        style: Theme.of(context)
                                            .textTheme
                                            .bodyLarge
                                            ?.copyWith(
                                              color: DS.textPrimary,
                                              height: 1.6,
                                            ),
                                      ),
                                    ),
                                  ),
                                  const SizedBox(height: DS.spacing16),
                                  Wrap(
                                    spacing: DS.spacing10,
                                    runSpacing: DS.spacing10,
                                    children: List.generate(
                                      5,
                                      (index) => ToolChoiceChip(
                                        label: context.l10n.toolsTransStarCount,
                                        selected: _currentRating == index + 1,
                                        onTap: () => _updateRating(index + 1),
                                        accentColor: accent,
                                        icon: Icons.star_rounded,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
              );

              if (compact) {
                return Column(
                  children: [
                    inputCard,
                    const SizedBox(height: DS.spacing16),
                    ConstrainedBox(
                      constraints: const BoxConstraints(minHeight: 200),
                      child: outputCard,
                    ),
                  ],
                );
              }

              return IntrinsicHeight(
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(minHeight: 300),
                        child: inputCard,
                      ),
                    ),
                    const SizedBox(width: DS.spacing16),
                    Expanded(
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(minHeight: 300),
                        child: outputCard,
                      ),
                    ),
                  ],
                ),
              );
            },
          ),
          if (_canAddToWordbook) ...[
            const SizedBox(height: DS.spacing16),
            ToolSectionCard(
              accentColor: accent,
              title: context.l10n.toolsTransWordbookLink,
              subtitle: context.l10n.toolsTransWordbookDesc,
              child: Align(
                alignment: Alignment.centerLeft,
                child: SparkleButton(
                  label: context.l10n.toolsTransAddWordbook,
                  onPressed: _isAddingToWordbook ? null : _addToWordbook,
                  icon: const Icon(Icons.bookmark_add_rounded),
                  loading: _isAddingToWordbook,
                ),
              ),
            ),
          ],
        ],
      ),
      footer: LayoutBuilder(
        builder: (context, constraints) {
          final compact = constraints.maxWidth < 560;
          final copyButton = SparkleButton(
            label: context.l10n.toolsTransCopyResult,
            variant: ButtonVariant.ghost,
            onPressed: _output.isEmpty ? null : _copyToClipboard,
            icon: const Icon(Icons.copy_rounded),
            expand: true,
          );
          final translateButton = SparkleButton(
            label: _isLoading ? context.l10n.toolsTransTranslating : context.l10n.toolsTransStart,
            onPressed: _isLoading ? null : _translate,
            icon: const Icon(Icons.auto_fix_high_rounded),
            loading: _isLoading,
            expand: true,
          );

          if (compact) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                copyButton,
                const SizedBox(height: DS.spacing12),
                translateButton,
              ],
            );
          }

          return Row(
            children: [
              Expanded(child: copyButton),
              const SizedBox(width: DS.spacing12),
              Expanded(child: translateButton),
            ],
          );
        },
      ),
    );
  }
}

class _LanguageDropdown extends StatelessWidget {
  const _LanguageDropdown({
    required this.value,
    required this.items,
    required this.onChanged,
  });

  final Language value;
  final List<Language> items;
  final ValueChanged<Language> onChanged;

  @override
  Widget build(BuildContext context) => DecoratedBox(
        decoration: BoxDecoration(
          color: DS.surfacePrimary,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: DS.spacing12),
          child: DropdownButtonHideUnderline(
            child: DropdownButton<Language>(
              isDense: true,
              isExpanded: true,
              value: value,
              items: items
                  .map(
                    (language) => DropdownMenuItem<Language>(
                      value: language,
                      child: Text(
                        language.toString(),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  )
                  .toList(),
              onChanged: (language) {
                if (language != null) {
                  onChanged(language);
                }
              },
            ),
          ),
        ),
      );
}
