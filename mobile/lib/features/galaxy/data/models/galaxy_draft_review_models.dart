import 'package:flutter/foundation.dart';

@immutable
class GalaxyDraftSimilarity {
  const GalaxyDraftSimilarity({
    required this.existingNodeId,
    required this.existingNodeName,
    required this.similarityPercent,
  });

  factory GalaxyDraftSimilarity.fromJson(Map<String, dynamic> json) {
    final rawPercent = json['similarity_percent'] ??
        json['similarity'] ??
        json['score'] ??
        json['similarity_score'];
    final similarityValue = switch (rawPercent) {
      int value => value,
      double value when value <= 1 => (value * 100).round(),
      num value => value.round(),
      String value => _normalizePercent(double.tryParse(value)),
      _ => 0,
    };

    return GalaxyDraftSimilarity(
      existingNodeId: _readString(
        json,
        const ['existing_node_id', 'node_id', 'id'],
      ),
      existingNodeName: _readString(
        json,
        const ['existing_node_name', 'node_name', 'name'],
      ),
      similarityPercent: similarityValue < 0
          ? 0
          : similarityValue > 100
              ? 100
              : similarityValue,
    );
  }

  final String existingNodeId;
  final String existingNodeName;
  final int similarityPercent;
}

@immutable
class GalaxyDraftNode {
  const GalaxyDraftNode({
    required this.id,
    required this.proposedName,
    required this.proposedDescription,
    required this.excerpts,
    this.similarity,
  });

  factory GalaxyDraftNode.fromJson(Map<String, dynamic> json) {
    final rawExcerpts = json['sample_excerpts'] ??
        json['excerpts'] ??
        json['text_excerpts'] ??
        json['preview_excerpts'] ??
        json['source_quotes'];
    final excerpts = switch (rawExcerpts) {
      List<dynamic> values => values
          .map((value) => value?.toString().trim() ?? '')
          .where((value) => value.isNotEmpty)
          .take(3)
          .toList(growable: false),
      _ => const <String>[],
    };

    final rawSimilarity = json['similarity_candidate'] ??
        json['similarity'] ??
        json['similar_node'] ??
        json['existing_match'];

    return GalaxyDraftNode(
      id: _readString(json, const ['draft_id', 'id', 'node_id']),
      proposedName: _readString(
        json,
        const ['proposed_name', 'name', 'title'],
      ),
      proposedDescription: _readString(
        json,
        const ['proposed_description', 'description', 'summary'],
      ),
      excerpts: excerpts,
      similarity: rawSimilarity is Map<String, dynamic>
          ? GalaxyDraftSimilarity.fromJson(rawSimilarity)
          : null,
    );
  }

  final String id;
  final String proposedName;
  final String proposedDescription;
  final List<String> excerpts;
  final GalaxyDraftSimilarity? similarity;
}

@immutable
class GalaxyDraftBatch {
  const GalaxyDraftBatch({
    required this.id,
    required this.documentId,
    required this.documentName,
    required this.createdAt,
    required this.drafts,
  });

  factory GalaxyDraftBatch.fromJson(Map<String, dynamic> json) {
    final rawDrafts =
        json['drafts'] ?? json['nodes'] ?? json['items'] ?? json['entries'];
    final drafts = switch (rawDrafts) {
      List<dynamic> values => values
          .where((value) => value is Map)
          .map(
            (value) => GalaxyDraftNode.fromJson(
              Map<String, dynamic>.from(value as Map),
            ),
          )
          .toList(growable: false),
      _ => const <GalaxyDraftNode>[],
    };

    return GalaxyDraftBatch(
      id: _readString(
        json,
        const ['batch_id', 'id', 'draft_batch_id', 'document_id'],
      ),
      documentId: _readString(
        json,
        const ['document_id', 'file_id', 'source_file_id'],
      ),
      documentName: _readString(
        json,
        const ['document_name', 'file_name', 'filename', 'source_file_name'],
      ),
      createdAt: DateTime.tryParse(
            _readString(
              json,
              const ['created_at', 'updated_at', 'generated_at'],
            ),
          ) ??
          DateTime.now(),
      drafts: drafts,
    );
  }

  final String id;
  final String documentId;
  final String documentName;
  final DateTime createdAt;
  final List<GalaxyDraftNode> drafts;
}

enum GalaxyDraftDecision { approve, merge, reject }

@immutable
class ReviewedGalaxyDraftNode {
  const ReviewedGalaxyDraftNode({
    required this.draft,
    required this.decision,
    required this.finalName,
    required this.finalDescription,
  });

  final GalaxyDraftNode draft;
  final GalaxyDraftDecision decision;
  final String finalName;
  final String finalDescription;
}

@immutable
class GalaxyDraftReviewResult {
  const GalaxyDraftReviewResult({
    required this.batchId,
    required this.documentName,
    required this.totalDraftCount,
    required this.reviewedNodes,
  });

  final String batchId;
  final String documentName;
  final int totalDraftCount;
  final List<ReviewedGalaxyDraftNode> reviewedNodes;

  int get approvedCount => reviewedNodes
      .where((node) => node.decision == GalaxyDraftDecision.approve)
      .length;

  int get mergedCount => reviewedNodes
      .where((node) => node.decision == GalaxyDraftDecision.merge)
      .length;

  int get acceptedCount => reviewedNodes
      .where((node) => node.decision != GalaxyDraftDecision.reject)
      .length;

  int get rejectedCount => reviewedNodes
      .where((node) => node.decision == GalaxyDraftDecision.reject)
      .length;
}

int _normalizePercent(double? value) {
  if (value == null) {
    return 0;
  }
  return value <= 1 ? (value * 100).round() : value.round();
}

String _readString(Map<String, dynamic> json, List<String> keys) {
  for (final key in keys) {
    final value = json[key];
    final text = value?.toString().trim() ?? '';
    if (text.isNotEmpty) {
      return text;
    }
  }
  return '';
}
