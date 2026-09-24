import 'dart:async';
import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/galaxy/data/repositories/galaxy_draft_repository.dart';

/// WT328 C 线 F-1：星图草稿 mock 回落必须切除。
/// kDebugMode 在 flutter test 下为 true —— 以下断言证明 debug 构建不再把
/// 空结果/网络错误偷换成硬编码「OS.pdf」假草稿。
class _CannedJsonAdapter implements HttpClientAdapter {
  _CannedJsonAdapter(this.payload);

  final Object? payload;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    await Future<void>.delayed(Duration.zero);
    return ResponseBody.fromString(
      jsonEncode(payload),
      200,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

class _ServerErrorAdapter implements HttpClientAdapter {
  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    await Future<void>.delayed(Duration.zero);
    return ResponseBody.fromString(
      jsonEncode({'detail': 'galaxy drafts unavailable'}),
      500,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

void main() {
  group('GalaxyDraftRepository.listPendingDrafts', () {
    test('empty drafts from backend surface as an empty list in debug builds',
        () async {
      expect(kDebugMode, isTrue,
          reason: '该回归只在 debug 构建有意义，测试环境必须处于 kDebugMode',);
      final dio = Dio()
        ..options.baseUrl = 'http://localhost'
        ..httpClientAdapter = _CannedJsonAdapter({'drafts': <dynamic>[]});
      final repository = GalaxyDraftRepository(dio);

      final batches = await repository.listPendingDrafts();

      expect(batches, isEmpty,
          reason: '空草稿必须走真实空态，绝不允许 mock「OS.pdf 5 颗知识星」回落',);
    });

    test('backend error surfaces as an exception instead of mock batches',
        () async {
      final dio = Dio()
        ..options.baseUrl = 'http://localhost'
        ..httpClientAdapter = _ServerErrorAdapter();
      final repository = GalaxyDraftRepository(dio);

      await expectLater(
        repository.listPendingDrafts(),
        throwsException,
      );
    });

    test('explicit demoMode:true is still allowed to serve mock batches',
        () async {
      final dio = Dio()..options.baseUrl = 'http://localhost';
      final repository = GalaxyDraftRepository(dio, demoMode: true);

      final batches = await repository.listPendingDrafts();

      expect(batches, isNotEmpty,
          reason: '演示数据只允许经显式 demoMode 构造参数进入',);
    });
  });
}
