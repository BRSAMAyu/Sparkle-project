import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/widgets/sparkle_markdown.dart';

/// U-05（v3/03_modules/CHAT.md「action proposal 以卡片进入确认，不藏在长段落」）：
/// 长建议的结构化呈现层。
///
/// 当一条助手消息是「长建议」且自带可确定性识别的列表结构（编号 / 项目符号）
/// 时，把裸 markdown 墙转成 proposal 式条目列表：序号徽标 + 单条内容行。
/// 纯文本段落（无列表结构）或含围栏代码块的内容不适用——回退到原有
/// markdown 渲染，行为与改动前一致。
///
/// 边界约束：
/// - 这只是表现层的确定性排版（正则识别 markdown 列表语法），不是新的
///   语义真源：真正的 action proposal 卡（ActionCard）仍只由后端
///   action_proposal 载荷触发，本组件不渲染任何确认按钮，不产生可执行语义；
/// - 来源/回执锚点（AssistantCitationStrip / ContextReceiptBar）保持挂在
///   气泡下方，与本组件互补（proposal / source / receipt 三件套）。
class StructuredSuggestionBody extends StatelessWidget {
  const StructuredSuggestionBody({
    required this.content,
    required this.textColor,
    this.codeBackgroundColor,
    this.linkColor,
    super.key,
  });

  final String content;
  final Color textColor;
  final Color? codeBackgroundColor;
  final Color? linkColor;

  static final RegExp _orderedItem = RegExp(r'^\s*(\d{1,2})[.)、]\s+(.*)$');
  static final RegExp _bulletItem = RegExp(r'^\s*[-*+•]\s+(.*)$');
  static final RegExp _fence = RegExp(r'^\s*```', multiLine: true);

  /// 确定性结构探测：内容包含 ≥2 个列表条目、且不含围栏代码块时，
  /// 认为适合结构化呈现。静态可测、无启发式 NLP。
  static bool hasListStructure(String content) {
    if (_fence.hasMatch(content)) {
      return false;
    }
    var count = 0;
    for (final line in content.split('\n')) {
      if (_orderedItem.hasMatch(line) || _bulletItem.hasMatch(line)) {
        count++;
        if (count >= 2) {
          return true;
        }
      }
    }
    return false;
  }

  @override
  Widget build(BuildContext context) {
    final segments = _splitSegments(content);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        for (final segment in segments) ...[
          if (segment.isList)
            for (final item in segment.items)
              _ProposalRow(item: item, textColor: textColor),
          if (!segment.isList)
            SparkleMarkdown(
              content: segment.prose,
              textColor: textColor,
              codeBackgroundColor: codeBackgroundColor ?? DS.surfaceTertiary,
              linkColor: linkColor ?? DS.brandPrimary,
              contentRole: SparkleMarkdownRole.chatBubble,
            ),
        ],
      ],
    );
  }

  /// 行级确定性分块：连续列表行归为一个列表段，其余行归为 prose 段。
  /// 列表条目保留原文（含条内 markdown 强调），仅剥离列表标记。
  List<_SuggestionSegment> _splitSegments(String content) {
    final segments = <_SuggestionSegment>[];
    final currentProse = <String>[];
    final currentItems = <_ProposalItemData>[];

    void flushProse() {
      final text = currentProse.join('\n').trim();
      if (text.isNotEmpty) {
        segments.add(_SuggestionSegment.prose(text));
      }
      currentProse.clear();
    }

    void flushItems() {
      if (currentItems.isNotEmpty) {
        segments.add(_SuggestionSegment.list(List.of(currentItems)));
        currentItems.clear();
      }
    }

    for (final line in content.split('\n')) {
      final ordered = _orderedItem.firstMatch(line);
      final bullet = _bulletItem.firstMatch(line);
      if (ordered != null) {
        flushProse();
        currentItems.add(
          _ProposalItemData(
            index: int.tryParse(ordered.group(1)!),
            text: ordered.group(2)!.trim(),
          ),
        );
      } else if (bullet != null) {
        flushProse();
        currentItems
            .add(_ProposalItemData(index: null, text: bullet.group(1)!.trim()));
      } else {
        flushItems();
        currentProse.add(line);
      }
    }
    flushProse();
    flushItems();
    return segments;
  }
}

class _SuggestionSegment {
  const _SuggestionSegment.prose(this.prose)
      : isList = false,
        items = const [];

  const _SuggestionSegment.list(this.items)
      : isList = true,
        prose = '';

  final bool isList;
  final String prose;
  final List<_ProposalItemData> items;
}

class _ProposalItemData {
  const _ProposalItemData({required this.index, required this.text});

  /// 编号列表的序号（1 起）；null = 项目符号条目。
  final int? index;
  final String text;
}

/// 单条 proposal 行：序号徽标 + 内容。徽标只做视觉导航（proposal 结构），
/// 不携带任何按钮语义——确认动作仍只属于 ActionCard。
class _ProposalRow extends StatelessWidget {
  const _ProposalRow({required this.item, required this.textColor});

  final _ProposalItemData item;
  final Color textColor;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: DS.spacing8),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: DS.iconSizeBase,
              height: DS.iconSizeBase,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: DS.brandPrimary.withValues(alpha: 0.1),
                shape: BoxShape.circle,
                border: Border.all(
                  color: DS.brandPrimary.withValues(alpha: 0.18),
                ),
              ),
              child: item.index != null
                  ? Text(
                      '${item.index}',
                      style: DS.labelSmall.copyWith(
                        color: DS.brandPrimary,
                        fontWeight: DS.fontWeightBold,
                      ),
                    )
                  : Icon(
                      Icons.arrow_right_alt_rounded,
                      size: DS.iconSizeXs,
                      color: DS.brandPrimary,
                    ),
            ),
            const SizedBox(width: DS.spacing8),
            Expanded(
              child: SparkleMarkdown(
                content: item.text,
                textColor: textColor,
                codeBackgroundColor: DS.surfaceTertiary,
                linkColor: DS.brandPrimary,
                contentRole: SparkleMarkdownRole.chatBubble,
              ),
            ),
          ],
        ),
      );
}
