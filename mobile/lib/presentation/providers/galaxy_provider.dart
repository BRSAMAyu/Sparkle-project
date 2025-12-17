import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/data/models/galaxy_model.dart';
import 'package:sparkle/data/repositories/galaxy_repository.dart';

class GalaxyState {
  final List<GalaxyNodeModel> nodes;
  final Map<String, Offset> nodePositions;
  final double userFlameIntensity;
  final bool isLoading;

  GalaxyState({
    this.nodes = const [],
    this.nodePositions = const {},
    this.userFlameIntensity = 0.0,
    this.isLoading = false,
  });

  GalaxyState copyWith({
    List<GalaxyNodeModel>? nodes,
    Map<String, Offset>? nodePositions,
    double? userFlameIntensity,
    bool? isLoading,
  }) {
    return GalaxyState(
      nodes: nodes ?? this.nodes,
      nodePositions: nodePositions ?? this.nodePositions,
      userFlameIntensity: userFlameIntensity ?? this.userFlameIntensity,
      isLoading: isLoading ?? this.isLoading,
    );
  }
}

final galaxyProvider = StateNotifierProvider<GalaxyNotifier, GalaxyState>((ref) {
  final repository = ref.watch(galaxyRepositoryProvider);
  return GalaxyNotifier(repository);
});

class GalaxyNotifier extends StateNotifier<GalaxyState> {
  final GalaxyRepository _repository;

  GalaxyNotifier(this._repository) : super(GalaxyState());

  Future<void> loadGalaxy() async {
    state = state.copyWith(isLoading: true);
    try {
      final response = await _repository.getGraph();
      final positions = _calculateLayout(response.nodes);
      state = state.copyWith(
        nodes: response.nodes,
        nodePositions: positions,
        userFlameIntensity: response.userFlameIntensity,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(isLoading: false);
      debugPrint('Error loading galaxy: $e');
    }
  }

  Future<void> sparkNode(String id) async {
    try {
      await _repository.sparkNode(id);
      // Refresh to get new status
      // Ideally we should just update local state to avoid full reload
      // But for MVP full reload is safer for consistency
      await loadGalaxy(); 
    } catch (e) {
      debugPrint('Error sparking node: $e');
    }
  }

  Map<String, Offset> _calculateLayout(List<GalaxyNodeModel> nodes) {
    final Map<String, Offset> positions = {};
    final Random random = Random(42); // Fixed seed for consistent layout across reloads if data is same

    // Sector angles (6 sectors)
    final sectorAngles = {
      SectorEnum.COSMOS: 0.0,
      SectorEnum.TECH: 60.0,
      SectorEnum.ART: 120.0,
      SectorEnum.CIVILIZATION: 180.0,
      SectorEnum.LIFE: 240.0,
      SectorEnum.WISDOM: 300.0,
      SectorEnum.VOID: 0.0,
    };

    double rad(double deg) => deg * pi / 180.0;

    // Sort: Roots first
    final sortedNodes = List<GalaxyNodeModel>.from(nodes);
    sortedNodes.sort((a, b) {
      if (a.parentId == null && b.parentId != null) return -1;
      if (a.parentId != null && b.parentId == null) return 1;
      return 0;
    });

    for (var node in sortedNodes) {
      if (node.parentId == null) {
        // Root placement
        final baseAngle = sectorAngles[node.sector] ?? 0.0;
        final angleNoise = (random.nextDouble() - 0.5) * 40.0; 
        final radius = 200.0 + random.nextDouble() * 100.0; 
        
        final theta = rad(baseAngle + angleNoise);
        positions[node.id] = Offset(radius * cos(theta), radius * sin(theta));
      } else {
        // Child placement
        final parentPos = positions[node.parentId];
        if (parentPos != null) {
          // Place somewhat outward from center relative to parent, but with randomness
          // Simple cluster:
          final angle = random.nextDouble() * 2 * pi;
          final dist = 60.0 + (5 - node.importance) * 10.0;
          
          positions[node.id] = parentPos + Offset(dist * cos(angle), dist * sin(angle));
        } else {
          // Orphan fallback
           positions[node.id] = const Offset(0, 0); 
        }
      }
    }
    
    return positions;
  }
}
