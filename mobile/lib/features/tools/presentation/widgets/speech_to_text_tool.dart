import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/chat/presentation/widgets/voice_input_button.dart';
import 'package:sparkle/features/tools/models/tool_definition.dart';
import 'package:sparkle/features/tools/presentation/widgets/tool_shell.dart';

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
      title: '语音转文字',
      subtitle: '面向真实记录场景的轻量转写台。单次录音最长 30 秒，直接调用当前已接通的 GLM ASR 链路。',
      accentColor: accent,
      compactHeader: true,
      fillHeight: false,
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
          Wrap(
            spacing: DS.spacing12,
            runSpacing: DS.spacing12,
            children: [
              ToolMetricCard(
                label: '字数',
                value: '$_charCount',
                accentColor: accent,
                icon: Icons.notes_rounded,
                caption: '适合直接发送或整理',
              ),
              ToolMetricCard(
                label: '词数',
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
            title: '录音控制',
            subtitle: '点击麦克风开始录音，再次点击结束转写。',
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
          SizedBox(
            height: 360,
            child: ToolSectionCard(
              accentColor: accent,
              title: '转写结果',
              subtitle: '结果区支持直接复制，可作为后续写作和总结的原文底稿。',
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
                        title: '还没有转写内容',
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
              label: '清空',
              variant: ButtonVariant.ghost,
              onPressed:
                  hasText ? () => setState(() => _transcript = '') : null,
              expand: true,
            ),
            SparkleButton(
              label: '复制文本',
              onPressed: hasText ? _copyTranscript : null,
              icon: const Icon(Icons.copy_rounded),
              expand: true,
            ),
            if (widget.onTextResult != null)
              SparkleButton(
                label: '插入内容',
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
