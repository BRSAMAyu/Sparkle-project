import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:sparkle/data/models/cognitive_fragment_model.dart';
import 'package:sparkle/data/repositories/sync_cognitive_repository.dart';
import 'package:sparkle/data/repositories/cognitive_repository.dart';
import 'package:sparkle/data/repositories/local_cognitive_repository.dart';

// Manual Mocks
class MockApiRepository extends Mock implements ApiCognitiveRepository {
  @override
  Future<CognitiveFragmentModel> createFragment(CognitiveFragmentCreate data) => super.noSuchMethod(
      Invocation.method(#createFragment, [data]),
      returnValue: Future.value(CognitiveFragmentModel(
        id: 'api_id',
        userId: 'user',
        sourceType: 'test',
        content: 'content',
        createdAt: DateTime.now(),
      )),
      returnValueForMissingStub: Future.value(CognitiveFragmentModel(
         id: 'api_id',
        userId: 'user',
        sourceType: 'test',
        content: 'content',
        createdAt: DateTime.now(),
      )),
    );
}

class MockLocalRepository extends Mock implements LocalCognitiveRepository {
  @override
  Future<void> queueFragment(CognitiveFragmentCreate data) => super.noSuchMethod(
      Invocation.method(#queueFragment, [data]),
      returnValue: Future<void>.value(),
      returnValueForMissingStub: Future<void>.value(),
    );
}

void main() {
  late SyncCognitiveRepository syncRepo;
  late MockApiRepository mockApi;
  late MockLocalRepository mockLocal;

  setUp(() {
    mockApi = MockApiRepository();
    mockLocal = MockLocalRepository();
    syncRepo = SyncCognitiveRepository(mockApi, mockLocal);
  });

  group('SyncCognitiveRepository', () {
    test('createFragment calls API and returns result on success', () async {
      final data = CognitiveFragmentCreate(content: 'test', sourceType: 'manual');
      
      when(mockApi.createFragment(data)).thenAnswer((_) async => CognitiveFragmentModel(
        id: 'real_api_id',
        userId: 'user',
        sourceType: 'manual',
        content: 'test',
        createdAt: DateTime.now(),
      ),);

      final result = await syncRepo.createFragment(data);

      expect(result.id, 'real_api_id');
      verify(mockApi.createFragment(data)).called(1);
      verifyNever(mockLocal.queueFragment(data));
    });

    test('createFragment falls back to Local on failure', () async {
      final data = CognitiveFragmentCreate(content: 'test', sourceType: 'manual');
      
      // Simulate Network Error
      when(mockApi.createFragment(data)).thenThrow(Exception('Network Error'));

      final result = await syncRepo.createFragment(data);

      // Should return local pending model
      expect(result.id, startsWith('local_'));
      expect(result.tags, contains('pending_sync'));
      
      // Verify local queue called
      verify(mockLocal.queueFragment(data)).called(1);
    });
  });
}
