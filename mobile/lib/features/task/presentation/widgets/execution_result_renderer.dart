import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:sparkle/core/design/design_system.dart';

enum ResultContentType {
  plainText,
  structured,
  markdown,
  codeBlock,
  linkList,
  mixed,
}

class ExecutionResultRenderer extends StatelessWidget {
  const ExecutionResultRenderer({
    required this.parsedOutput,
    super.key,
    this.artifacts,
    this.expanded = false,
  });

  final Map<String, dynamic> parsedOutput;
  final List<Map<String, dynamic>>? artifacts;
  final bool expanded;

  static ResultContentType detectContentType(Map<String, dynamic> output) {
    final text =
        output['text'] as String? ?? output['content'] as String? ?? '';
    final hasLinks =
        output.containsKey('urls') ||
        output.containsKey('links') ||
        output.containsKey('sources');
    final hasNonLinkContent =
        text.trim().isNotEmpty ||
        output.keys.any(
          (key) => key != 'urls' && key != 'links' && key != 'sources',
        );
    final indentedLines = text
        .split('\n')
        .where((line) => line.startsWith('    '))
        .length;
    final hasCode = text.contains('```') || indentedLines > 3;
    final hasMarkdown =
        text.contains('# ') ||
        text.contains('**') ||
        text.contains('- ') ||
        text.contains('| ');

    if (hasLinks && hasNonLinkContent) return ResultContentType.mixed;
    if (hasLinks) return ResultContentType.linkList;
    if (hasCode && !hasMarkdown) return ResultContentType.codeBlock;
    if (hasMarkdown) return ResultContentType.markdown;
    if (output.keys.length > 2) return ResultContentType.structured;
    return text.trim().isEmpty
        ? ResultContentType.structured
        : ResultContentType.plainText;
  }

  @override
  Widget build(BuildContext context) {
    final contentType = detectContentType(parsedOutput);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildContent(context, contentType),
        if ((artifacts ?? const []).isNotEmpty) ...[
          const SizedBox(height: DS.spacing12),
          Divider(color: DS.borderSubtle, height: 1),
          const SizedBox(height: DS.spacing12),
          Text(
            '附件产物',
            style: DS.bodySmall.copyWith(
              fontWeight: DS.fontWeightBold,
              color: DS.textSecondary,
            ),
          ),
          const SizedBox(height: DS.spacing8),
          ...((artifacts ?? const <Map<String, dynamic>>[])
              .map((artifact) => _ArtifactTile(artifact: artifact))),
        ],
      ],
    );
  }

  Widget _buildContent(BuildContext context, ResultContentType type) {
    switch (type) {
      case ResultContentType.plainText:
        return _PlainTextBlock(text: _extractPrimaryText(parsedOutput));
      case ResultContentType.structured:
        return _StructuredBlock(
          parsedOutput: parsedOutput,
          expanded: expanded,
        );
      case ResultContentType.markdown:
        return _MarkdownLikeBlock(text: _extractPrimaryText(parsedOutput));
      case ResultContentType.codeBlock:
        return _CodeBlock(text: _extractPrimaryText(parsedOutput));
      case ResultContentType.linkList:
        return _LinkListBlock(parsedOutput: parsedOutput);
      case ResultContentType.mixed:
        return _MixedBlock(
          parsedOutput: parsedOutput,
          expanded: expanded,
        );
    }
  }

  static Map<String, dynamic> _withoutLinkFields(Map<String, dynamic> output) {
    final sanitized = Map<String, dynamic>.from(output);
    sanitized.remove('urls');
    sanitized.remove('links');
    sanitized.remove('sources');
    return sanitized;
  }

  static String _extractPrimaryText(Map<String, dynamic> output) {
    final text =
        output['text'] as String? ??
        output['content'] as String? ??
        output['summary'] as String? ??
        '';
    if (text.trim().isNotEmpty) return text.trim();
    return output.entries
        .map((entry) => '${entry.key}: ${entry.value}')
        .join('\n')
        .trim();
  }
}

class _PlainTextBlock extends StatelessWidget {
  const _PlainTextBlock({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return SelectableText(
      text.isEmpty ? '暂无文本结果。' : text,
      style: DS.bodySmall.copyWith(
        color: DS.textPrimary,
        height: 1.5,
      ),
    );
  }
}

class _StructuredBlock extends StatelessWidget {
  const _StructuredBlock({
    required this.parsedOutput,
    required this.expanded,
  });

  final Map<String, dynamic> parsedOutput;
  final bool expanded;

  String _displayValue(Object? value) {
    if (value is List) {
      return value.map((item) => '$item').join(', ');
    }
    if (value is Map) {
      return value.entries.map((entry) => '${entry.key}: ${entry.value}').join(', ');
    }
    return '$value';
  }

  @override
  Widget build(BuildContext context) {
    final entries = parsedOutput.entries.toList();
    final visibleEntries = expanded ? entries : entries.take(5).toList();
    if (entries.isEmpty) {
      return Text(
        '暂无结构化结果字段。',
        style: DS.bodySmall.copyWith(color: DS.textSecondary),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ...visibleEntries.map(
          (entry) => Padding(
            padding: const EdgeInsets.only(bottom: DS.spacing8),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  entry.key,
                  style: DS.labelSmall.copyWith(
                    fontWeight: DS.fontWeightBold,
                    color: DS.textSecondary,
                  ),
                ),
                const SizedBox(height: DS.spacing4),
                SelectableText(
                  _displayValue(entry.value),
                  style: DS.bodySmall.copyWith(
                    color: DS.textPrimary,
                    height: 1.5,
                  ),
                ),
              ],
            ),
          ),
        ),
        if (!expanded && entries.length > visibleEntries.length)
          Text(
            '还有 ${entries.length - visibleEntries.length} 个字段',
            style: DS.bodySmall.copyWith(color: DS.textSecondary),
          ),
      ],
    );
  }
}

class _MarkdownLikeBlock extends StatelessWidget {
  const _MarkdownLikeBlock({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    final lines = text.split('\n');
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: lines.map((line) {
        final trimmed = line.trimRight();
        if (trimmed.startsWith('```')) {
          return const SizedBox.shrink();
        }
        if (trimmed.startsWith('# ')) {
          return Padding(
            padding: const EdgeInsets.only(bottom: DS.spacing6),
            child: Text(
              trimmed.substring(2),
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
          );
        }
        if (trimmed.startsWith('- ')) {
          return Padding(
            padding: const EdgeInsets.only(bottom: DS.spacing4),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Padding(
                  padding: EdgeInsets.only(top: 6),
                  child: Icon(Icons.circle, size: 6, color: DS.textSecondary),
                ),
                const SizedBox(width: DS.spacing8),
                Expanded(
                  child: SelectableText(
                    trimmed.substring(2),
                    style: DS.bodySmall.copyWith(
                      color: DS.textPrimary,
                      height: 1.5,
                    ),
                  ),
                ),
              ],
            ),
          );
        }
        return Padding(
          padding: const EdgeInsets.only(bottom: DS.spacing6),
          child: SelectableText(
            trimmed,
            style: DS.bodySmall.copyWith(
              color: DS.textPrimary,
              height: 1.5,
            ),
          ),
        );
      }).toList(),
    );
  }
}

class _CodeBlock extends StatelessWidget {
  const _CodeBlock({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        color: DS.surfaceTertiary,
        borderRadius: BorderRadius.circular(8),
      ),
      child: SelectableText(
        text.isEmpty ? '暂无代码结果。' : text,
        style: DS.bodySmall.copyWith(
          color: DS.textPrimary,
          height: 1.5,
          fontFamily: 'monospace',
        ),
      ),
    );
  }
}

class _LinkListBlock extends StatelessWidget {
  const _LinkListBlock({required this.parsedOutput});

  final Map<String, dynamic> parsedOutput;

  List<Map<String, String>> _extractLinks() {
    final rawLinks =
        parsedOutput['urls'] ?? parsedOutput['links'] ?? parsedOutput['sources'];
    if (rawLinks is! List) return const [];
    return rawLinks.map((item) {
      if (item is Map) {
        final map = Map<String, dynamic>.from(item);
        return {
          'url':
              map['url']?.toString() ??
              map['href']?.toString() ??
              map['link']?.toString() ??
              '',
          'title': map['title']?.toString() ?? map['name']?.toString() ?? '',
        };
      }
      return {
        'url': item.toString(),
        'title': '',
      };
    }).where((item) => (item['url'] ?? '').isNotEmpty).toList();
  }

  String _domainOf(String url) {
    final uri = Uri.tryParse(url);
    return uri?.host.isNotEmpty == true ? uri!.host : url;
  }

  @override
  Widget build(BuildContext context) {
    final links = _extractLinks();
    if (links.isEmpty) {
      return Text(
        '暂无链接结果。',
        style: DS.bodySmall.copyWith(color: DS.textSecondary),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: links.map((link) {
        return InkWell(
          onTap: () async {
            await Clipboard.setData(ClipboardData(text: link['url'] ?? ''));
            if (context.mounted) {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('链接已复制')),
              );
            }
          },
          borderRadius: BorderRadius.circular(12),
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: DS.spacing6),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(
                  Icons.link_rounded,
                  size: 16,
                  color: DS.textSecondary,
                ),
                const SizedBox(width: DS.spacing8),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        _domainOf(link['url'] ?? ''),
                        style: DS.bodySmall.copyWith(
                          color: DS.info,
                          fontWeight: DS.fontWeightBold,
                        ),
                      ),
                      if ((link['title'] ?? '').trim().isNotEmpty)
                        Text(
                          link['title']!,
                          style: DS.bodySmall.copyWith(
                            color: DS.textPrimary,
                          ),
                        ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        );
      }).toList(),
    );
  }
}

class _MixedBlock extends StatelessWidget {
  const _MixedBlock({
    required this.parsedOutput,
    required this.expanded,
  });

  final Map<String, dynamic> parsedOutput;
  final bool expanded;

  @override
  Widget build(BuildContext context) {
    final contentOnly = ExecutionResultRenderer._withoutLinkFields(parsedOutput);
    final contentType = ExecutionResultRenderer.detectContentType(contentOnly);

    Widget primaryContent;
    switch (contentType) {
      case ResultContentType.plainText:
        primaryContent = _PlainTextBlock(
          text: ExecutionResultRenderer._extractPrimaryText(contentOnly),
        );
      case ResultContentType.structured:
      case ResultContentType.mixed:
        primaryContent = _StructuredBlock(
          parsedOutput: contentOnly,
          expanded: expanded,
        );
      case ResultContentType.markdown:
        primaryContent = _MarkdownLikeBlock(
          text: ExecutionResultRenderer._extractPrimaryText(contentOnly),
        );
      case ResultContentType.codeBlock:
        primaryContent = _CodeBlock(
          text: ExecutionResultRenderer._extractPrimaryText(contentOnly),
        );
      case ResultContentType.linkList:
        primaryContent = const SizedBox.shrink();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (contentOnly.isNotEmpty) primaryContent,
        if (contentOnly.isNotEmpty) const SizedBox(height: DS.spacing12),
        _LinkListBlock(parsedOutput: parsedOutput),
      ],
    );
  }
}

class _ArtifactTile extends StatelessWidget {
  const _ArtifactTile({required this.artifact});

  final Map<String, dynamic> artifact;

  IconData _iconForType(String type) {
    if (type.contains('image') || type.contains('screenshot')) {
      return Icons.photo_outlined;
    }
    if (type.contains('pdf')) {
      return Icons.picture_as_pdf_outlined;
    }
    return Icons.insert_drive_file_outlined;
  }

  bool _isImage(String type) =>
      type.contains('image') || type.contains('screenshot');

  @override
  Widget build(BuildContext context) {
    final type = artifact['type']?.toString().toLowerCase() ?? '';
    final url =
        artifact['url']?.toString() ??
        artifact['uri']?.toString() ??
        artifact['path']?.toString() ??
        '';
    final name =
        artifact['name']?.toString() ??
        artifact['filename']?.toString() ??
        artifact['path']?.toString() ??
        '附件';
    final size = artifact['size']?.toString();

    return Padding(
      padding: const EdgeInsets.only(bottom: DS.spacing10),
      child: InkWell(
        onTap: () {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('附件预览即将推出')),
          );
        },
        borderRadius: BorderRadius.circular(12),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.all(DS.spacing12),
          decoration: BoxDecoration(
            color: DS.surfacePrimary,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: DS.borderSubtle),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(_iconForType(type), color: DS.textSecondary, size: 18),
                  const SizedBox(width: DS.spacing8),
                  Expanded(
                    child: Text(
                      name,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: DS.bodySmall.copyWith(
                        color: DS.textPrimary,
                        fontWeight: DS.fontWeightMedium,
                      ),
                    ),
                  ),
                  if (size != null)
                    Text(
                      size,
                      style: DS.bodySmall.copyWith(color: DS.textSecondary),
                    ),
                ],
              ),
              if (_isImage(type) && url.isNotEmpty) ...[
                const SizedBox(height: DS.spacing10),
                ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: Image.network(
                    url,
                    height: 120,
                    width: double.infinity,
                    fit: BoxFit.cover,
                    errorBuilder: (_, __, ___) => Container(
                      height: 120,
                      color: DS.surfaceTertiary,
                      alignment: Alignment.center,
                      child: const Icon(Icons.broken_image_outlined),
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
