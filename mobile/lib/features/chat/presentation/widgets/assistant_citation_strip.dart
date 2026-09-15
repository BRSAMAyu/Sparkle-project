import 'dart:async';
import 'dart:collection';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/deep_link_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_accessory_pill.dart';

class AssistantCitationStrip extends StatefulWidget {
  const AssistantCitationStrip({
    required this.message,
    super.key,
    this.onCitationFeedback,
  });

  final ChatMessageModel message;
  final FutureOr<void> Function(ChatCitation citation, bool helpful)?
      onCitationFeedback;

  @override
  State<AssistantCitationStrip> createState() => _AssistantCitationStripState();
}

class _AssistantCitationStripState extends State<AssistantCitationStrip> {
  static const int _maxStoredSelections = 200;
  static final LinkedHashMap<String, String> _feedbackSelections =
      LinkedHashMap<String, String>();

  List<ChatCitation> get _citations => widget.message.citations;

  @override
  Widget build(BuildContext context) {
    if (_citations.isEmpty) {
      return const SizedBox.shrink();
    }

    return Padding(
      padding: const EdgeInsets.only(
        top: DS.spacing8,
        left: DS.spacing8,
        right: DS.spacing8,
      ),
      child: Wrap(
        spacing: DS.spacing8,
        runSpacing: DS.spacing8,
        children: _citations
            .map(
              (citation) => ChatAccessoryPill(
                icon: Icons.description_outlined,
                label: citation.chipLabel,
                trailing: Icon(
                  Icons.arrow_outward_rounded,
                  size: 12,
                  color: DS.textSecondary,
                ),
                onTap: () => _showCitationSheet(citation),
                emphasize: true,
                accentColor: DS.primaryBase,
              ),
            )
            .toList(growable: false),
      ),
    );
  }

  String _selectionKey(ChatCitation citation) {
    final responseId = widget.message.responseId ?? widget.message.id;
    return '$responseId::${citation.feedbackKey}';
  }

  String? _selectionFor(ChatCitation citation) =>
      _feedbackSelections[_selectionKey(citation)];

  void _rememberSelection(ChatCitation citation, String selection) {
    final key = _selectionKey(citation);
    _feedbackSelections.remove(key);
    _feedbackSelections[key] = selection;
    if (_feedbackSelections.length > _maxStoredSelections) {
      _feedbackSelections.remove(_feedbackSelections.keys.first);
    }
  }

  Future<void> _showCitationSheet(ChatCitation citation) async {
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.sheetOpen));
    await showSensoryModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) {
        final excerpt = citation.excerptText;
        final selection = _selectionFor(citation);
        final isPositive = selection == 'up';
        final isNegative = selection == 'down';
        final documentRoute = _resolveDocumentRoute(citation);

        return SafeArea(
          top: false,
          child: Container(
            decoration: BoxDecoration(
              color: DS.surfacePrimary,
              borderRadius: const BorderRadius.vertical(
                top: Radius.circular(24),
              ),
            ),
            padding: const EdgeInsets.fromLTRB(
              DS.spacing20,
              DS.spacing16,
              DS.spacing20,
              DS.spacing20,
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Center(
                  child: Container(
                    width: 44,
                    height: 4,
                    decoration: BoxDecoration(
                      color: DS.borderSubtle,
                      borderRadius: DS.borderRadiusFull,
                    ),
                  ),
                ),
                const SizedBox(height: DS.spacing16),
                Text(
                  citation.chipTitle,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        color: DS.textPrimary,
                        fontWeight: DS.fontWeightSemibold,
                      ),
                ),
                if (citation.locatorLabel.isNotEmpty) ...[
                  const SizedBox(height: DS.spacing6),
                  Text(
                    citation.locatorLabel,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: DS.textSecondary,
                        ),
                  ),
                ],
                const SizedBox(height: DS.spacing16),
                Container(
                  width: double.infinity,
                  constraints: const BoxConstraints(maxHeight: 280),
                  padding: const EdgeInsets.all(DS.spacing16),
                  decoration: BoxDecoration(
                    color: DS.surfaceSecondary,
                    borderRadius: DS.borderRadius16,
                    border: Border.all(color: DS.borderSubtle),
                  ),
                  child: SingleChildScrollView(
                    child: Text(
                      excerpt.isNotEmpty
                          ? excerpt
                          : context.l10n.chatCitationExcerptUnavailable,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: excerpt.isNotEmpty
                                ? DS.textPrimary
                                : DS.textSecondary,
                            height: 1.6,
                          ),
                    ),
                  ),
                ),
                const SizedBox(height: DS.spacing16),
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton.icon(
                    onPressed: documentRoute == null
                        ? null
                        : () => _openDocument(documentRoute),
                    icon: const Icon(Icons.open_in_new_rounded),
                    label: Text(context.l10n.chatCitationOpenDocument),
                  ),
                ),
                const SizedBox(height: DS.spacing12),
                Text(
                  context.l10n.chatCitationHelpfulPrompt,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: DS.textSecondary,
                      ),
                ),
                const SizedBox(height: DS.spacing10),
                Wrap(
                  spacing: DS.spacing8,
                  runSpacing: DS.spacing8,
                  children: [
                    ChatAccessoryPill(
                      icon: Icons.thumb_up_alt_rounded,
                      label: context.l10n.chatHelpful,
                      selected: isPositive,
                      onTap: selection == null
                          ? () =>
                              _submitCitationFeedback(citation, helpful: true)
                          : null,
                    ),
                    ChatAccessoryPill(
                      icon: Icons.thumb_down_alt_rounded,
                      label: context.l10n.chatNotHelpful,
                      selected: isNegative,
                      onTap: selection == null
                          ? () =>
                              _submitCitationFeedback(citation, helpful: false)
                          : null,
                    ),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Future<void> _submitCitationFeedback(
    ChatCitation citation, {
    required bool helpful,
  }) async {
    final nextSelection = helpful ? 'up' : 'down';
    setState(() {
      _rememberSelection(citation, nextSelection);
    });
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm));
    await widget.onCitationFeedback?.call(citation, helpful);
  }

  String? _resolveDocumentRoute(ChatCitation citation) {
    final target = citation.navigationTarget;
    if (target == null || target.isEmpty) {
      return null;
    }
    return DeepLinkService.resolveRoute(target);
  }

  void _openDocument(String route) {
    if (mounted) {
      unawaited(context.push(route));
    }
  }
}
