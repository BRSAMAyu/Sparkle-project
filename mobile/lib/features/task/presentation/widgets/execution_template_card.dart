import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/task/data/models/execution_template_model.dart';

class ExecutionTemplateCard extends StatelessWidget {
  const ExecutionTemplateCard({
    required this.template,
    required this.isSelected,
    required this.onTap,
    super.key,
  });

  final ExecutionTemplateModel template;
  final bool isSelected;
  final VoidCallback onTap;

  (IconData, Color) _visualForTemplate() {
    switch (template.templateId) {
      case 'web_research_brief':
        return (Icons.travel_explore_rounded, DS.info);
      case 'document_digest':
        return (Icons.summarize_rounded, DS.semanticSuccess);
      case 'shell_diagnostics':
        return (Icons.terminal_rounded, DS.semanticWarning);
      case 'browser_form_prepare':
        return (Icons.edit_document, DS.brandPrimary);
      case 'cross_device_capture':
        return (Icons.devices_rounded, DS.brandSecondary);
      default:
        return (Icons.smart_toy_rounded, DS.textSecondary);
    }
  }

  @override
  Widget build(BuildContext context) {
    final (icon, accent) = _visualForTemplate();
    final score = template.matchScore.clamp(0.0, 1.0);

    return AnimatedContainer(
      duration: DS.quick,
      curve: Curves.easeOutCubic,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(18),
          onTap: () {
            unawaited(
              SensoryFeedbackService.emit(SensoryFeedbackEvent.selection),
            );
            onTap();
          },
          child: Container(
            height: 72,
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing12,
              vertical: DS.spacing10,
            ),
            decoration: BoxDecoration(
              color: isSelected ? DS.surfacePrimary : DS.surfaceSecondary,
              borderRadius: BorderRadius.circular(18),
              border: Border.all(
                color: isSelected ? accent : Colors.transparent,
                width: isSelected ? 2 : 1,
              ),
            ),
            child: Row(
              children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: accent.withValues(alpha: 0.12),
                    shape: BoxShape.circle,
                  ),
                  alignment: Alignment.center,
                  child: Icon(icon, color: accent, size: 20),
                ),
                const SizedBox(width: DS.spacing12),
                Expanded(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        template.name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: DS.bodyMedium.copyWith(
                          fontWeight: DS.fontWeightMedium,
                        ),
                      ),
                      const SizedBox(height: DS.spacing4),
                      Text(
                        template.description,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: DS.bodySmall.copyWith(
                          fontSize: 12,
                          color: DS.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: DS.spacing12),
                Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    if (score > 0)
                      SizedBox(
                        width: 36,
                        height: 36,
                        child: Stack(
                          alignment: Alignment.center,
                          children: [
                            CircularProgressIndicator(
                              value: score,
                              strokeWidth: 3,
                              color: accent,
                              backgroundColor: accent.withValues(alpha: 0.14),
                            ),
                            Text(
                              '${(score * 100).round()}%',
                              style: DS.bodySmall.copyWith(fontSize: 10),
                            ),
                          ],
                        ),
                      ),
                    const SizedBox(height: DS.spacing4),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: DS.spacing8,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        color: accent.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(999),
                      ),
                      child: Text(
                        template.modeLabel,
                        style: DS.bodySmall.copyWith(
                          fontSize: 10,
                          color: accent,
                          fontWeight: DS.fontWeightBold,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
