import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:url_launcher/url_launcher.dart';

const aiContentFontFallback = <String>[
  'PingFang SC',
  'Hiragino Sans GB',
  'Heiti SC',
  'Noto Sans SC',
  'Noto Sans CJK SC',
  'Source Han Sans SC',
  'Microsoft YaHei',
  'Arial Unicode MS',
  'Apple Color Emoji',
  'Noto Color Emoji',
  'Segoe UI Emoji',
];

bool hasSafeMarkdownSyntax(String content) {
  if (content.trim().isEmpty) {
    return false;
  }
  return <RegExp>[
    RegExp(r'(^|\n)#{1,6}\s', multiLine: true),
    RegExp('```'),
    RegExp(r'`[^`\n]+`'),
    RegExp(r'\[[^\]]+\]\([^)]+\)'),
    RegExp(r'(^|\n)>\s', multiLine: true),
    RegExp(r'(^|\n)\|.+\|', multiLine: true),
    RegExp(r'(\*\*|__)[^*_]+(\*\*|__)'),
    RegExp(r'(^|\n)[-*+]\s', multiLine: true),
    RegExp(r'(^|\n)\d+\.\s', multiLine: true),
  ].any((pattern) => pattern.hasMatch(content.trim()));
}

MarkdownStyleSheet buildAiMarkdownStyle({
  required Color textColor,
  required Color codeBackgroundColor,
  required Color linkColor,
  double fontSize = 16,
  double height = 1.5,
}) => MarkdownStyleSheet(
    p: TextStyle(
      color: textColor,
      fontSize: fontSize,
      height: height,
      fontFamilyFallback: aiContentFontFallback,
    ),
    h1: TextStyle(
      color: textColor,
      fontSize: fontSize + 8,
      fontWeight: FontWeight.bold,
      fontFamilyFallback: aiContentFontFallback,
    ),
    h2: TextStyle(
      color: textColor,
      fontSize: fontSize + 6,
      fontWeight: FontWeight.bold,
      fontFamilyFallback: aiContentFontFallback,
    ),
    h3: TextStyle(
      color: textColor,
      fontSize: fontSize + 4,
      fontWeight: FontWeight.w600,
      fontFamilyFallback: aiContentFontFallback,
    ),
    h4: TextStyle(
      color: textColor,
      fontSize: fontSize + 2,
      fontWeight: FontWeight.w600,
      fontFamilyFallback: aiContentFontFallback,
    ),
    h5: TextStyle(
      color: textColor,
      fontSize: fontSize + 1,
      fontWeight: FontWeight.w600,
      fontFamilyFallback: aiContentFontFallback,
    ),
    h6: TextStyle(
      color: textColor,
      fontSize: fontSize,
      fontWeight: FontWeight.w600,
      fontFamilyFallback: aiContentFontFallback,
    ),
    strong: TextStyle(
      color: textColor,
      fontWeight: FontWeight.w700,
      fontFamilyFallback: aiContentFontFallback,
    ),
    em: TextStyle(
      color: textColor,
      fontStyle: FontStyle.italic,
      fontFamilyFallback: aiContentFontFallback,
    ),
    code: TextStyle(
      backgroundColor: codeBackgroundColor,
      color: textColor,
      fontSize: fontSize - 2,
      fontFamily: 'monospace',
      fontFamilyFallback: aiContentFontFallback,
    ),
    codeblockDecoration: BoxDecoration(
      color: codeBackgroundColor,
      borderRadius: BorderRadius.circular(12),
    ),
    a: TextStyle(
      color: linkColor,
      decoration: TextDecoration.underline,
      fontFamilyFallback: aiContentFontFallback,
    ),
    listBullet: TextStyle(
      color: textColor,
      fontFamilyFallback: aiContentFontFallback,
    ),
    blockquote: TextStyle(
      color: textColor,
      fontStyle: FontStyle.italic,
      fontFamilyFallback: aiContentFontFallback,
    ),
    );

class AiRichText extends StatelessWidget {
  const AiRichText({
    required this.content,
    required this.textColor,
    required this.codeBackgroundColor,
    required this.linkColor,
    super.key,
    this.fontSize = 16,
    this.height = 1.5,
    this.selectablePlainText = false,
  });

  final String content;
  final Color textColor;
  final Color codeBackgroundColor;
  final Color linkColor;
  final double fontSize;
  final double height;
  final bool selectablePlainText;

  @override
  Widget build(BuildContext context) {
    if (!hasSafeMarkdownSyntax(content)) {
      final textStyle = TextStyle(
        color: textColor,
        fontSize: fontSize,
        height: height,
        fontFamilyFallback: aiContentFontFallback,
      );
      if (selectablePlainText) {
        return SelectableText(content, style: textStyle);
      }
      return Text(content, style: textStyle);
    }

    return MarkdownBody(
      data: content,
      onTapLink: (text, href, title) async {
        if (href == null) {
          return;
        }
        final uri = Uri.tryParse(href);
        if (uri == null) {
          return;
        }
        final scheme = uri.scheme.toLowerCase();
        if (scheme != 'http' && scheme != 'https') {
          return;
        }
        try {
          if (await canLaunchUrl(uri)) {
            await launchUrl(uri, mode: LaunchMode.externalApplication);
          }
        } catch (_) {}
      },
      styleSheet: buildAiMarkdownStyle(
        textColor: textColor,
        codeBackgroundColor: codeBackgroundColor,
        linkColor: linkColor,
        fontSize: fontSize,
        height: height,
      ),
    );
  }
}
