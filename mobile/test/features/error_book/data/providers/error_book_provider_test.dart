import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/error_book/data/models/error_record.dart';
import 'package:sparkle/features/error_book/data/providers/error_book_provider.dart';
import 'package:sparkle/features/error_book/data/repositories/error_book_repository.dart';
import 'package:sparkle/features/galaxy/presentation/providers/galaxy_provider.dart';

void main() {
  group('ErrorOperations galaxy refresh', () {
    late ProviderContainer container;

    setUp(() {
      container = ProviderContainer(
        overrides: [
          errorBookRepositoryProvider.overrideWithValue(
            _FakeErrorBookRepository(),
          ),
        ],
      );
    });

    tearDown(() {
      container.dispose();
    });

    test('submitReview increments galaxyRefreshTriggerProvider', () async {
      final triggerBefore =
          container.read(galaxyRefreshTriggerProvider);

      await container
          .read(errorOperationsProvider.notifier)
          .submitReview(
            errorId: 'err-1',
            performance: 'remembered',
          );

      final triggerAfter =
          container.read(galaxyRefreshTriggerProvider);

      expect(triggerAfter, triggerBefore + 1);
    });

    test('createError increments galaxyRefreshTriggerProvider', () async {
      final triggerBefore =
          container.read(galaxyRefreshTriggerProvider);

      await container
          .read(errorOperationsProvider.notifier)
          .createError(
            questionText: 'What is 2+2?',
            subject: 'math',
          );

      final triggerAfter =
          container.read(galaxyRefreshTriggerProvider);

      expect(triggerAfter, triggerBefore + 1);
    });
  });
}

class _FakeErrorBookRepository extends ErrorBookRepository {
  _FakeErrorBookRepository() : super(Dio());

  @override
  Future<ErrorRecord> submitReview({
    required String errorId,
    required String performance,
    int? timeSpentSeconds,
  }) async =>
      ErrorRecord(
        id: errorId,
        questionText: 'test',
        userAnswer: '',
        correctAnswer: '',
        subject: 'math',
        masteryLevel: 0.5,
        reviewCount: 1,
        createdAt: DateTime(2026, 4, 26),
        updatedAt: DateTime(2026, 4, 26),
      );

  @override
  Future<ErrorRecord> createError({
    required String questionText,
    required String subject,
    String? userAnswer,
    String? correctAnswer,
    String? chapter,
    String? questionImageUrl,
  }) async =>
      ErrorRecord(
        id: 'new-err',
        questionText: questionText,
        userAnswer: userAnswer ?? '',
        correctAnswer: correctAnswer ?? '',
        subject: subject,
        masteryLevel: 0,
        reviewCount: 0,
        createdAt: DateTime(2026, 4, 26),
        updatedAt: DateTime(2026, 4, 26),
      );
}
