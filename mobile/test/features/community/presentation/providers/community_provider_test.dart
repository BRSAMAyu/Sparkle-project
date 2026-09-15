import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/community/data/repositories/community_repository.dart';
import 'package:sparkle/features/community/presentation/providers/community_provider.dart';
import 'package:sparkle/shared/entities/user_brief.dart';

class _FakeRepository implements CommunityRepository {
  _FakeRepository({this.shouldThrow = false});

  bool shouldThrow;

  @override
  Future<void> updateStatus(UserStatus status) async {
    if (shouldThrow) {
      throw Exception('Network error');
    }
  }

  @override
  dynamic noSuchMethod(Invocation invocation) {
    throw UnimplementedError('${invocation.memberName} not implemented');
  }
}

void main() {
  group('CurrentUserStatusNotifier', () {
    test('updateStatus rolls back on API failure', () async {
      final repo = _FakeRepository(shouldThrow: true);
      final notifier = CurrentUserStatusNotifier(repo);

      expect(notifier.state, UserStatus.online);

      await notifier.updateStatus(UserStatus.invisible);

      // After failed API call, state should roll back to original
      expect(notifier.state, UserStatus.online);
    });

    test('updateStatus succeeds on successful API call', () async {
      final repo = _FakeRepository(shouldThrow: false);
      final notifier = CurrentUserStatusNotifier(repo);

      expect(notifier.state, UserStatus.online);

      await notifier.updateStatus(UserStatus.invisible);

      // After successful API call, state should be updated
      expect(notifier.state, UserStatus.invisible);
    });

    test('updateStatus rollback from non-default state', () async {
      final repo = _FakeRepository(shouldThrow: false);
      final notifier = CurrentUserStatusNotifier(repo);

      // First, set to a non-default state with successful call
      await notifier.updateStatus(UserStatus.offline);
      expect(notifier.state, UserStatus.offline);

      // Now try to update, but API will fail
      repo.shouldThrow = true;
      await notifier.updateStatus(UserStatus.invisible);

      // Should roll back to offline, not online
      expect(notifier.state, UserStatus.offline);
    });
  });
}
