import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sparkle_avatar.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

enum AvatarCollection {
  all,
  persona,
  playful,
  abstract,
  calm,
}

class AvatarOption {
  const AvatarOption({
    required this.id,
    required this.url,
    required this.label,
    required this.collection,
    required this.accent,
  });
  final String id;
  final String url;
  final String label;
  final AvatarCollection collection;
  final Color accent;
}

class AvatarSelectionDialog extends StatefulWidget {
  const AvatarSelectionDialog({
    required this.onAvatarSelected,
    super.key,
    this.currentAvatarUrl,
    this.closeOnSelect = true,
  });
  final String? currentAvatarUrl;
  final ValueChanged<String> onAvatarSelected;
  final bool closeOnSelect;

  static const List<AvatarOption> presets = [
    AvatarOption(
      id: 'geek',
      url:
          'https://api.dicebear.com/9.x/bottts/svg?seed=geek&backgroundColor=b6e3f4',
      label: 'geek',
      collection: AvatarCollection.persona,
      accent: Color(0xFF64B5F6),
    ),
    AvatarOption(
      id: 'artist',
      url:
          'https://api.dicebear.com/9.x/avataaars/svg?seed=artist&backgroundColor=ffdfbf',
      label: 'artist',
      collection: AvatarCollection.persona,
      accent: Color(0xFFFFB74D),
    ),
    AvatarOption(
      id: 'explorer',
      url:
          'https://api.dicebear.com/9.x/avataaars-neutral/svg?seed=explorer&backgroundColor=c0aede',
      label: 'explorer',
      collection: AvatarCollection.persona,
      accent: Color(0xFF9575CD),
    ),
    AvatarOption(
      id: 'scholar',
      url:
          'https://api.dicebear.com/9.x/avataaars-neutral/svg?seed=scholar&backgroundColor=d1d4f9',
      label: 'scholar',
      collection: AvatarCollection.persona,
      accent: Color(0xFF7986CB),
    ),
    AvatarOption(
      id: 'energy',
      url:
          'https://api.dicebear.com/9.x/big-smile/svg?seed=energy&backgroundColor=ffd5dc',
      label: 'energy',
      collection: AvatarCollection.playful,
      accent: Color(0xFFF06292),
    ),
    AvatarOption(
      id: 'pet',
      url:
          'https://api.dicebear.com/9.x/adventurer/svg?seed=pet&backgroundColor=ffdfbf',
      label: 'pet',
      collection: AvatarCollection.playful,
      accent: Color(0xFFFF8A65),
    ),
    AvatarOption(
      id: 'captain',
      url:
          'https://api.dicebear.com/9.x/adventurer-neutral/svg?seed=captain&backgroundColor=b6e3f4',
      label: 'captain',
      collection: AvatarCollection.persona,
      accent: Color(0xFF4FC3F7),
    ),
    AvatarOption(
      id: 'nova',
      url:
          'https://api.dicebear.com/9.x/lorelei/svg?seed=nova&backgroundColor=d1d4f9',
      label: 'nova',
      collection: AvatarCollection.calm,
      accent: Color(0xFF7E57C2),
    ),
    AvatarOption(
      id: 'pixel',
      url:
          'https://api.dicebear.com/9.x/pixel-art/svg?seed=pixel&backgroundColor=c0aede',
      label: 'pixel',
      collection: AvatarCollection.abstract,
      accent: Color(0xFF5C6BC0),
    ),
    AvatarOption(
      id: 'orbit',
      url:
          'https://api.dicebear.com/9.x/identicon/svg?seed=orbit&backgroundColor=b6e3f4',
      label: 'orbit',
      collection: AvatarCollection.abstract,
      accent: Color(0xFF26C6DA),
    ),
    AvatarOption(
      id: 'aurora',
      url:
          'https://api.dicebear.com/9.x/shapes/svg?seed=aurora&backgroundColor=d1d4f9',
      label: 'aurora',
      collection: AvatarCollection.abstract,
      accent: Color(0xFFAB47BC),
    ),
    AvatarOption(
      id: 'fox',
      url:
          'https://api.dicebear.com/9.x/bottts-neutral/svg?seed=fox&backgroundColor=ffdfbf',
      label: 'fox',
      collection: AvatarCollection.playful,
      accent: Color(0xFFFFA726),
    ),
    AvatarOption(
      id: 'breeze',
      url:
          'https://api.dicebear.com/9.x/micah/svg?seed=breeze&backgroundColor=b6e3f4',
      label: 'breeze',
      collection: AvatarCollection.calm,
      accent: Color(0xFF4DD0E1),
    ),
    AvatarOption(
      id: 'muse',
      url:
          'https://api.dicebear.com/9.x/notionists/svg?seed=muse&backgroundColor=ffd5dc',
      label: 'muse',
      collection: AvatarCollection.playful,
      accent: Color(0xFFEC407A),
    ),
    AvatarOption(
      id: 'ember',
      url:
          'https://api.dicebear.com/9.x/croodles/svg?seed=ember&backgroundColor=ffdfbf',
      label: 'ember',
      collection: AvatarCollection.playful,
      accent: Color(0xFFFF7043),
    ),
    AvatarOption(
      id: 'serene',
      url:
          'https://api.dicebear.com/9.x/miniavs/svg?seed=serene&backgroundColor=d1d4f9',
      label: 'serene',
      collection: AvatarCollection.calm,
      accent: Color(0xFF5E92F3),
    ),
  ];

  @override
  State<AvatarSelectionDialog> createState() => _AvatarSelectionDialogState();
}

class _AvatarSelectionDialogState extends State<AvatarSelectionDialog> {
  late AvatarCollection _activeCollection;
  late String _previewUrl;

  @override
  void initState() {
    super.initState();
    _activeCollection = AvatarCollection.all;
    _previewUrl =
        widget.currentAvatarUrl ?? AvatarSelectionDialog.presets.first.url;
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final visibleOptions = _visibleOptions;
    final highlighted = _findByUrl(_previewUrl) ?? visibleOptions.first;

    return AlertDialog(
      titlePadding: const EdgeInsets.fromLTRB(24, 24, 24, 12),
      contentPadding: const EdgeInsets.fromLTRB(20, 0, 20, 8),
      title: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(context.l10n.avatarSelectTitle),
          const SizedBox(height: DS.spacing6),
          Text(
            '挑一个更贴近你气质的形象，默认就能直接应用。',
            style: DS.bodySmall.copyWith(color: DS.textSecondary),
          ),
        ],
      ),
      shape: const RoundedRectangleBorder(borderRadius: DS.borderRadius16),
      content: SizedBox(
        width: 520,
        child: LayoutBuilder(
          builder: (context, constraints) {
            final crossAxisCount = constraints.maxWidth > 460 ? 4 : 3;
            return SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  AnimatedContainer(
                    duration: DS.normal,
                    curve: DS.motionCurve(SparkleMotionToken.standard),
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      borderRadius: DS.borderRadius16,
                      border: Border.all(
                        color: highlighted.accent.withValues(
                          alpha: isDark ? 0.44 : 0.26,
                        ),
                      ),
                      gradient: LinearGradient(
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                        colors: [
                          Color.alphaBlend(
                            highlighted.accent.withValues(
                              alpha: isDark ? 0.18 : 0.1,
                            ),
                            DS.surfaceSecondary,
                          ),
                          DS.surfacePrimaryElevated,
                        ],
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: highlighted.accent.withValues(
                            alpha: isDark ? 0.18 : 0.12,
                          ),
                          blurRadius: 24,
                          offset: const Offset(0, 12),
                        ),
                      ],
                    ),
                    child: Row(
                      children: [
                        DecoratedBox(
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            boxShadow: [
                              BoxShadow(
                                color: highlighted.accent.withValues(
                                  alpha: isDark ? 0.28 : 0.18,
                                ),
                                blurRadius: 18,
                                offset: const Offset(0, 8),
                              ),
                            ],
                          ),
                          child: SparkleAvatar(
                            radius: 32,
                            backgroundColor: Color.alphaBlend(
                              highlighted.accent.withValues(alpha: 0.16),
                              DS.avatarFallbackBackground,
                            ),
                            url: _previewUrl,
                          ),
                        ),
                        const SizedBox(width: DS.spacing16),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                _localizedLabel(context, highlighted.label),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: DS.titleLarge.copyWith(
                                  color: DS.textPrimary,
                                  fontWeight: DS.fontWeightBold,
                                ),
                              ),
                              const SizedBox(height: DS.spacing4),
                              Text(
                                _collectionDescription(_activeCollection),
                                style: DS.bodySmall.copyWith(
                                  color: DS.textSecondary,
                                  height: 1.35,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: DS.spacing16),
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Row(
                      children: AvatarCollection.values.map((collection) {
                        final selected = collection == _activeCollection;
                        return Padding(
                          padding: const EdgeInsets.only(right: 8),
                          child: ChoiceChip(
                            selected: selected,
                            label: Text(_collectionLabel(collection)),
                            onSelected: (_) {
                              setState(() {
                                _activeCollection = collection;
                              });
                            },
                          ),
                        );
                      }).toList(),
                    ),
                  ),
                  const SizedBox(height: DS.spacing16),
                  GridView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: crossAxisCount,
                      crossAxisSpacing: 12,
                      mainAxisSpacing: 12,
                      childAspectRatio: 0.82,
                    ),
                    itemCount: visibleOptions.length,
                    itemBuilder: (context, index) {
                      final option = visibleOptions[index];
                      final isSelected = widget.currentAvatarUrl == option.url;
                      final isPreview = _previewUrl == option.url;

                      return InkWell(
                        borderRadius: DS.borderRadius16,
                        onTap: () {
                          setState(() {
                            _previewUrl = option.url;
                          });
                          widget.onAvatarSelected(option.url);
                          if (widget.closeOnSelect) {
                            Navigator.pop(context, option.url);
                          }
                        },
                        child: AnimatedContainer(
                          duration: DS.normal,
                          curve: DS.motionCurve(SparkleMotionToken.standard),
                          padding: const EdgeInsets.symmetric(
                            horizontal: 10,
                            vertical: 12,
                          ),
                          decoration: BoxDecoration(
                            borderRadius: DS.borderRadius16,
                            border: Border.all(
                              color: (isSelected || isPreview)
                                  ? option.accent.withValues(
                                      alpha: isDark ? 0.58 : 0.34,
                                    )
                                  : DS.borderSubtle,
                            ),
                            gradient: LinearGradient(
                              begin: Alignment.topLeft,
                              end: Alignment.bottomRight,
                              colors: [
                                Color.alphaBlend(
                                  option.accent.withValues(
                                    alpha: isPreview
                                        ? (isDark ? 0.14 : 0.08)
                                        : (isDark ? 0.08 : 0.04),
                                  ),
                                  DS.surfaceSecondary,
                                ),
                                DS.surfacePrimaryElevated,
                              ],
                            ),
                            boxShadow: isPreview
                                ? [
                                    BoxShadow(
                                      color: option.accent.withValues(
                                        alpha: isDark ? 0.18 : 0.1,
                                      ),
                                      blurRadius: 18,
                                      offset: const Offset(0, 10),
                                    ),
                                  ]
                                : null,
                          ),
                          child: Column(
                            children: [
                              Expanded(
                                child: Center(
                                  child: DecoratedBox(
                                    decoration: BoxDecoration(
                                      shape: BoxShape.circle,
                                      border: Border.all(
                                        color: option.accent.withValues(
                                          alpha: isSelected || isPreview
                                              ? 0.52
                                              : 0.2,
                                        ),
                                        width:
                                            isSelected || isPreview ? 2.4 : 1.2,
                                      ),
                                    ),
                                    child: Padding(
                                      padding: const EdgeInsets.all(3),
                                      child: SparkleAvatar(
                                        radius: 28,
                                        backgroundColor: Color.alphaBlend(
                                          option.accent.withValues(alpha: 0.14),
                                          DS.avatarFallbackBackground,
                                        ),
                                        url: option.url,
                                      ),
                                    ),
                                  ),
                                ),
                              ),
                              const SizedBox(height: DS.spacing8),
                              Text(
                                _localizedLabel(context, option.label),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: DS.bodySmall.copyWith(
                                  fontWeight: isSelected || isPreview
                                      ? DS.fontWeightBold
                                      : DS.fontWeightMedium,
                                  color: isSelected || isPreview
                                      ? option.accent
                                      : DS.textPrimary,
                                ),
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ],
              ),
            );
          },
        ),
      ),
      actions: [
        SparkleButton.ghost(
          label: context.l10n.cancel,
          onPressed: () => Navigator.pop(context),
        ),
      ],
    );
  }

  List<AvatarOption> get _visibleOptions {
    if (_activeCollection == AvatarCollection.all) {
      return AvatarSelectionDialog.presets;
    }
    return AvatarSelectionDialog.presets
        .where((option) => option.collection == _activeCollection)
        .toList();
  }

  AvatarOption? _findByUrl(String url) {
    for (final option in AvatarSelectionDialog.presets) {
      if (option.url == url) {
        return option;
      }
    }
    return null;
  }

  String _collectionLabel(AvatarCollection collection) => switch (collection) {
        AvatarCollection.all => '全部',
        AvatarCollection.persona => '人物感',
        AvatarCollection.playful => '活泼感',
        AvatarCollection.abstract => '抽象感',
        AvatarCollection.calm => '安静感',
      };

  String _collectionDescription(AvatarCollection collection) =>
      switch (collection) {
        AvatarCollection.all => '从人物、抽象到轻松风格里挑一个更像你的头像。',
        AvatarCollection.persona => '更像角色形象，适合想保留个性辨识度的主页氛围。',
        AvatarCollection.playful => '更轻松、更有情绪张力，适合希望主页更灵动的人。',
        AvatarCollection.abstract => '更干净、图形化，适合偏系统感和科技感的风格。',
        AvatarCollection.calm => '更柔和克制，适合长时间陪伴型的个人空间。',
      };

  String _localizedLabel(BuildContext context, String id) {
    switch (id) {
      case 'geek':
        return context.l10n.avatarPresetGeek;
      case 'artist':
        return context.l10n.avatarPresetArtist;
      case 'explorer':
        return context.l10n.avatarPresetExplorer;
      case 'scholar':
        return context.l10n.avatarPresetScholar;
      case 'energy':
        return context.l10n.avatarPresetEnergy;
      case 'pet':
        return context.l10n.avatarPresetPet;
      default:
        return id
            .split('_')
            .map(
              (part) => part.isEmpty
                  ? part
                  : '${part[0].toUpperCase()}${part.substring(1)}',
            )
            .join(' ');
    }
  }
}
