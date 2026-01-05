import 'package:sparkle/shared/entities/galaxy_model.dart';

/// Compact Edge Representation for Rendering
class CompactEdge {
  // For unique identification if needed

  const CompactEdge({
    required this.idHash,
    required this.sourceHash,
    required this.targetHash,
    required this.relationType,
    required this.strength,
    required this.bidirectional,
  });

  factory CompactEdge.fromModel(GalaxyEdgeModel edge) => CompactEdge(
        idHash: edge.id.hashCode,
        sourceHash: edge.sourceId.hashCode,
        targetHash: edge.targetId.hashCode,
        relationType: edge.relationType,
        strength: edge.strength,
        bidirectional: edge.bidirectional,
      );
  final int sourceHash;
  final int targetHash;
  final EdgeRelationType relationType;
  final double strength;
  final bool bidirectional;
  final int idHash;
}
