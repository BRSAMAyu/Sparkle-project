import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/presentation/widgets/common/sparkle_avatar.dart';

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
    required this.onAvatarSelected, super.key,
    this.currentAvatarUrl,
  });
  final String? currentAvatarUrl;
  final Function(String) onAvatarSelected;

  static const List<AvatarOption> presets = [
    AvatarOption(
      id: 'geek',
      url: 'https://api.dicebear.com/9.x/bottts/svg?seed=geek&backgroundColor=b6e3f4',
      label: '极客',
    ),
    AvatarOption(
      id: 'artist',
      url: 'https://api.dicebear.com/9.x/avataaars/svg?seed=artist&backgroundColor=ffdfbf',
      label: '艺术家',
    ),
    AvatarOption(
      id: 'explorer',
      url: 'https://api.dicebear.com/9.x/avataaars-neutral/svg?seed=explorer&backgroundColor=c0aede',
      label: '探险家',
    ),
    AvatarOption(
      id: 'scholar',
      url: 'https://api.dicebear.com/9.x/avataaars-neutral/svg?seed=scholar&backgroundColor=d1d4f9',
      label: '学者',
    ),
    AvatarOption(
      id: 'energy',
      url: 'https://api.dicebear.com/9.x/big-smile/svg?seed=energy&backgroundColor=ffd5dc',
      label: '元气',
    ),
    AvatarOption(
      id: 'pet',
      url: 'https://api.dicebear.com/9.x/adventurer/svg?seed=pet&backgroundColor=ffdfbf',
      label: '萌友',
    ),
  ];

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return AlertDialog(
      title: const Text('选择系统头像'),
      shape: RoundedRectangleBorder(borderRadius: AppDesignTokens.borderRadius16),
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
                Navigator.pop(context);
              },
              child: Column(
                children: [
                  Expanded(
                    child: DecoratedBox(
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        border: Border.all(
                          color: isSelected ? AppDesignTokens.primaryBase : Colors.transparent,
                          width: 3,
                        ),
                        boxShadow: isSelected
                            ? [
                                BoxShadow(
                                  color: AppDesignTokens.primaryBase.withValues(alpha: 0.3),
                                  blurRadius: 8,
                                ),
                              ]
                            : null,
                      ),
                      child: SparkleAvatar(
                        radius: 30,
                        backgroundColor: isDark ? DS.brandPrimary.shade800 : DS.brandPrimary.shade100,
                        url: option.url,
                      ),
                    ),
                  ),
                  const SizedBox(height: DS.xs),
                  Text(
                    option.label,
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                      color: isSelected ? AppDesignTokens.primaryBase : null,
                    ),
                  ),
                ],
              ),
            );
          },
        ),
      ),
      actions: [
        SparkleButton.ghost(label: '取消', onPressed: () => Navigator.pop(context)),
      ],
    );
  }
}
