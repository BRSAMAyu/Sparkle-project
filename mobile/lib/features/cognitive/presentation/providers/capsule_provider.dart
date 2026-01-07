import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/cognitive/data/models/curiosity_capsule_model.dart';
import 'package:sparkle/features/cognitive/data/repositories/capsule_repository.dart';

class CapsuleNotifier
    extends StateNotifier<AsyncValue<List<CuriosityCapsuleModel>>> {
  CapsuleNotifier(this._repository) : super(const AsyncValue.loading()) {
    fetchTodayCapsules();
  }
  final CapsuleRepository _repository;

  Future<void> fetchTodayCapsules() async {
    try {
      final capsules = await _repository.getTodayCapsules();
      state = AsyncValue.data(capsules);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> markAsRead(String id) async {
    try {
      await _repository.markAsRead(id);
      // Optimistic update
      state.whenData((capsules) {
        state = AsyncValue.data(
          capsules
              .map(
                (c) => c.id == id
                    ? CuriosityCapsuleModel(
                        id: c.id,
                        title: c.title,
                        content: c.content,
                        isRead: true,
                        createdAt: c.createdAt,
                        relatedSubject: c.relatedSubject,
                      )
                    : c,
              )
              .toList(),
        );
      });
    } catch (e) {
      // Revert or show error
    }
  }
}

final capsuleProvider = StateNotifierProvider<CapsuleNotifier,
        AsyncValue<List<CuriosityCapsuleModel>>>(
    (ref) => CapsuleNotifier(ref.watch(capsuleRepositoryProvider)),);
