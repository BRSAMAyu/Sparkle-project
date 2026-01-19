enum EdgeStateSource {
  passiveSignals,
  fallback,
}

class UserEdgeState {

  UserEdgeState({
    required this.isForeground,
    required this.sessionDuration,
    required this.focusScore,
    required this.switchingRate,
    required this.updatedAt,
    required this.source,
    Map<String, dynamic>? debug,
  }) : debug = debug ?? {};
  final bool isForeground;
  final Duration sessionDuration;
  final double focusScore;
  final double switchingRate;
  final DateTime updatedAt;
  final EdgeStateSource source;
  final Map<String, dynamic> debug;

  UserEdgeState copyWith({
    bool? isForeground,
    Duration? sessionDuration,
    double? focusScore,
    double? switchingRate,
    DateTime? updatedAt,
    EdgeStateSource? source,
    Map<String, dynamic>? debug,
  }) => UserEdgeState(
      isForeground: isForeground ?? this.isForeground,
      sessionDuration: sessionDuration ?? this.sessionDuration,
      focusScore: focusScore ?? this.focusScore,
      switchingRate: switchingRate ?? this.switchingRate,
      updatedAt: updatedAt ?? this.updatedAt,
      source: source ?? this.source,
      debug: debug ?? this.debug,
    );
}
