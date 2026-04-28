import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

class AttachmentPickerSheet extends StatelessWidget {
  const AttachmentPickerSheet({
    required this.onDirectUpload,
    required this.onDocumentClean,
    super.key,
    this.title,
    this.primaryTitle,
    this.primarySubtitle,
  });

  final VoidCallback onDirectUpload;
  final VoidCallback onDocumentClean;
  final String? title;
  final String? primaryTitle;
  final String? primarySubtitle;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return SafeArea(
      child: Container(
        margin: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              isDark ? DS.surfaceOverlay : DS.surfacePrimary,
              Color.alphaBlend(
                DS.info.withValues(alpha: 0.03),
                DS.surfacePrimary,
              ),
            ],
          ),
          borderRadius: BorderRadius.circular(28),
          border: Border.all(color: DS.borderSubtle),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: isDark ? 0.24 : 0.08),
              blurRadius: 24,
              offset: const Offset(0, 12),
            ),
          ],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const SizedBox(height: DS.spacing12),
            Center(
              child: Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: DS.borderStrong,
                  borderRadius: BorderRadius.circular(999),
                ),
              ),
            ),
            const SizedBox(height: DS.spacing16),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: DS.spacing20),
              child: Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  title ?? context.l10n.chatAttachTitle,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        color: DS.textPrimary,
                        fontWeight: DS.fontWeightBold,
                      ),
                ),
              ),
            ),
            const SizedBox(height: DS.spacing12),
            _AttachmentOption(
              icon: Icons.upload_file_rounded,
              iconColor: DS.brandPrimary,
              title: primaryTitle ?? context.l10n.chatAttachDirectUpload,
              subtitle: primarySubtitle ?? context.l10n.chatAttachUploadDesc,
              onTap: () {
                SensoryFeedbackService.emit(SensoryFeedbackEvent.selection);
                Navigator.pop(context);
                onDirectUpload();
              },
            ),
            _AttachmentOption(
              icon: Icons.auto_fix_high_rounded,
              iconColor: DS.prismPurple,
              title: context.l10n.chatAttachAiDocClean,
              subtitle: context.l10n.chatAttachAiDocCleanDesc,
              onTap: () {
                SensoryFeedbackService.emit(SensoryFeedbackEvent.selection);
                Navigator.pop(context);
                onDocumentClean();
              },
            ),
            const SizedBox(height: DS.spacing16),
          ],
        ),
      ),
    );
  }
}

class _AttachmentOption extends StatelessWidget {
  const _AttachmentOption({
    required this.icon,
    required this.iconColor,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  final IconData icon;
  final Color iconColor;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing12,
        vertical: DS.spacing4,
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(20),
          child: Container(
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing16,
              vertical: DS.spacing12,
            ),
            decoration: BoxDecoration(
              color: isDark
                  ? DS.surfacePrimary.withValues(alpha: 0.5)
                  : DS.surfaceSecondary,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: DS.borderSubtle),
            ),
            child: Row(
              children: [
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: iconColor.withValues(alpha: isDark ? 0.18 : 0.10),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                      color: iconColor.withValues(alpha: isDark ? 0.28 : 0.16),
                    ),
                  ),
                  child: Icon(icon, size: 22, color: iconColor),
                ),
                const SizedBox(width: DS.spacing12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style:
                            Theme.of(context).textTheme.titleSmall?.copyWith(
                                  color: DS.textPrimary,
                                  fontWeight: DS.fontWeightSemiBold,
                                ),
                      ),
                      const SizedBox(height: DS.spacing4),
                      Text(
                        subtitle,
                        style:
                            Theme.of(context).textTheme.bodySmall?.copyWith(
                                  color: DS.textSecondary,
                                  height: 1.3,
                                ),
                      ),
                    ],
                  ),
                ),
                Icon(
                  Icons.chevron_right_rounded,
                  color: DS.textSecondary,
                  size: 20,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
