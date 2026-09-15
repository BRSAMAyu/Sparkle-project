import 'package:flutter/material.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';
import 'package:sparkle/shared/models/compact_knowledge_node.dart';

@immutable
class GalaxyViewportState {
  const GalaxyViewportState({
    required this.matrix,
    required this.absoluteViewport,
    required this.relativeViewport,
    required this.scale,
    required this.viewportBucket,
    required this.zoomBucket,
  });

  final Matrix4 matrix;
  final Rect absoluteViewport;
  final Rect relativeViewport;
  final double scale;
  final int viewportBucket;
  final int zoomBucket;
}

@immutable
class GalaxyRenderBudget {
  const GalaxyRenderBudget({
    required this.maxNodes,
    required this.maxEdges,
    required this.maxLabels,
    required this.showLabels,
    required this.showTags,
    required this.showEdgeGlow,
    required this.labelScaleThreshold,
  });

  final int maxNodes;
  final int maxEdges;
  final int maxLabels;
  final bool showLabels;
  final bool showTags;
  final bool showEdgeGlow;
  final double labelScaleThreshold;
}

@immutable
class GalaxyHitTarget {
  const GalaxyHitTarget({
    required this.nodeId,
    required this.nodeHash,
    required this.position,
    required this.radius,
  });

  final String nodeId;
  final int nodeHash;
  final Offset position;
  final double radius;
}

@immutable
class GalaxySceneSnapshot {
  const GalaxySceneSnapshot({
    required this.viewport,
    required this.budget,
    required this.nodes,
    required this.edges,
    required this.hitTargets,
    required this.selectedNodeIdHash,
    required this.highlightedNodeIdHashes,
    required this.expandedEdgeNodeIdHashes,
    required this.highlightRevision,
  });

  final GalaxyViewportState viewport;
  final GalaxyRenderBudget budget;
  final List<CompactKnowledgeNode> nodes;
  final List<GalaxyEdgeModel> edges;
  final List<GalaxyHitTarget> hitTargets;
  final int? selectedNodeIdHash;
  final Set<int> highlightedNodeIdHashes;
  final Set<int> expandedEdgeNodeIdHashes;
  final int highlightRevision;
}
