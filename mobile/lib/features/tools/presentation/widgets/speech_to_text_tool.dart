import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/chat/presentation/widgets/voice_input_button.dart';

class SpeechToTextTool extends StatefulWidget {
  const SpeechToTextTool({super.key});

  @override
  State<SpeechToTextTool> createState() => _SpeechToTextToolState();
}

class _SpeechToTextToolState extends State<SpeechToTextTool> {
  String _transcript = '';

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
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(DS.spacing24),
        decoration: BoxDecoration(
          color: DS.surfacePrimary,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
          border: Border(
            top: BorderSide(color: DS.borderSubtle),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(DS.spacing10),
                  decoration: BoxDecoration(
                    color: DS.info.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(Icons.mic_rounded, color: DS.info),
                ),
                const SizedBox(width: DS.spacing12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '语音转文字',
                        style: Theme.of(context).textTheme.titleLarge?.copyWith(
                              fontWeight: DS.fontWeightBold,
                            ),
                      ),
                      const SizedBox(height: DS.spacing4),
                      Text(
                        '单次录音最长 30 秒，直接走当前已接通的 GLM ASR 实时链路。',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: DS.textSecondary,
                            ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: DS.spacing20),
            Center(
              child: VoiceInputButton(
                onTranscription: (text) {
                  setState(() {
                    _transcript = text;
                  });
                },
                onError: (error) {
                  AppFeedback.error(context, error);
                },
              ),
            ),
            const SizedBox(height: DS.spacing20),
            Container(
              padding: const EdgeInsets.all(DS.spacing16),
              constraints: const BoxConstraints(minHeight: 220),
              decoration: BoxDecoration(
                color: DS.surfaceSecondary,
                borderRadius: BorderRadius.circular(18),
                border: Border.all(color: DS.borderSubtle),
              ),
              child: Text(
                _transcript.isEmpty ? '点击麦克风开始转写，结果会实时显示在这里。' : _transcript,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: _transcript.isEmpty
                          ? DS.textSecondary
                          : DS.textPrimary,
                      height: 1.5,
                    ),
              ),
            ),
            const SizedBox(height: DS.spacing16),
            Row(
              children: [
                Expanded(
                  child: SparkleButton(
                    label: '清空',
                    variant: ButtonVariant.ghost,
                    onPressed: _transcript.isEmpty
                        ? null
                        : () => setState(() => _transcript = ''),
                  ),
                ),
                const SizedBox(width: DS.spacing12),
                Expanded(
                  child: SparkleButton(
                    label: '复制文本',
                    onPressed: _transcript.isEmpty ? null : _copyTranscript,
                    icon: const Icon(Icons.copy_rounded),
                  ),
                ),
              ],
            ),
          ],
        ),
      );
}
