import 'dart:async';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:sparkle/features/document/models/document_cleaning_model.dart';
import 'package:sparkle/features/document/repositories/document_repository.dart';

part 'document_controller.g.dart';

@riverpod
class DocumentController extends _$DocumentController {
  Timer? _timer;

  @override
  AsyncValue<CleaningTaskStatus?> build() {
    // Initial state is null (no task started)
    return const AsyncValue.data(null);
  }

  Future<void> startCleaning(File file, {bool enableOcr = true}) async {
    state = const AsyncValue.loading();
    try {
      final repo = ref.read(documentRepositoryProvider);
      final taskId = await repo.uploadAndClean(file, enableOcr: enableOcr);

      // Start polling immediately with a dummy initial status
      state = const AsyncValue.data(
        CleaningTaskStatus(
          status: 'queued',
          percent: 0,
          message: 'Uploading...',
        ),
      );

      _startPolling(taskId);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  void _startPolling(String taskId) {
    _timer?.cancel();
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) async {
      try {
        final repo = ref.read(documentRepositoryProvider);
        final status = await repo.getTaskStatus(taskId);

        state = AsyncValue.data(status);

        if (status.status == 'completed' ||
            status.status == 'failed' ||
            status.status == 'error') {
          timer.cancel();
        }
      } catch (e) {
        // If polling fails (network glitch), don't fail immediately, just log/wait
        // Unless it's a 404, which means task lost
        if (kDebugMode) {
          debugPrint('Polling error: $e');
        }
      }
    });
  }

  void reset() {
    _timer?.cancel();
    state = const AsyncValue.data(null);
  }
}
