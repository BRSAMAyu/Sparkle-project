import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/presentation/providers/galaxy_provider.dart';
import 'package:sparkle/presentation/widgets/galaxy/flame_core.dart';
import 'package:sparkle/presentation/widgets/galaxy/star_map_painter.dart';

class GalaxyScreen extends ConsumerStatefulWidget {
  const GalaxyScreen({super.key});

  @override
  ConsumerState<GalaxyScreen> createState() => _GalaxyScreenState();
}

class _GalaxyScreenState extends ConsumerState<GalaxyScreen> {
  final TransformationController _transformationController = TransformationController();

  @override
  void initState() {
    super.initState();
    
    // Defer initial centering until we know screen size (in build) or post frame
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final size = MediaQuery.of(context).size;
      // Center the 4000x4000 canvas
      final x = -2000.0 + size.width / 2;
      final y = -2000.0 + size.height / 2;
      _transformationController.value = Matrix4.identity()..translate(x, y);
      
      ref.read(galaxyProvider.notifier).loadGalaxy();
    });
  }

  @override
  void dispose() {
    _transformationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final galaxyState = ref.watch(galaxyProvider);

    return Scaffold(
      backgroundColor: Colors.black, // Deep space
      body: Stack(
        children: [
          // 1. Star Map (Interactive)
          InteractiveViewer(
            transformationController: _transformationController,
            boundaryMargin: const EdgeInsets.all(2000), // Huge scroll area
            minScale: 0.1,
            maxScale: 3.0,
            constrained: false, // Infinite canvas
            child: SizedBox(
              width: 4000,
              height: 4000,
              child: AnimatedBuilder(
                animation: _transformationController,
                builder: (context, child) {
                   final scale = _transformationController.value.getMaxScaleOnAxis();
                   return CustomPaint(
                    painter: StarMapPainter(
                      nodes: galaxyState.nodes,
                      positions: _centerPositions(galaxyState.nodePositions, 2000, 2000),
                      scale: scale,
                    ),
                  );
                },
              ),
            ),
          ),
          
          // 2. Flame Core (Fixed at screen center)
          Center(
            child: IgnorePointer( // Let touches pass through to InteractiveViewer
              child: FlameCore(
                intensity: galaxyState.userFlameIntensity,
              ),
            ),
          ),
          
          // 3. UI Overlays (Back button)
          Positioned(
            top: 40,
            left: 20,
            child: IconButton(
              icon: const Icon(Icons.arrow_back, color: Colors.white),
              onPressed: () => Navigator.of(context).pop(),
            ),
          ),

          // 4. Debug: Spark Button (Bottom Right)
          Positioned(
            bottom: 40,
            right: 20,
            child: FloatingActionButton(
              mini: true,
              backgroundColor: Colors.white24,
              child: const Icon(Icons.bolt),
              onPressed: () {
                // Pick a random node to spark for demo
                if (galaxyState.nodes.isNotEmpty) {
                  final node = galaxyState.nodes[DateTime.now().millisecond % galaxyState.nodes.length];
                  ref.read(galaxyProvider.notifier).sparkNode(node.id);
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('Sparking ${node.name}!')),
                  );
                }
              },
            ),
          ),
          
          if (galaxyState.isLoading)
            const Center(child: CircularProgressIndicator()),
        ],
      ),
    );
  }

  // Helper to shift logical (0,0) to center of the 4000x4000 canvas
  Map<String, Offset> _centerPositions(Map<String, Offset> raw, double cx, double cy) {
    return raw.map((key, value) => MapEntry(key, value + Offset(cx, cy)));
  }
}
