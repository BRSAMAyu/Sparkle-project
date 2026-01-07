import 'package:sparkle/features/cognitive/data/models/behavior_pattern_model.dart';
import 'package:sparkle/features/cognitive/data/models/cognitive_fragment_model.dart';

/// Abstract Interface for Cognitive Repository
/// Allows switching between Mock, API, and Offline implementations.
abstract class ICognitiveRepository {
  /// Create a new cognitive fragment
  Future<CognitiveFragmentModel> createFragment(CognitiveFragmentCreate data);

  /// Get list of fragments
  Future<List<CognitiveFragmentModel>> getFragments(
      {int limit = 20, int skip = 0,});

  /// Get behavior patterns
  Future<List<BehaviorPatternModel>> getBehaviorPatterns();
}
