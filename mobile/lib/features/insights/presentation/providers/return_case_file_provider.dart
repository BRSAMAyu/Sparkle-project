import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/insights/data/models/return_case_file.dart';
import 'package:sparkle/features/insights/data/repositories/return_case_file_repository.dart';

/// GOAL-011: Provider for the ReturnCaseFile shown to returning users.
///
/// Cache-first; the user can force a rebuild via the `refreshReturnCaseFile`
/// helper which invalidates the provider.
final returnCaseFileProvider = FutureProvider<ReturnCaseFile?>((ref) async {
  final repo = ref.watch(returnCaseFileRepositoryProvider);
  return repo.fetch();
});

final returnCaseFileForceRebuildProvider =
    FutureProvider.family<ReturnCaseFile?, bool>((ref, rebuild) async {
  final repo = ref.watch(returnCaseFileRepositoryProvider);
  return repo.fetch(rebuild: rebuild);
});

void refreshReturnCaseFile(WidgetRef ref) {
  ref.invalidate(returnCaseFileProvider);
}
