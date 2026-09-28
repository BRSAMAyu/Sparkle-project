import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/features/memory/data/context_receipt_models.dart';

/// V4-U03 · 「这次的理解」回执读面状态（唯一数据源 = I06
/// `GET /experience/context-receipts/latest`）。
///
/// 状态语义（诚实呈现，每态可失败）：
/// - [loading]：读面在途；
/// - [offline]：读失败（断网/5xx）——诚实「现在连不上」，绝不渲染为空数据；
/// - [modeGated]：mode=off/shadow → 读面 `receipt: null`（写先行读未开），
///   按档位如实说明；
/// - [empty]：mode=live 且服务端无回执（如本轮为确定性应答未发生选择）；
/// - [unsupported]：schema_version 非当前版本（读门 fail-closed 同语义）；
/// - [ready]：回执可用（candidates 缺失时 [ContextReceiptView.candidatesUnknown]
///   仍为 ready——unknown 是合法读态，不当空集渲染）。
enum ContextReceiptPhase { loading, offline, modeGated, empty, unsupported, ready }

@immutable
class ContextReceiptState {
  const ContextReceiptState({
    this.phase = ContextReceiptPhase.loading,
    this.mode = '',
    this.view,
    this.errorMessage,
  });

  final ContextReceiptPhase phase;

  /// 读面模式原样透传（off/shadow/live；modeGated 态的如实说明依据）。
  final String mode;

  /// ready 态的回执投影（其余态恒 null）。
  final ContextReceiptView? view;

  /// offline 态的用户语言错误（detail 已提取；无 detail 时为 null → 通用文案）。
  final String? errorMessage;

  ContextReceiptState copyWith({
    ContextReceiptPhase? phase,
    String? mode,
    ContextReceiptView? view,
    String? errorMessage,
  }) =>
      ContextReceiptState(
        phase: phase ?? this.phase,
        mode: mode ?? this.mode,
        view: view ?? this.view,
        errorMessage: errorMessage,
      );
}

class ContextReceiptNotifier extends StateNotifier<ContextReceiptState> {
  ContextReceiptNotifier(this._apiClient) : super(const ContextReceiptState());

  final ApiClient _apiClient;

  Future<void> load() async {
    state = state.copyWith(phase: ContextReceiptPhase.loading);
    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.experienceContextReceiptLatest,
      );
      final data = response.data ?? const <String, dynamic>{};
      if (!mounted) {
        return;
      }
      state = _project(data);
    } on DioException catch (error) {
      if (!mounted) {
        return;
      }
      state = state.copyWith(
        phase: ContextReceiptPhase.offline,
        errorMessage: _detailOf(error),
      );
    } catch (_) {
      if (!mounted) {
        return;
      }
      state = state.copyWith(phase: ContextReceiptPhase.offline);
    }
  }

  Future<void> refresh() => load();

  /// 读面响应 → 状态（纯投影：三态语义与 backend 端点逐字对齐）。
  ContextReceiptState _project(Map<String, dynamic> data) {
    final mode = data['mode']?.toString() ?? '';
    final receiptRaw = data['receipt'];
    final receipt = receiptRaw is Map ? Map<String, dynamic>.from(receiptRaw) : null;
    if (receipt == null) {
      // off/shadow（写先行读未开）与 live+无回执（本轮未发生选择）语义分立。
      final phase = mode == 'live' ? ContextReceiptPhase.empty : ContextReceiptPhase.modeGated;
      return ContextReceiptState(phase: phase, mode: mode);
    }
    final verifications = <Map<String, dynamic>>[
      if (data['source_verification'] is List)
        for (final entry
            in (data['source_verification'] as List).whereType<Map<dynamic, dynamic>>())
          Map<String, dynamic>.from(entry),
    ];
    final view = ContextReceiptView.tryParse(
      mode: mode,
      receipt: receipt,
      sourceVerifications: verifications,
      resolvedSelectedCount: (data['resolved_selected_count'] as num?)?.toInt() ?? 0,
    );
    if (view == null) {
      return ContextReceiptState(phase: ContextReceiptPhase.unsupported, mode: mode);
    }
    return ContextReceiptState(phase: ContextReceiptPhase.ready, mode: mode, view: view);
  }

  String? _detailOf(DioException error) {
    final data = error.response?.data;
    if (data is Map) {
      final detail = data['detail'];
      if (detail is String && detail.trim().isNotEmpty) {
        return detail.trim();
      }
    }
    return null;
  }
}

final contextReceiptProvider =
    StateNotifierProvider<ContextReceiptNotifier, ContextReceiptState>((ref) {
  final notifier = ContextReceiptNotifier(ref.watch(apiClientProvider));
  unawaited(notifier.load());
  return notifier;
});
