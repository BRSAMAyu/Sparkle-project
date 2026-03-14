import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/user/data/repositories/user_repository.dart';

final profileContextProvider =
    FutureProvider<Map<String, dynamic>>((ref) async {
  final repo = ref.watch(userRepositoryProvider);
  return repo.fetchProfileContext();
});
