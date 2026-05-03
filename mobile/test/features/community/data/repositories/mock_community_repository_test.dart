import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/data/repositories/mock_community_repository.dart';

void main() {
  late MockCommunityRepository repo;

  setUp(() {
    repo = MockCommunityRepository();
  });

  group('Group management operations', () {
    test('kickMember reduces memberCount and clears myRole when self', () async {
      const groupId = 'group_sprint_001';

      // Verify initial state
      final before = await repo.getGroup(groupId);
      expect(before.memberCount, greaterThan(0));
      expect(before.myRole, isNotNull);

      // Kick the current user (self)
      await repo.kickMember(groupId, MockCommunityRepository.currentUserId);

      final after = await repo.getGroup(groupId);
      expect(after.memberCount, before.memberCount - 1);
      expect(after.myRole, isNull);
    });

    test('promoteMember sets myRole to admin when self', () async {
      const groupId = 'group_sprint_001';

      await repo.promoteMember(groupId, MockCommunityRepository.currentUserId);

      final after = await repo.getGroup(groupId);
      expect(after.myRole, GroupRole.admin);
    });

    test('demoteMember sets myRole to member when self', () async {
      const groupId = 'group_sprint_001';

      await repo.demoteMember(groupId, MockCommunityRepository.currentUserId);

      final after = await repo.getGroup(groupId);
      expect(after.myRole, GroupRole.member);
    });

    test('transferOwnership sets myRole to owner when self', () async {
      const groupId = 'group_sprint_001';

      await repo.transferOwnership(groupId, MockCommunityRepository.currentUserId);

      final after = await repo.getGroup(groupId);
      expect(after.myRole, GroupRole.owner);
    });

    test('transferOwnership sets myRole to member for non-self', () async {
      const groupId = 'group_sprint_001';

      await repo.transferOwnership(groupId, 'other_user_id');

      final after = await repo.getGroup(groupId);
      expect(after.myRole, GroupRole.member);
    });

    test('non-existent group does not throw', () async {
      // All management methods should handle non-existent groups gracefully
      await repo.kickMember('nonexistent', 'user');
      await repo.promoteMember('nonexistent', 'user');
      await repo.demoteMember('nonexistent', 'user');
      await repo.transferOwnership('nonexistent', 'user');
      // No exception thrown = pass
    });
  });
}
