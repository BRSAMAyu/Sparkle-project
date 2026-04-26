import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/widgets/sparkle_markdown.dart';

/// Renders Aurora multi-message output as visually segmented cards
/// instead of a flat text block.
///
/// When the backend sends multiple messages via Aurora's ChatLayerAdapter
/// (multimessage_allowed, up to 3 messages), they arrive joined by `\n\n`
/// with `aurora_message_count` in rawMetadata. This widget splits them
/// and renders each as a distinct card with subtle separators.
class AuroraMessageGroup extends StatelessWidget {
  const AuroraMessageGroup({
    required this.segments,
    super.key,
  });

  /// Split [content] on double-newline boundaries and return segments,
  /// but only if [rawMetadata] indicates `aurora_message_count > 1`.
  /// Returns `null` if the message should be rendered normally (not grouped).
  static List<String>? tryParse({
    required String content,
    required Map<String, dynamic>? rawMetadata,
  }) {
    if (rawMetadata == null) return null;
    final surface = rawMetadata['aurora_surface'];
    if (surface == null) return null;
    final countRaw = rawMetadata['aurora_message_count'];
    if (countRaw == null) return null;
    final count = int.tryParse(countRaw.toString());
    if (count == null || count <= 1) return null;

    final parts = content.split('\n\n').where((s) => s.trim().isNotEmpty).toList();
    if (parts.length <= 1) return null;
    return parts;
  }

  final List<String> segments;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (int i = 0; i < segments.length; i++) ...[
          if (i > 0)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: DS.spacing6),
              child: Row(
                children: [
                  SizedBox(
                    width: 16,
                    child: Center(
                      child: Container(
                        width: 3,
                        height: 3,
                        decoration: BoxDecoration(
                          color: DS.brandPrimary.withValues(alpha: 0.35),
                          shape: BoxShape.circle,
                        ),
                      ),
                    ),
                  ),
                  Expanded(
                    child: Container(
                      height: 0.5,
                      color: DS.borderSubtle,
                    ),
                  ),
                  SizedBox(
                    width: 16,
                    child: Center(
                      child: Container(
                        width: 3,
                        height: 3,
                        decoration: BoxDecoration(
                          color: DS.brandPrimary.withValues(alpha: 0.35),
                          shape: BoxShape.circle,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          SparkleMarkdown(
            content: segments[i],
            textColor: DS.chatBubbleOtherText,
            codeBackgroundColor: DS.surfaceTertiary,
            linkColor: DS.brandPrimary,
            contentRole: SparkleMarkdownRole.chatBubble,
          ),
        ],
      ],
    );
  }
}
