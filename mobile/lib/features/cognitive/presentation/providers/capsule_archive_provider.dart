import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/providers/persistent_state_notifier.dart';

class CapsuleArchiveState {
  const CapsuleArchiveState({
    required this.archivedIds,
  });

  factory CapsuleArchiveState.defaults() =>
      const CapsuleArchiveState(archivedIds: <String>[]);

  final List<String> archivedIds;

  CapsuleArchiveState copyWith({
    List<String>? archivedIds,
  }) =>
      CapsuleArchiveState(
        archivedIds: archivedIds ?? this.archivedIds,
      );

  Map<String, dynamic> toJson() => {
        'archivedIds': archivedIds,
      };

  static CapsuleArchiveState? fromJson(Map<String, dynamic> json) {
    try {
      return CapsuleArchiveState(
        archivedIds: (json['archivedIds'] as List<dynamic>? ?? const [])
            .map((item) => item.toString())
            .toList(),
      );
    } catch (_) {
      return null;
    }
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is CapsuleArchiveState &&
          runtimeType == other.runtimeType &&
          _listEquals(archivedIds, other.archivedIds);

  @override
  int get hashCode => Object.hashAll(archivedIds);

  static bool _listEquals(List<String> left, List<String> right) {
    if (left.length != right.length) {
      return false;
    }
    for (var index = 0; index < left.length; index++) {
      if (left[index] != right[index]) {
        return false;
      }
    }
    return true;
  }
}

class CapsuleArchiveNotifier
    extends PersistentStateNotifier<CapsuleArchiveState> {
  CapsuleArchiveNotifier(super.ref)
      : super(
          namespace: 'capsules',
          key: 'archive',
          defaultValue: CapsuleArchiveState.defaults(),
          toJson: (state) => state.toJson(),
          fromJson: CapsuleArchiveState.fromJson,
        );

  bool isArchived(String capsuleId) => state.archivedIds.contains(capsuleId);

  void archive(String capsuleId) {
    if (isArchived(capsuleId)) {
      return;
    }
    state = state.copyWith(
      archivedIds: [...state.archivedIds, capsuleId],
    );
  }

  void restore(String capsuleId) {
    if (!isArchived(capsuleId)) {
      return;
    }
    state = state.copyWith(
      archivedIds: state.archivedIds
          .where((id) => id != capsuleId)
          .toList(growable: false),
    );
  }

  void toggleArchive(String capsuleId) {
    if (isArchived(capsuleId)) {
      restore(capsuleId);
    } else {
      archive(capsuleId);
    }
  }
}

final capsuleArchiveProvider =
    StateNotifierProvider<CapsuleArchiveNotifier, CapsuleArchiveState>(
  CapsuleArchiveNotifier.new,
);
