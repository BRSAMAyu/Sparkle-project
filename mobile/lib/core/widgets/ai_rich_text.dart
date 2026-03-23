import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:markdown/markdown.dart' as md;
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
  final trimmed = content.trim();
  if (trimmed.isEmpty) {
    return false;
  }
  if (!_hasBalancedMarkdownDelimiters(trimmed)) {
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
  ].any((pattern) => pattern.hasMatch(trimmed));
}

String normalizeAiMarkdown(String content) {
  var normalized = content.replaceAll('\r\n', '\n');
  normalized = normalized.replaceAll(
    RegExp(r'[\u200B-\u200D\uFEFF]'),
    '',
  );
  normalized = normalized.replaceAll('\uFFFD', '');
  final normalizedLines = normalized
      .split('\n')
      .map(_normalizeAiMarkdownLine)
      .toList();
  normalized = normalizedLines.join('\n');
  normalized = normalized.replaceAllMapped(
    RegExp(r'(^|\n)([-*+])(?=\S)', multiLine: true),
    (match) => '${match.group(1)}${match.group(2)} ',
  );
  normalized = normalized.replaceAllMapped(
    RegExp(r'(^|\n)(\d+\.)(?=\S)', multiLine: true),
    (match) => '${match.group(1)}${match.group(2)} ',
  );
  normalized = normalized.replaceAllMapped(
    RegExp(r'(^|\n)(\d+)[、．](?=\S)', multiLine: true),
    (match) => '${match.group(1)}${match.group(2)}. ',
  );
  normalized = normalized.replaceAllMapped(
    RegExp(r'(^|\n)(#{1,6})(?=\S)', multiLine: true),
    (match) => '${match.group(1)}${match.group(2)} ',
  );
  normalized = normalized.replaceAllMapped(
    RegExp(r'(^|\n)>(?=\S)', multiLine: true),
    (match) => '${match.group(1)}> ',
  );
  normalized = normalized.replaceAllMapped(
    RegExp(r'(^|\n)([-*+]\s+)(?=(\*\*|__)\S)', multiLine: true),
    (match) => '${match.group(1)}${match.group(2)}',
  );
  normalized = normalized.replaceAllMapped(
    RegExp(r'(^|\n)([-*+])(\*\*|__)', multiLine: true),
    (match) => '${match.group(1)}${match.group(2)} ${match.group(3)}',
  );
  return normalized;
}

String _normalizeAiMarkdownLine(String rawLine) {
  final line = rawLine;
  final trimmedLeft = line.trimLeft();
  final leadingWhitespace = line.substring(0, line.length - trimmedLeft.length);
  if (trimmedLeft.isEmpty) {
    return line;
  }

  final suspiciousLeadingMarkers = <String>{
    '•',
    '●',
    '▪',
    '◦',
    '‣',
    '?',
    '？',
    '�',
    '·',
    '•️',
    '◉',
    '○',
    '◆',
    '◇',
    '▶',
    '▸',
    '－',
    '—',
    '–',
  };

  if (suspiciousLeadingMarkers.any(trimmedLeft.startsWith)) {
    final marker = suspiciousLeadingMarkers.firstWhere(trimmedLeft.startsWith);
    final rest = trimmedLeft.substring(marker.length).trimLeft();
    return '$leadingWhitespace- $rest';
  }

  final suspiciousBulletMatch = RegExp(
    r'^[?？�]+[\s\u3000]*(\*\*|__|#+\s+|[-*+]\s+|\d+\.\s+)?',
  ).firstMatch(trimmedLeft);
  if (suspiciousBulletMatch != null) {
    final rest = trimmedLeft.substring(suspiciousBulletMatch.end).trimLeft();
    if (rest.isNotEmpty) {
      return '$leadingWhitespace- $rest';
    }
  }

  if (trimmedLeft.startsWith('-**') || trimmedLeft.startsWith('-__')) {
    return '$leadingWhitespace- ${trimmedLeft.substring(1)}';
  }

  if (trimmedLeft.startsWith('***') || trimmedLeft.startsWith('*__')) {
    return '$leadingWhitespace- ${trimmedLeft.substring(1)}';
  }

  final numberedMatch = RegExp(r'^[(（]?(\d+)[)）][\s\u3000]*').firstMatch(
    trimmedLeft,
  );
  if (numberedMatch != null) {
    final rest = trimmedLeft.substring(numberedMatch.end).trimLeft();
    if (rest.isNotEmpty) {
      return '$leadingWhitespace${numberedMatch.group(1)}. $rest';
    }
  }

  return line;
}

bool _hasBalancedMarkdownDelimiters(String content) {
  final tripleBackticks = RegExp('```').allMatches(content).length;
  final doubleAsterisks = RegExp(r'\*\*').allMatches(content).length;
  final doubleUnderscores = RegExp('__').allMatches(content).length;
  return tripleBackticks.isEven &&
      doubleAsterisks.isEven &&
      doubleUnderscores.isEven;
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
    final normalizedContent = normalizeAiMarkdown(content);
    if (!hasSafeMarkdownSyntax(normalizedContent)) {
      final textStyle = TextStyle(
        color: textColor,
        fontSize: fontSize,
        height: height,
        fontFamilyFallback: aiContentFontFallback,
      );
      if (selectablePlainText) {
        return SelectableText(normalizedContent, style: textStyle);
      }
      return Text(normalizedContent, style: textStyle);
    }

    return MarkdownBody(
      data: normalizedContent,
      extensionSet: md.ExtensionSet.gitHubFlavored,
      listItemCrossAxisAlignment: MarkdownListItemCrossAxisAlignment.start,
      bulletBuilder: (index, style) {
        final bulletText =
            style == BulletStyle.orderedList ? '${index + 1}.' : '-';
        return Padding(
          padding: const EdgeInsets.only(right: 8, top: 1),
          child: Text(
            bulletText,
            style: TextStyle(
              color: textColor,
              fontSize: fontSize,
              height: height,
              fontFamilyFallback: aiContentFontFallback,
            ),
          ),
        );
      },
      softLineBreak: true,
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
