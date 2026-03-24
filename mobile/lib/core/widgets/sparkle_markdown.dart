import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:markdown/markdown.dart' as md;
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sparkle_network_image.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:url_launcher/url_launcher.dart';

/// Font fallback list for CJK and emoji rendering.
/// Public so callers can use the same fallback stack for custom text widgets.
const sparkleFontFallback = <String>[
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

enum SparkleMarkdownRole {
  standard,
  chatBubble,
  taskGuide,
  seedBody,
  knowledgeSummary,
}

double _defaultLineHeightForRole(SparkleMarkdownRole role) => switch (role) {
      SparkleMarkdownRole.chatBubble => 1.45,
      SparkleMarkdownRole.taskGuide => 1.65,
      SparkleMarkdownRole.seedBody => 1.7,
      SparkleMarkdownRole.knowledgeSummary => 1.55,
      SparkleMarkdownRole.standard => 1.5,
    };

/// Unified markdown rendering widget for the entire Sparkle app.
///
/// Handles both static content and streaming AI responses with proper
/// incremental markdown rendering — similar to ChatGPT / Claude.
///
/// Usage:
/// ```dart
/// // Static content (task guides, seed library, knowledge details, etc.)
/// SparkleMarkdown(content: markdownString, textColor: DS.textPrimary, ...)
///
/// // Streaming content (chat, AI responses)
/// SparkleMarkdown(content: streamingText, isStreaming: true, ...)
/// ```
class SparkleMarkdown extends StatelessWidget {
  const SparkleMarkdown({
    required this.content,
    required this.textColor,
    required this.codeBackgroundColor,
    required this.linkColor,
    super.key,
    this.fontSize = 16,
    this.lineHeight,
    this.isStreaming = false,
    this.selectable = false,
    this.onLinkTap,
    this.shrinkWrap = true,
    this.contentRole = SparkleMarkdownRole.standard,
  });

  /// The markdown / plain text content to render.
  final String content;

  /// Primary text color.
  final Color textColor;

  /// Background color for inline `code` and code blocks.
  final Color codeBackgroundColor;

  /// Color for hyperlinks.
  final Color linkColor;

  /// Base font size in logical pixels.
  final double fontSize;

  /// Line height multiplier.
  final double? lineHeight;

  /// Whether content is actively being streamed (enables partial-markdown
  /// completion so incomplete syntax renders correctly).
  final bool isStreaming;

  /// Whether the rendered text should be selectable.
  final bool selectable;

  /// Custom link tap handler. If null, links open in external browser.
  final void Function(String text, String? href, String title)? onLinkTap;

  /// Whether the markdown body should shrink-wrap its content.
  final bool shrinkWrap;

  /// Scene-specific reading preset.
  final SparkleMarkdownRole contentRole;

  @override
  Widget build(BuildContext context) {
    if (content.isEmpty) {
      return const SizedBox.shrink();
    }

    final prepared = _prepareContent(content, isStreaming: isStreaming);
    final resolvedLineHeight =
        lineHeight ?? _defaultLineHeightForRole(contentRole);

    // Build the MarkdownBody — always attempt markdown rendering.
    // The normalization + completion pipeline ensures even plain text
    // renders correctly through the markdown renderer.
    final body = MarkdownBody(
      data: prepared,
      extensionSet: md.ExtensionSet.gitHubFlavored,
      listItemCrossAxisAlignment: MarkdownListItemCrossAxisAlignment.start,
      bulletBuilder: (index, style) {
        final bullet =
            style == BulletStyle.orderedList ? '${index + 1}.' : '•';
        return Padding(
          padding: const EdgeInsets.only(right: 8, top: 1),
          child: Text(
            bullet,
            style: TextStyle(
              color: textColor,
              fontSize: fontSize,
              height: resolvedLineHeight,
              fontFamilyFallback: sparkleFontFallback,
            ),
          ),
        );
      },
      softLineBreak: true,
      shrinkWrap: shrinkWrap,
      onTapLink: onLinkTap ?? _defaultLinkHandler,
      imageBuilder: (uri, title, alt) => _MarkdownNetworkImage(
        uri: uri,
        alt: alt,
      ),
      builders: {
        'pre': _CodeBlockBuilder(
          textColor: textColor,
          codeBackgroundColor: codeBackgroundColor,
          accentColor: linkColor,
        ),
      },
      styleSheet: _buildStyleSheet(),
    );

    if (selectable) {
      return SelectionArea(child: body);
    }

    return body;
  }

  MarkdownStyleSheet _buildStyleSheet() {
    final resolvedLineHeight =
        lineHeight ?? _defaultLineHeightForRole(contentRole);
    final base = TextStyle(
      color: textColor,
      fontSize: fontSize,
      height: resolvedLineHeight,
      fontFamilyFallback: sparkleFontFallback,
    );

    return MarkdownStyleSheet(
      p: base,
      h1: base.copyWith(fontSize: fontSize + 8, fontWeight: FontWeight.bold),
      h2: base.copyWith(fontSize: fontSize + 6, fontWeight: FontWeight.bold),
      h3: base.copyWith(fontSize: fontSize + 4, fontWeight: FontWeight.w600),
      h4: base.copyWith(fontSize: fontSize + 2, fontWeight: FontWeight.w600),
      h5: base.copyWith(fontSize: fontSize + 1, fontWeight: FontWeight.w600),
      h6: base.copyWith(fontWeight: FontWeight.w600),
      strong: base.copyWith(fontWeight: FontWeight.w700),
      em: base.copyWith(fontStyle: FontStyle.italic),
      code: TextStyle(
        backgroundColor: codeBackgroundColor,
        color: textColor,
        fontSize: fontSize - 2,
        fontFamily: 'monospace',
        fontFamilyFallback: sparkleFontFallback,
      ),
      codeblockDecoration: BoxDecoration(
        color: codeBackgroundColor,
        borderRadius: BorderRadius.circular(12),
      ),
      codeblockPadding: const EdgeInsets.all(12),
      a: base.copyWith(
        color: linkColor,
        decoration: TextDecoration.underline,
      ),
      listBullet: base,
      blockquote: base.copyWith(fontStyle: FontStyle.italic),
      blockquoteDecoration: BoxDecoration(
        border: Border(
          left: BorderSide(color: textColor.withValues(alpha: 0.3), width: 3),
        ),
      ),
      blockquotePadding: const EdgeInsets.only(left: 12, top: 4, bottom: 4),
      tableBorder: TableBorder.all(
        color: textColor.withValues(alpha: 0.2),
      ),
      tableHead: base.copyWith(fontWeight: FontWeight.w600),
      tableBody: base,
      tableCellsPadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      horizontalRuleDecoration: BoxDecoration(
        border: Border(
          top: BorderSide(color: textColor.withValues(alpha: 0.15)),
        ),
      ),
    );
  }

  Future<void> _defaultLinkHandler(String text, String? href, String title) async {
    if (href == null) return;
    final uri = Uri.tryParse(href);
    if (uri == null) return;
    final scheme = uri.scheme.toLowerCase();
    if (scheme != 'http' && scheme != 'https') return;
    try {
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri, mode: LaunchMode.externalApplication);
      }
    } catch (_) {}
  }
}

class _CodeBlockBuilder extends MarkdownElementBuilder {
  _CodeBlockBuilder({
    required this.textColor,
    required this.codeBackgroundColor,
    required this.accentColor,
  });

  final Color textColor;
  final Color codeBackgroundColor;
  final Color accentColor;

  @override
  Widget? visitElementAfter(md.Element element, TextStyle? preferredStyle) {
    final codeElement = element.children
        ?.whereType<md.Element>()
        .cast<md.Element?>()
        .firstWhere(
          (child) => child?.tag == 'code',
          orElse: () => null,
        );
    final className = codeElement?.attributes['class'] ?? '';
    final language = className.startsWith('language-')
        ? className.substring('language-'.length)
        : null;
    final code = codeElement?.textContent.trimRight() ?? element.textContent;
    return _CodeBlockCard(
      content: code,
      language: language,
      textColor: textColor,
      codeBackgroundColor: codeBackgroundColor,
      accentColor: accentColor,
    );
  }
}

class _CodeBlockCard extends StatefulWidget {
  const _CodeBlockCard({
    required this.content,
    required this.textColor,
    required this.codeBackgroundColor,
    required this.accentColor,
    this.language,
  });

  final String content;
  final String? language;
  final Color textColor;
  final Color codeBackgroundColor;
  final Color accentColor;

  @override
  State<_CodeBlockCard> createState() => _CodeBlockCardState();
}

class _CodeBlockCardState extends State<_CodeBlockCard> {
  bool _copied = false;

  Future<void> _handleCopy() async {
    await Clipboard.setData(ClipboardData(text: widget.content));
    await SensoryFeedbackService.emit(SensoryFeedbackEvent.success);
    if (!mounted) return;
    setState(() => _copied = true);
    Future<void>.delayed(const Duration(milliseconds: 800), () {
      if (mounted) {
        setState(() => _copied = false);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final languageLabel = _formatLanguage(widget.language);
    return RepaintBoundary(
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 6),
        decoration: BoxDecoration(
          color: widget.codeBackgroundColor,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: widget.textColor.withValues(alpha: 0.08),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(10, 8, 8, 6),
              child: Row(
                children: [
                  if (languageLabel != null)
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        color: widget.accentColor.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(999),
                      ),
                      child: Text(
                        languageLabel,
                        style: TextStyle(
                          color: widget.accentColor,
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  const Spacer(),
                  IconButton(
                    onPressed: _handleCopy,
                    icon: AnimatedSwitcher(
                      duration: const Duration(milliseconds: 180),
                      switchInCurve: Curves.easeOutCubic,
                      switchOutCurve: Curves.easeInCubic,
                      transitionBuilder: (child, animation) => ScaleTransition(
                        scale: animation,
                        child: FadeTransition(opacity: animation, child: child),
                      ),
                      child: Icon(
                        _copied ? Icons.check_rounded : Icons.copy_all_rounded,
                        key: ValueKey<bool>(_copied),
                        size: 18,
                      ),
                    ),
                    tooltip: '复制代码',
                    visualDensity: VisualDensity.compact,
                    color: _copied
                        ? DS.success
                        : widget.textColor.withValues(alpha: 0.78),
                  ),
                ],
              ),
            ),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
              child: SelectableText(
                widget.content,
                style: TextStyle(
                  color: widget.textColor,
                  fontSize: 13,
                  height: 1.5,
                  fontFamily: 'monospace',
                  fontFamilyFallback: sparkleFontFallback,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  String? _formatLanguage(String? raw) {
    if (raw == null || raw.trim().isEmpty) return null;
    final normalized = raw.trim().toLowerCase();
    switch (normalized) {
      case 'dart':
        return 'Dart';
      case 'python':
      case 'py':
        return 'Python';
      case 'javascript':
      case 'js':
        return 'JavaScript';
      case 'typescript':
      case 'ts':
        return 'TypeScript';
      case 'json':
        return 'JSON';
      case 'bash':
      case 'shell':
      case 'sh':
        return 'Shell';
      case 'yaml':
      case 'yml':
        return 'YAML';
      default:
        return normalized[0].toUpperCase() + normalized.substring(1);
    }
  }
}

class _MarkdownNetworkImage extends StatelessWidget {
  const _MarkdownNetworkImage({
    required this.uri,
    this.alt,
  });

  final Uri uri;
  final String? alt;

  @override
  Widget build(BuildContext context) => SparkleNetworkImage(
        imageUrl: uri.toString(),
        borderRadius: BorderRadius.circular(14),
        aspectRatio: 16 / 9,
        errorWidget: Container(
          padding: const EdgeInsets.all(12),
          color: DS.surfaceSecondary,
          alignment: Alignment.center,
          child: Text(
            alt?.trim().isNotEmpty ?? false ? alt! : '图片加载失败',
            style: const TextStyle(fontSize: 12),
          ),
        ),
      );
}

// ---------------------------------------------------------------------------
// Content preparation pipeline
// ---------------------------------------------------------------------------

/// Master preparation: normalize → (streaming ? complete partial syntax : noop)
String _prepareContent(String raw, {required bool isStreaming}) {
  var text = _normalize(raw);
  if (isStreaming) {
    text = _completePartialMarkdown(text);
  }
  return text;
}

/// Normalize AI-generated markdown to standard form.
///
/// Handles:
/// - CRLF → LF
/// - Zero-width / replacement characters
/// - Suspicious Unicode bullets → standard `-`
/// - Missing spaces after markdown markers (`#`, `-`, `>`, `1.`)
/// - Chinese punctuation numbered lists (`1、` → `1.`)
String _normalize(String raw) {
  var s = raw.replaceAll('\r\n', '\n');
  // Remove zero-width chars and replacement character
  s = s.replaceAll(RegExp(r'[\u200B-\u200D\uFEFF]'), '');
  s = s.replaceAll('\uFFFD', '');

  // Process line by line for bullet normalization
  final lines = s.split('\n');
  for (var i = 0; i < lines.length; i++) {
    lines[i] = _normalizeLine(lines[i]);
  }
  s = lines.join('\n');

  // Ensure space after list markers
  s = s.replaceAllMapped(
    RegExp(r'(^|\n)([-*+])(?=\S)', multiLine: true),
    (m) => '${m.group(1)}${m.group(2)} ',
  );
  // Ensure space after ordered list markers
  s = s.replaceAllMapped(
    RegExp(r'(^|\n)(\d+\.)(?=\S)', multiLine: true),
    (m) => '${m.group(1)}${m.group(2)} ',
  );
  // Chinese numbered lists: 1、 → 1.
  s = s.replaceAllMapped(
    RegExp(r'(^|\n)(\d+)[、．](?=\S)', multiLine: true),
    (m) => '${m.group(1)}${m.group(2)}. ',
  );
  // Ensure space after heading markers
  s = s.replaceAllMapped(
    RegExp(r'(^|\n)(#{1,6})(?=\S)', multiLine: true),
    (m) => '${m.group(1)}${m.group(2)} ',
  );
  // Ensure space after blockquote marker
  s = s.replaceAllMapped(
    RegExp(r'(^|\n)>(?=\S)', multiLine: true),
    (m) => '${m.group(1)}> ',
  );
  // Fix `-**` without space → `- **`
  s = s.replaceAllMapped(
    RegExp(r'(^|\n)([-*+])(\*\*|__)', multiLine: true),
    (m) => '${m.group(1)}${m.group(2)} ${m.group(3)}',
  );

  return s;
}

/// Normalize a single line — convert Unicode bullets to standard `-`.
String _normalizeLine(String raw) {
  final trimmedLeft = raw.trimLeft();
  final leading = raw.substring(0, raw.length - trimmedLeft.length);
  if (trimmedLeft.isEmpty) return raw;

  // Unicode bullet characters that AI models sometimes emit
  const unicodeBullets = <String>{
    '•', '●', '▪', '◦', '‣', '·', '◉', '○', '◆', '◇',
    '▶', '▸', '－', '—', '–',
  };

  for (final bullet in unicodeBullets) {
    if (trimmedLeft.startsWith(bullet)) {
      final rest = trimmedLeft.substring(bullet.length).trimLeft();
      return '$leading- $rest';
    }
  }

  // Lines starting with ? or replacement chars followed by content → `-`
  final suspiciousMatch = RegExp(
    r'^[?？�]+[\s\u3000]*',
  ).firstMatch(trimmedLeft);
  if (suspiciousMatch != null) {
    final rest = trimmedLeft.substring(suspiciousMatch.end).trimLeft();
    if (rest.isNotEmpty) {
      return '$leading- $rest';
    }
  }

  // Parenthesized numbers: (1) or （1） → 1.
  final numberedMatch = RegExp(r'^[(（]?(\d+)[)）][\s\u3000]*').firstMatch(
    trimmedLeft,
  );
  if (numberedMatch != null) {
    final rest = trimmedLeft.substring(numberedMatch.end).trimLeft();
    if (rest.isNotEmpty) {
      return '$leading${numberedMatch.group(1)}. $rest';
    }
  }

  return raw;
}

/// Complete partial / unterminated markdown so it renders correctly
/// during streaming.
///
/// This is the key function that makes streaming markdown work like
/// ChatGPT / Claude — we auto-close any open syntax so the markdown
/// parser can produce valid output for the current partial content.
String _completePartialMarkdown(String content) {
  var result = content;

  // 1. Close unclosed fenced code blocks
  final tripleBacktickCount = RegExp('```').allMatches(result).length;
  if (tripleBacktickCount.isOdd) {
    // If the last ``` is the opening one, add a closing one
    result = '$result\n```';
  }

  // 2. Close unclosed inline code (single backtick)
  //    Only fix if we're inside an inline code span (odd count of single
  //    backticks that aren't part of triple backticks).
  final singleBacktickContent = result.replaceAll('```', '');
  final singleBacktickCount = '`'.allMatches(singleBacktickContent).length;
  if (singleBacktickCount.isOdd) {
    result = '$result`';
  }

  // 3. Close unclosed bold (**) — count pairs
  final boldCount = RegExp(r'\*\*').allMatches(result).length;
  if (boldCount.isOdd) {
    result = '$result**';
  }

  // 4. Close unclosed bold (__)
  final underscoreBoldCount = RegExp('__').allMatches(result).length;
  if (underscoreBoldCount.isOdd) {
    result = '${result}__';
  }

  // 5. Close unclosed italic (*) — after handling bold
  //    Count single asterisks not part of **
  final afterBold = result.replaceAll('**', '');
  final italicCount = '*'.allMatches(afterBold).length;
  if (italicCount.isOdd) {
    result = '$result*';
  }

  // 6. Close unclosed italic (_) — after handling __
  final afterUnderBold = result.replaceAll('__', '');
  final underItalicCount = '_'.allMatches(afterUnderBold).length;
  if (underItalicCount.isOdd) {
    result = '${result}_';
  }

  // 7. Close unclosed strikethrough (~~)
  final strikeCount = RegExp('~~').allMatches(result).length;
  if (strikeCount.isOdd) {
    result = '$result~~';
  }

  return result;
}
