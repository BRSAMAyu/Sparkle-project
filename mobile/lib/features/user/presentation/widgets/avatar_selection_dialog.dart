import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sparkle_avatar.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

class AvatarOption {
  const AvatarOption({
    required this.id,
    required this.url,
    required this.label,
  });
  final String id;
  final String url;
  final String label;
}

class AvatarSelectionDialog extends StatelessWidget {
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
    ),
    AvatarOption(
      id: 'artist',
      url:
          'https://api.dicebear.com/9.x/avataaars/svg?seed=artist&backgroundColor=ffdfbf',
      label: 'artist',
    ),
    AvatarOption(
      id: 'explorer',
      url:
          'https://api.dicebear.com/9.x/avataaars-neutral/svg?seed=explorer&backgroundColor=c0aede',
      label: 'explorer',
    ),
    AvatarOption(
      id: 'scholar',
      url:
          'https://api.dicebear.com/9.x/avataaars-neutral/svg?seed=scholar&backgroundColor=d1d4f9',
      label: 'scholar',
    ),
    AvatarOption(
      id: 'energy',
      url:
          'https://api.dicebear.com/9.x/big-smile/svg?seed=energy&backgroundColor=ffd5dc',
      label: 'energy',
    ),
    AvatarOption(
      id: 'pet',
      url:
          'https://api.dicebear.com/9.x/adventurer/svg?seed=pet&backgroundColor=ffdfbf',
      label: 'pet',
    ),
  ];

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return AlertDialog(
      title: Text(context.l10n.avatarSelectTitle),
      shape: const RoundedRectangleBorder(borderRadius: DS.borderRadius16),
      content: SizedBox(
        width: double.maxFinite,
        child: GridView.builder(
          shrinkWrap: true,
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 3,
            crossAxisSpacing: 12,
            mainAxisSpacing: 12,
            childAspectRatio: 0.8,
          ),
          itemCount: presets.length,
          itemBuilder: (context, index) {
            final option = presets[index];
            final isSelected = currentAvatarUrl == option.url;

            return GestureDetector(
              onTap: () {
                onAvatarSelected(option.url);
                if (closeOnSelect) {
                  Navigator.pop(context, option.url);
                }
              },
              child: Column(
                children: [
                  Expanded(
                    child: DecoratedBox(
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        border: Border.all(
                          color:
                              isSelected ? DS.primaryBase : Colors.transparent,
                          width: 3,
                        ),
                        boxShadow: isSelected
                            ? [
                                BoxShadow(
                                  color: DS.primaryBase.withValues(alpha: 0.3),
                                  blurRadius: 8,
                                ),
                              ]
                            : null,
                      ),
                      child: SparkleAvatar(
                        radius: 30,
                        backgroundColor: isDark
                            ? DS.brandPrimary.shade800
                            : DS.brandPrimary.shade100,
                        url: option.url,
                      ),
                    ),
                  ),
                  const SizedBox(height: DS.xs),
                  Text(
                    _localizedLabel(context, option.label),
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight:
                          isSelected ? FontWeight.bold : FontWeight.normal,
                      color: isSelected ? DS.primaryBase : null,
                    ),
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
        return id;
    }
  }
}
