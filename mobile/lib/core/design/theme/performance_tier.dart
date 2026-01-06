/// Global performance tier for visual effects and motion.
///
/// UI must read this from theme/context; do not infer per-widget.
enum PerformanceTier { 
  ultra, 
  high, 
  medium, 
  low 
}

/// Single decision point for performance tier defaults.
PerformanceTier defaultPerformanceTier() => PerformanceTier.high;