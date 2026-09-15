import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/focus/data/services/candidate_feedback_service.dart';

class _StubDio implements Dio {
  bool postCalled = false;

  @override
  Future<Response<T>> post<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
    CancelToken? cancelToken,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    postCalled = true;
    throw UnimplementedError();
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  test('recordFeedback skips request when access token is unavailable', () async {
    final dio = _StubDio();
    final service = CandidateFeedbackService(
      dio,
      accessTokenGetter: () async => null,
    );

    await service.recordFeedback(
      candidateId: 'cand-1',
      actionType: 'resume_priority_task',
      feedbackType: 'impression',
    );

    expect(dio.postCalled, isFalse);
  });
}
