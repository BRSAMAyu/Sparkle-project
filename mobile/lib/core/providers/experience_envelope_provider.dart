import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/models/experience_envelope.dart';

final experienceEnvelopeProvider =
    StateNotifierProvider<ExperienceEnvelopeNotifier, ExperienceEnvelope>(
  (ref) => ExperienceEnvelopeNotifier(),
);

class ExperienceEnvelopeNotifier extends StateNotifier<ExperienceEnvelope> {
  ExperienceEnvelopeNotifier() : super(const ExperienceEnvelope());

  void updateFromMetadata(Map<String, dynamic>? metadata) {
    if (metadata == null || metadata.isEmpty) return;
    final envelope = ExperienceEnvelope.fromMetadata(metadata);
    if (envelope.isEmpty) return;
    state = state.isEmpty ? envelope : state.merge(envelope);
  }

  void clear() {
    state = const ExperienceEnvelope();
  }
}
