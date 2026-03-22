import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sparkle_motion_primitives.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';

/// Privacy settings panel for share card customization
class SharePrivacySettings extends StatelessWidget {
  SharePrivacySettings({
    required this.settings,
    required this.onSettingsChanged,
    this.defaultDisplayName,
    super.key,
  });

  final ShareCardPrivacySettings settings;
  final ValueChanged<ShareCardPrivacySettings> onSettingsChanged;
  final String? defaultDisplayName;

  final TextEditingController _nameController = TextEditingController();

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;

    // Initialize controller with current display name
    _nameController.text = settings.displayName ?? '';

    return Container(
      padding: const EdgeInsets.all(DS.md),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: DS.borderRadius12,
        border: Border.all(color: DS.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          SparkleStaggerItem(
            index: 0,
            child: Row(
              children: [
                Icon(
                  Icons.privacy_tip_outlined,
                  size: 20,
                  color: DS.textSecondary,
                ),
                const SizedBox(width: DS.sm),
                Text(
                  l10n.sharePrivacyTitle,
                  style: TextStyle(
                    fontSize: DS.fontSizeBase,
                    fontWeight: DS.fontWeightSemiBold,
                    color: DS.textPrimary,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: DS.md),

          // Display Name Input
          SparkleStaggerItem(
            index: 1,
            child: _buildDisplayNameField(context, l10n),
          ),
          const SizedBox(height: DS.md),

          // Toggle Options
          SparkleStaggerItem(
            index: 2,
            child: _buildToggleOption(
              context: context,
              title: l10n.sharePrivacyShowAvatar,
              subtitle: l10n.sharePrivacyShowAvatarDesc,
              icon: Icons.account_circle_outlined,
              value: settings.showAvatar,
              onChanged: (value) => _updateSettings(showAvatar: value),
            ),
          ),
          const SizedBox(height: DS.sm),

          SparkleStaggerItem(
            index: 3,
            child: _buildToggleOption(
              context: context,
              title: l10n.sharePrivacyShowDate,
              subtitle: l10n.sharePrivacyShowDateDesc,
              icon: Icons.calendar_today_outlined,
              value: settings.showUnlockDate,
              onChanged: (value) => _updateSettings(showUnlockDate: value),
            ),
          ),
          const SizedBox(height: DS.sm),

          SparkleStaggerItem(
            index: 4,
            child: _buildToggleOption(
              context: context,
              title: l10n.sharePrivacyShowStats,
              subtitle: l10n.sharePrivacyShowStatsDesc,
              icon: Icons.bar_chart_outlined,
              value: settings.showProgressStats,
              onChanged: (value) => _updateSettings(showProgressStats: value),
            ),
          ),
          const SizedBox(height: DS.sm),

          SparkleStaggerItem(
            index: 5,
            child: _buildToggleOption(
              context: context,
              title: l10n.sharePrivacyShowFirstBadge,
              subtitle: l10n.sharePrivacyShowFirstBadgeDesc,
              icon: Icons.emoji_events_outlined,
              value: settings.showFirstUnlockerBadge,
              onChanged: (value) =>
                  _updateSettings(showFirstUnlockerBadge: value),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDisplayNameField(BuildContext context, AppLocalizations l10n) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          l10n.sharePrivacyDisplayName,
          style: TextStyle(
            fontSize: DS.fontSizeSm,
            fontWeight: DS.fontWeightMedium,
            color: DS.textSecondary,
          ),
        ),
        const SizedBox(height: DS.xs),
        TextField(
          controller: _nameController,
          decoration: InputDecoration(
            hintText: defaultDisplayName ?? l10n.sharePrivacyDisplayNameHint,
            hintStyle: TextStyle(
              color: DS.textTertiary,
              fontSize: DS.fontSizeSm,
            ),
            filled: true,
            fillColor: DS.surfacePrimary,
            border: OutlineInputBorder(
              borderRadius: DS.borderRadius8,
              borderSide: BorderSide(color: DS.border),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: DS.borderRadius8,
              borderSide: BorderSide(color: DS.border),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: DS.borderRadius8,
              borderSide: BorderSide(color: DS.brandPrimary, width: 2),
            ),
            contentPadding: const EdgeInsets.symmetric(
              horizontal: DS.md,
              vertical: DS.sm,
            ),
            suffixIcon: _nameController.text.isNotEmpty
                ? IconButton(
                    icon: Icon(Icons.clear, size: 18, color: DS.textTertiary),
                    onPressed: () {
                      SensoryFeedbackService.emit(
                        SensoryFeedbackEvent.selection,
                      );
                      _nameController.clear();
                      _updateSettings(displayName: null);
                    },
                  )
                : null,
          ),
          style: TextStyle(
            fontSize: DS.fontSizeSm,
            color: DS.textPrimary,
          ),
          onChanged: (value) {
            // Debounce the update to avoid too many rebuilds
            Future.delayed(const Duration(milliseconds: 300), () {
              if (_nameController.text == value) {
                _updateSettings(displayName: value.isEmpty ? null : value);
              }
            });
          },
        ),
        const SizedBox(height: DS.xs),
        Text(
          l10n.sharePrivacyDisplayNameNote,
          style: TextStyle(
            fontSize: DS.fontSizeXs,
            color: DS.textTertiary,
          ),
        ),
      ],
    );
  }

  Widget _buildToggleOption({
    required BuildContext context,
    required String title,
    required String subtitle,
    required IconData icon,
    required bool value,
    required ValueChanged<bool> onChanged,
  }) {
    return Container(
      padding: const EdgeInsets.all(DS.sm),
      decoration: BoxDecoration(
        color: DS.surfacePrimary,
        borderRadius: DS.borderRadius8,
      ),
      child: Row(
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: value
                  ? DS.brandPrimary.withValues(alpha: 0.1)
                  : DS.surfaceSecondary,
              borderRadius: DS.borderRadius8,
            ),
            child: Icon(
              icon,
              size: 20,
              color: value ? DS.brandPrimary : DS.textTertiary,
            ),
          ),
          const SizedBox(width: DS.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    fontSize: DS.fontSizeSm,
                    fontWeight: DS.fontWeightMedium,
                    color: DS.textPrimary,
                  ),
                ),
                Text(
                  subtitle,
                  style: TextStyle(
                    fontSize: DS.fontSizeXs,
                    color: DS.textTertiary,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
          Transform.scale(
            scale: 0.85,
            child: Switch(
              value: value,
              onChanged: (next) {
                SensoryFeedbackService.emit(
                  SensoryFeedbackEvent.selection,
                );
                onChanged(next);
              },
              activeTrackColor: DS.brandPrimary.withValues(alpha: 0.3),
            ),
          ),
        ],
      ),
    );
  }

  void _updateSettings({
    String? displayName,
    bool? showAvatar,
    bool? showUnlockDate,
    bool? showProgressStats,
    bool? showFirstUnlockerBadge,
  }) {
    onSettingsChanged(settings.copyWith(
      displayName: displayName,
      showAvatar: showAvatar,
      showUnlockDate: showUnlockDate,
      showProgressStats: showProgressStats,
      showFirstUnlockerBadge: showFirstUnlockerBadge,
    ));
  }
}
