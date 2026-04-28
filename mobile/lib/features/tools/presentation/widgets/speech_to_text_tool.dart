import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/chat/presentation/widgets/voice_input_button.dart';
import 'package:sparkle/features/tools/models/tool_definition.dart';
import 'package:sparkle/features/tools/presentation/widgets/tool_shell.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

class SpeechToTextTool extends StatefulWidget {
  const SpeechToTextTool({
    super.key,
    this.surface = ToolSurface.page,
    this.onTextResult,
  });

  final ToolSurface surface;
  final ValueChanged<String>? onTextResult;

  @override
  State<SpeechToTextTool> createState() => _SpeechToTextToolState();
}

class _SpeechToTextToolState extends State<SpeechToTextTool> {
  String _transcript = '';
  DateTime? _lastCapturedAt;

  int get _charCount => _transcript.trim().length;
  int get _wordCount => _transcript.trim().isEmpty
      ? 0
      : _transcript.trim().split(RegExp(r'\s+')).length;

  Future<void> _copyTranscript() async {
    if (_transcript.trim().isEmpty) {
      return;
    }
    await Clipboard.setData(ClipboardData(text: _transcript));
    if (!mounted) {
      return;
    }
    AppFeedback.success(context, '转写文本已复制');
  }

  @override
  Widget build(BuildContext context) {
    final accent = DS.info;
    final hasText = _transcript.trim().isNotEmpty;

    return ToolShell(
      surface: widget.surface,
      icon: Icons.mic_rounded,
      title: context.l10n.toolsSttTitle,
      subtitle: context.l10n.toolsSttSubtitle,
      accentColor: accent,
      compactHeader: true,
      heroChips: [
        ToolHeroChip(
          label: hasText ? '已捕获 $_charCount 字' : '30 秒单次录音',
          accentColor: accent,
          icon: Icons.graphic_eq_rounded,
        ),
        ToolHeroChip(
          label: _lastCapturedAt == null
              ? '实时转写'
              : '${_lastCapturedAt!.hour.toString().padLeft(2, '0')}:${_lastCapturedAt!.minute.toString().padLeft(2, '0')} 更新',
          accentColor: accent,
          icon: Icons.bolt_rounded,
        ),
      ],
      body: Column(
        children: [
          ToolMetricRow(
            children: [
              ToolMetricCard(
                label: context.l10n.toolsSttCharCountLabel,
                value: '$_charCount',
                accentColor: accent,
                icon: Icons.notes_rounded,
                caption: '适合直接发送或整理',
              ),
              ToolMetricCard(
                label: context.l10n.toolsSttWordCountLabel,
                value: '$_wordCount',
                accentColor: accent,
                icon: Icons.subject_rounded,
                caption: '便于快速判断长度',
              ),
            ],
          ),
          const SizedBox(height: DS.spacing16),
          ToolSectionCard(
            accentColor: accent,
            title: context.l10n.toolsSttRecordControl,
            subtitle: context.l10n.toolsSttRecordDesc,
            child: Center(
              child: VoiceInputButton(
                onTranscription: (text) {
                  setState(() {
                    _transcript = text;
                    _lastCapturedAt = DateTime.now();
                  });
                },
                onError: (error) {
                  AppFeedback.error(context, error);
                },
              ),
            ),
          ),
          const SizedBox(height: DS.spacing16),
          ConstrainedBox(
            constraints: const BoxConstraints(minHeight: 200),
            child: ToolSectionCard(
              accentColor: accent,
              title: context.l10n.toolsSttResult,
              subtitle: context.l10n.toolsSttResultDesc,
              child: hasText
                  ? SingleChildScrollView(
                      child: SelectableText(
                        _transcript,
                        style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                              color: DS.textPrimary,
                              height: 1.65,
                            ),
                      ),
                    )
                  : SingleChildScrollView(
                      child: ToolEmptyState(
                        icon: Icons.hearing_rounded,
                        title: context.l10n.toolsSttEmpty,
                        description: '开始一次录音后，文本会实时显示在这里。适合课堂摘录、灵感捕捉和会议补记。',
                        accentColor: accent,
                      ),
                    ),
            ),
          ),
        ],
      ),
      footer: LayoutBuilder(
        builder: (context, constraints) {
          final compact = constraints.maxWidth < 620;
          final actions = <Widget>[
            SparkleButton(
              label: context.l10n.toolsSttClear,
              variant: ButtonVariant.ghost,
              onPressed:
                  hasText ? () => setState(() => _transcript = '') : null,
              expand: true,
            ),
            SparkleButton(
              label: context.l10n.toolsSttCopy,
              onPressed: hasText ? _copyTranscript : null,
              icon: const Icon(Icons.copy_rounded),
              expand: true,
            ),
            if (widget.onTextResult != null)
              SparkleButton(
                label: context.l10n.toolsSttInsert,
                onPressed: hasText
                    ? () => widget.onTextResult!.call(_transcript.trim())
                    : null,
                icon: const Icon(Icons.arrow_forward_rounded),
                expand: true,
              ),
          ];

          if (compact) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                for (var index = 0; index < actions.length; index++) ...[
                  if (index > 0) const SizedBox(height: DS.spacing12),
                  actions[index],
                ],
              ],
            );
          }

          return Row(
            children: [
              for (var index = 0; index < actions.length; index++) ...[
                if (index > 0) const SizedBox(width: DS.spacing12),
                Expanded(child: actions[index]),
              ],
            ],
          );
        },
      ),
    );
  }
}
