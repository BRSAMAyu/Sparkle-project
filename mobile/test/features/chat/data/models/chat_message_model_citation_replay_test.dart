import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';

/// V13 regression contract: chat history replay must rebuild the citation
/// strip and the source-summary tray from the gateway history payload.
///
/// Live turns carry citations via `meta` (→ rawMetadata) and the
/// `source_summary` widget (ChatCitation.listFromMessage reads both). The
/// history payload produced by the gateway must keep the same two shapes,
/// otherwise replay renders the "来源摘要" surface with no cards
/// (B-04: chat_citation_expanded_no_cards_1.png).
void main() {
  final citation = <String, dynamic>{
    'id': 'chunk-1',
    'title': '学习科学导论.pdf - 第2章 遗忘曲线',
    'content': '艾宾浩斯遗忘曲线表明，记忆在最初 24 小时内衰退最快……',
    'source_type': 'document',
    'score': 0.91,
    'file_id': 'file-abc',
    'page_number': 12,
    'chunk_index': 3,
    'section_title': '第2章 遗忘曲线',
  };

  Map<String, dynamic> historyItem({
    Map<String, dynamic>? meta,
    List<Map<String, dynamic>>? widgets,
  }) =>
      <String, dynamic>{
        'id': 'msg-1',
        'session_id': 'sess-cite',
        'conversation_id': 'sess-cite',
        'user_id': 'user-1',
        'role': 'assistant',
        'content': '根据文档，答案是 42。',
        'created_at': '2026-09-22T08:00:00.000Z',
        if (meta != null) 'meta': meta,
        if (widgets != null) 'widgets': widgets,
      };

  group('ChatMessageModel history replay citations', () {
    test('legacy history payload without citations renders no strip', () {
      // Documents the broken shape the gateway used to persist: latency-only
      // meta, no citation data anywhere — the strip must not render.
      final message = ChatMessageModel.fromJson(historyItem(
        meta: <String, dynamic>{'latency_ms': 42, 'total_duration_ms': 42},
      ));

      expect(message.citations, isEmpty);
    });

    test('meta.citations rebuilds the citation strip fields', () {
      final message = ChatMessageModel.fromJson(historyItem(
        meta: <String, dynamic>{
          'latency_ms': 42,
          'citations': [citation],
        },
      ));

      expect(message.citations, hasLength(1));
      final restored = message.citations.first;
      expect(restored.id, 'chunk-1');
      expect(restored.fileId, 'file-abc');
      expect(restored.title, '学习科学导论.pdf - 第2章 遗忘曲线');
      expect(
        restored.excerptText,
        '艾宾浩斯遗忘曲线表明，记忆在最初 24 小时内衰退最快……',
      );
      expect(restored.pageNumber, 12);
      expect(restored.chunkIndex, 3);
      expect(restored.sectionTitle, '第2章 遗忘曲线');
      expect(restored.locatorLabel, contains('p.12'));
    });

    test('source_summary widget rebuilds citations for the metadata tray', () {
      final message = ChatMessageModel.fromJson(historyItem(
        widgets: [
          <String, dynamic>{
            'type': 'source_summary',
            'data': <String, dynamic>{
              'citations_available': true,
              'reference_scope': 'file_only',
              'evidence_summary': '回答基于 1 个来源',
              'citations': [citation],
            },
          },
        ],
      ));

      expect(message.citations, hasLength(1));
      expect(message.citations.first.fileId, 'file-abc');
      expect(
        message.widgets?.any((widget) => widget.type == 'source_summary'),
        isTrue,
      );
    });

    test('meta and widget sources of the same citation deduplicate', () {
      // The gateway persists citations in BOTH places (parity with the live
      // turn assembly); the model must not double-render the chip.
      final message = ChatMessageModel.fromJson(historyItem(
        meta: <String, dynamic>{
          'citations': [citation],
        },
        widgets: [
          <String, dynamic>{
            'type': 'source_summary',
            'data': <String, dynamic>{
              'citations_available': true,
              'citations': [Map<String, dynamic>.from(citation)],
            },
          },
        ],
      ));

      expect(message.citations, hasLength(1));
    });
  });
}
