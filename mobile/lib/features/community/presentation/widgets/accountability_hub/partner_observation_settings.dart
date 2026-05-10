import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

/// COM-005: Permanent observation preferences for an established buddy.
///
/// Whereas PartnerObservationControl handles per-reminder accept/decline,
/// this widget controls long-lived permissions: whether the buddy can see my
/// activity at all, and which categories (study time / specific tasks /
/// emotional state). All toggles emit [onChanged] so the host screen can
/// persist via the user_settings API.
class PartnerObservationSettings extends StatelessWidget {
  const PartnerObservationSettings({
    required this.partnerName,
    required this.observationEnabled,
    required this.shareStudyTime,
    required this.shareTaskDetails,
    required this.shareEmotionalState,
    required this.onChanged,
    super.key,
  });

  final String partnerName;
  final bool observationEnabled;
  final bool shareStudyTime;
  final bool shareTaskDetails;
  final bool shareEmotionalState;
  final void Function({
    bool? enabled,
    bool? studyTime,
    bool? taskDetails,
    bool? emotion,
  }) onChanged;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: DS.surfaceHigh,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: DS.brandPrimary.withValues(alpha: 0.16)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              Icon(Icons.visibility_outlined,
                  size: 18, color: DS.brandPrimary),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  l10n.communityPartnerObservationPermissions(partnerName),
                  style: TextStyle(
                    color: DS.textPrimary,
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          SwitchListTile.adaptive(
            contentPadding: EdgeInsets.zero,
            dense: true,
            title: Text(
              l10n.communityAllowObservation,
              style: TextStyle(color: DS.textPrimary, fontSize: 13),
            ),
            subtitle: Text(
              l10n.communityAllowObservationDesc,
              style: TextStyle(color: DS.textSecondary, fontSize: 11),
            ),
            value: observationEnabled,
            onChanged: (value) => onChanged(enabled: value),
          ),
          if (observationEnabled) ...[
            const Divider(height: 12),
            CheckboxListTile.adaptive(
              contentPadding: EdgeInsets.zero,
              dense: true,
              controlAffinity: ListTileControlAffinity.leading,
              title: Text(
                l10n.communitySeeStudyTime,
                style: TextStyle(color: DS.textPrimary, fontSize: 12),
              ),
              value: shareStudyTime,
              onChanged: (value) => onChanged(studyTime: value ?? false),
            ),
            CheckboxListTile.adaptive(
              contentPadding: EdgeInsets.zero,
              dense: true,
              controlAffinity: ListTileControlAffinity.leading,
              title: Text(
                l10n.communitySeeTaskContent,
                style: TextStyle(color: DS.textPrimary, fontSize: 12),
              ),
              value: shareTaskDetails,
              onChanged: (value) => onChanged(taskDetails: value ?? false),
            ),
            CheckboxListTile.adaptive(
              contentPadding: EdgeInsets.zero,
              dense: true,
              controlAffinity: ListTileControlAffinity.leading,
              title: Text(
                l10n.communitySeeEmotionState,
                style: TextStyle(color: DS.textPrimary, fontSize: 12),
              ),
              value: shareEmotionalState,
              onChanged: (value) => onChanged(emotion: value ?? false),
            ),
          ],
        ],
      ),
    );
  }
}
