import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:sparkle/data/repositories/cognitive_repository.dart';
import 'package:sparkle/data/repositories/local_cognitive_repository.dart';
import 'package:sparkle/data/repositories/sync_cognitive_repository.dart';
import 'package:sparkle/features/knowledge/data/models/behavior_pattern_model.dart';
import 'package:sparkle/features/knowledge/data/models/cognitive_fragment_model.dart';

// Manual Mocks
class MockApiCognitiveRepository extends Mock
    implements ApiCognitiveRepository {
  final List<CognitiveFragmentModel> mockFragments = [];

  @override
  Future<CognitiveFragmentModel> createFragment(
      CognitiveFragmentCreate data,) async {
    // Determine if we should fail based on content
    if (data.content.contains('fail_api')) {
      throw Exception('API Error');
    }

    final model = CognitiveFragmentModel(
      id: data.id ?? 'api_id_${DateTime.now().millisecondsSinceEpoch}',
      userId: 'user_1',
      sourceType: data.sourceType,
      content: data.content,
      taskId: data.taskId,
      createdAt: DateTime.now(),
      sentiment: 'neutral',
      tags: [],
    );
    mockFragments.add(model);
    return Future.value(model);
  }

  @override
  Future<List<CognitiveFragmentModel>> getFragments(
      {int limit = 20, int skip = 0,}) {
    if (mockFragments.any((f) => f.content.contains('fail_fetch'))) {
      throw Exception('Fetch Error');
    }
    return Future.value(mockFragments);
  }

  @override
  Future<List<BehaviorPatternModel>> getBehaviorPatterns() => Future.value([]);
}

class MockLocalCognitiveRepository extends Mock
    implements LocalCognitiveRepository {
  final List<Map<String, dynamic>> queue = [];

  @override
  Future<void> queueFragment(CognitiveFragmentCreate data) async {
    queue.add({
      'id': data.id,
      'content': data.content,
      'source_type': data.sourceType,
      'task_id': data.taskId,
    });
  }

  @override
  Future<List<Map<String, dynamic>>> getQueueRaw() =>
      Future.value(List.from(queue));

  @override
  Future<void> removeFromQueue(int index) async {
    if (index < queue.length) {
      queue.removeAt(index);
    }
  }
}

void main() {
  group('SyncCognitiveRepository Tests', () {
    late SyncCognitiveRepository repository;
    late MockApiCognitiveRepository mockApi;
    late MockLocalCognitiveRepository mockLocal;

    setUp(() {
      mockApi = MockApiCognitiveRepository();
      mockLocal = MockLocalCognitiveRepository();
      repository = SyncCognitiveRepository(mockApi, mockLocal);
    });

    test('createFragment: calls API when online', () async {
      final input = CognitiveFragmentCreate(
        content: 'Online note',
        sourceType: 'note',
      );

      final result = await repository.createFragment(input);

      // Verify API was called
      expect(result.content, 'Online note');
      expect(mockApi.mockFragments.length, 1);

      // Verify nothing queued locally
      expect(mockLocal.queue.isEmpty, true);
    });

    test('createFragment: saves locally when API fails', () async {
      final input = CognitiveFragmentCreate(
        content: 'fail_api note', // Triggers mock failure
        sourceType: 'note',
      );

      final result = await repository.createFragment(input);

      // Verify returned opportunistic model
      expect(result.content, 'fail_api note');
      expect(result.tags, contains('pending_sync'));

      // Verify queued locally
      expect(mockLocal.queue.length, 1);
      expect(mockLocal.queue.first['content'], 'fail_api note');
    });

    test('getFragments: merges API and Local data', () async {
      // Setup API data
      mockApi.mockFragments.add(
        CognitiveFragmentModel(
          id: 'api_1',
          userId: 'u1',
          sourceType: 'note',
          content: 'From API',
          createdAt: DateTime.now().subtract(const Duration(hours: 1)),
          sentiment: 'neutral',
          tags: [],
        ),
      );

      // Setup Local data
      mockLocal.queue.add({
        'id': 'local_1',
        'content': 'From Local',
        'source_type': 'note',
      });

      final result = await repository.getFragments();

      expect(result.length, 2);
      expect(result.any((f) => f.content == 'From API'), true);
      expect(result.any((f) => f.content == 'From Local'), true);
    });

    test('getFragments: handles API failure by returning local only', () async {
      // Setup Local data
      mockLocal.queue.add({
        'id': 'local_1',
        'content': 'From Local',
        'source_type': 'note',
      });

      // Force API fetch failure
      mockApi.mockFragments.add(
        CognitiveFragmentModel(
          id: 'fail',
          userId: 'u',
          sourceType: 'note',
          content: 'fail_fetch', // Triggers mock failure
          createdAt: DateTime.now(),
          sentiment: 'neutral',
          tags: [],
        ),
      );

      final result = await repository.getFragments();

      // Should only contain local items (and handle exception gracefully)
      expect(result.length, 1);
      expect(result.first.content, 'From Local');
    });

    test('syncPending: successfully syncs and removes from queue', () async {
      // Setup Local data
      mockLocal.queue.add({
        'id': 'local_1',
        'content': 'Pending Sync 1',
        'source_type': 'note',
      });
      mockLocal.queue.add({
        'id': 'local_2',
        'content': 'Pending Sync 2',
        'source_type': 'note',
      });

      await repository.syncPending();

      // Verify API received them
      expect(mockApi.mockFragments.length, 2);
      expect(mockApi.mockFragments.any((f) => f.content == 'Pending Sync 1'),
          true,);

      // Verify queue cleared
      expect(mockLocal.queue.isEmpty, true);
    });

    test('syncPending: stops on failure and keeps failed item in queue',
        () async {
      // Setup Local data
      mockLocal.queue.add({
        'id': 'local_1',
        'content': 'Pending Sync 1',
        'source_type': 'note',
      });
      mockLocal.queue.add({
        'id': 'local_2',
        'content': 'fail_api sync', // Will fail
        'source_type': 'note',
      });
      mockLocal.queue.add({
        'id': 'local_3',
        'content': 'Pending Sync 3',
        'source_type': 'note',
      });

      await repository.syncPending();

      // First item succeeded
      expect(mockApi.mockFragments.any((f) => f.content == 'Pending Sync 1'),
          true,);

      // Second failed, third shouldn't be attempted (break on error)
      expect(mockApi.mockFragments.any((f) => f.content == 'Pending Sync 3'),
          false,);

      // Queue should still contain item 2 and 3
      // Item 1 was removed (index 0).
      // Remaining: [fail_api sync, Pending Sync 3]
      expect(mockLocal.queue.length, 2);
      expect(mockLocal.queue.first['content'], 'fail_api sync');
    });
  });
}
