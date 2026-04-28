import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/features/chat/data/models/chat_stream_events.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_state.dart';
import 'package:sparkle/features/chat/presentation/widgets/transparency_panel.dart';
import 'package:sparkle/features/settings/presentation/screens/transparency_settings_screen.dart';

class TransparencyFloatingCapsule extends StatelessWidget {
  const TransparencyFloatingCapsule({
    required this.preferences,
    required this.runPhase,
    required this.presentationState,
    super.key,
    this.status,
    this.details,
    this.promptTokens,
    this.completionTokens,
    this.totalTokens,
    this.currentAgentName,
    this.activeAgentType,
    this.activeTools = const [],
    this.dailyTokens,
    this.dailyTokenLimit,
    this.dailyCostMicroUsd,
    this.transparencyData,
    this.runLedgerSummary,
    this.currentStepIndex,
    this.onDismiss,
    this.onExpandedChanged,
  });

  final TransparencyPreferences preferences;
  final ChatRunPhase runPhase;
  final TransparencyPresentationState presentationState;
  final String? status;
  final String? details;
  final int? promptTokens;
  final int? completionTokens;
  final int? totalTokens;
  final String? currentAgentName;
  final String? activeAgentType;
  final List<String> activeTools;
  final int? dailyTokens;
  final int? dailyTokenLimit;
  final int? dailyCostMicroUsd;
  final TransparencyData? transparencyData;
  final RunLedgerSummary? runLedgerSummary;
  final int? currentStepIndex;
  final VoidCallback? onDismiss;
  final ValueChanged<bool>? onExpandedChanged;

  @override
  Widget build(BuildContext context) {
    if (!preferences.enabled ||
        preferences.displayMode == TransparencyDisplayMode.detailOnly ||
        presentationState.isDismissed) {
      return const SizedBox.shrink();
    }

    final hasLiveData = status != null ||
        details != null ||
        runLedgerSummary != null ||
        transparencyData != null ||
        activeTools.isNotEmpty;
    final summaryLabel = _summaryLabel;
    if (!hasLiveData && (summaryLabel == null || summaryLabel.isEmpty)) {
      return const SizedBox.shrink();
    }

    final tone = _toneColor;
    final secondaryText = Theme.of(context).brightness == Brightness.dark
        ? DS.neutral300
        : DS.neutral700;
    final stepCount = transparencyData?.steps.length ?? 0;
    final stepLabel = stepCount > 0 && currentStepIndex != null
        ? '${currentStepIndex! + 1}/$stepCount'
        : null;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: DS.spacing12),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: DS.surfacePrimaryElevated,
          borderRadius: DS.borderRadius20,
          boxShadow: DS.shadowSm,
          border: Border.all(color: tone.withValues(alpha: 0.14)),
        ),
        child: InkWell(
          borderRadius: DS.borderRadius20,
          onTap: () async {
            onExpandedChanged?.call(true);
            await showSensoryModalBottomSheet<void>(
              context: context,
              isScrollControlled: true,
              backgroundColor: Colors.transparent,
              builder: (context) => SafeArea(
                child: Padding(
                  padding: const EdgeInsets.all(DS.spacing12),
                  child: Material(
                    color: DS.surfacePrimary,
                    borderRadius: DS.borderRadius20,
                    clipBehavior: Clip.antiAlias,
                    child: SingleChildScrollView(
                      child: Padding(
                        padding: const EdgeInsets.only(top: DS.spacing12),
                        child: TransparencyPanel(
                          status: status,
                          details: details,
                          promptTokens: promptTokens,
                          completionTokens: completionTokens,
                          totalTokens: totalTokens,
                          currentAgentName: currentAgentName,
                          activeAgentType: activeAgentType,
                          activeTools: activeTools,
                          dailyTokens: dailyTokens,
                          dailyTokenLimit: dailyTokenLimit,
                          dailyCostMicroUsd: dailyCostMicroUsd,
                          transparencyData: transparencyData,
                          runLedgerSummary: runLedgerSummary,
                          currentStepIndex: currentStepIndex,
                          showTokenUsageDetails: preferences.showTokenUsage,
                          showAgentCollaboration:
                              preferences.showAgentSwitching,
                          showReasoningTimeline: preferences.showReasoningSteps,
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            );
            onExpandedChanged?.call(false);
          },
          child: Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing12,
              vertical: DS.spacing10,
            ),
            child: Row(
              children: [
                Container(
                  width: 10,
                  height: 10,
                  decoration: BoxDecoration(
                    color: tone,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: DS.spacing10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        summaryLabel ?? 'Sparkle AI',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          color: DS.textPrimary,
                          fontWeight: DS.fontWeightSemibold,
                        ),
                      ),
                      if ((details ?? '').trim().isNotEmpty ||
                          (currentAgentName ?? '').trim().isNotEmpty ||
                          stepLabel != null)
                        Padding(
                          padding: const EdgeInsets.only(top: 2),
                          child: Text(
                            [
                              if ((details ?? '').trim().isNotEmpty) details!,
                              if ((currentAgentName ?? '').trim().isNotEmpty)
                                currentAgentName!,
                              if (stepLabel != null) context.l10n.chatTransparencyStep(stepLabel),
                              if (activeTools.isNotEmpty)
                                '${activeTools.length} tools',
                            ].join(' · '),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              color: secondaryText,
                              fontSize: DS.fontSizeXs,
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
                if (preferences.allowPerTurnDismiss && onDismiss != null)
                  IconButton(
                    onPressed: onDismiss,
                    icon: Icon(
                      Icons.close_rounded,
                      size: DS.iconSizeSm,
                      color: secondaryText,
                    ),
                    splashRadius: DS.touchTargetMinSize / 2,
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  String? get _summaryLabel {
    if (runPhase == ChatRunPhase.completed &&
        preferences.autoCollapseOnComplete &&
        presentationState.lastCompletedLabel != null) {
      return presentationState.lastCompletedLabel;
    }
    if ((status ?? '').trim().isNotEmpty) {
      return status;
    }
    return null;
  }

  Color get _toneColor {
    switch ((status ?? '').toUpperCase()) {
      case 'THINKING':
        return DS.primaryBase;
      case 'GENERATING':
        return DS.info;
      case 'EXECUTING_TOOL':
        return DS.warning;
      default:
        if (runPhase == ChatRunPhase.completed) {
          return DS.success;
        }
        if (runPhase == ChatRunPhase.failed) {
          return DS.error;
        }
        return DS.brandPrimary;
    }
  }
}
