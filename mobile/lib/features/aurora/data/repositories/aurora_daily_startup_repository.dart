import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/aurora/data/models/aurora_comeback_context.dart';
import 'package:sparkle/features/aurora/data/models/aurora_daily_startup_message.dart';
import 'package:sparkle/shared/entities/task_model.dart';

final auroraDailyStartupRepositoryProvider =
    Provider<AuroraDailyStartupRepository>(
  (ref) => AuroraDailyStartupRepository(ref.read(apiClientProvider)),
);

class AuroraDailyStartupRepository {
  AuroraDailyStartupRepository(this._apiClient);

  static const String _latestCacheKey = 'aurora_daily_startup:last_overview';

  final ApiClient _apiClient;

  Future<AuroraDailyStartupMessage> getDailyStartup({
    required String planId,
  }) async {
    if (DemoDataService.isDemoMode) {
      return _buildDemoDailyStartup(planId);
    }

    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.auroraDailyStartup,
      queryParameters: {'plan_id': planId},
    );
    final payload = ApiResponseParser.unwrapMap(
      response.data,
      action: 'getDailyStartup',
    );
    final startup = AuroraDailyStartupMessage.fromJson(payload);
    await _cacheDailyStartup(planId, startup);
    return startup;
  }

  Future<AuroraCachedDailyStartup?> getCachedDailyStartup({
    String? planId,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    final normalizedPlanId = planId?.trim();
    final raw = normalizedPlanId == null || normalizedPlanId.isEmpty
        ? prefs.getString(_latestCacheKey)
        : prefs.getString(_cacheKey(normalizedPlanId)) ??
            prefs.getString(_latestCacheKey);
    if (raw == null || raw.isEmpty) {
      return null;
    }

    try {
      final decoded = jsonDecode(raw);
      if (decoded is! Map) {
        return null;
      }
      final payload = Map<String, dynamic>.from(decoded);
      final cachedPlanId = _firstNonEmpty([
        payload['plan_id'],
        normalizedPlanId,
      ]);
      if (cachedPlanId.isEmpty) {
        return null;
      }
      final message = AuroraDailyStartupMessage.fromJson(payload);
      if (message.message.trim().isEmpty) {
        return null;
      }
      return AuroraCachedDailyStartup(
        planId: cachedPlanId,
        message: message,
      );
    } catch (_) {
      return null;
    }
  }

  Future<AuroraComebackContext> getComebackContext() async {
    if (DemoDataService.isDemoMode) {
      return const AuroraComebackContext.empty();
    }

    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.auroraComebackContext,
    );
    final payload = ApiResponseParser.unwrapMap(
      response.data,
      action: 'getComebackContext',
    );
    if (payload.isEmpty) {
      return const AuroraComebackContext.empty();
    }
    return AuroraComebackContext.fromJson(payload);
  }

  AuroraDailyStartupMessage _buildDemoDailyStartup(String planId) {
    final demoService = DemoDataService();
    final plans = demoService.demoPlans;
    final plan = plans.firstWhere(
      (item) => item.id == planId,
      orElse: () => plans.firstWhere(
        (item) => item.isActive,
        orElse: () => plans.first,
      ),
    );
    final tasks = plan.tasks ?? const <TaskModel>[];
    final nextTask = tasks.isEmpty
        ? null
        : tasks.firstWhere(
            (task) => task.status != TaskStatus.completed,
            orElse: () => tasks.first,
          );
    final subject = _firstNonEmpty([
      plan.subject,
      plan.name,
      '今日学习',
    ]);
    final todayFocus = _firstNonEmpty([
      nextTask?.title,
      subject,
      '今日学习',
    ]);
    final estimatedMinutes =
        nextTask?.estimatedMinutes ?? plan.dailyAvailableMinutes;
    final message =
        '早上好，今天先把「$subject」推进一小步。核心任务是「$todayFocus」，预计 $estimatedMinutes 分钟。我们按你现在的计划节奏来，不急着换题，先完成这一段。准备好了吗？';
    return AuroraDailyStartupMessage(
      message: message,
      todayFocus: todayFocus,
      estimatedMinutes: estimatedMinutes,
      adjustmentReason: '根据当前 Demo 计划和下一项未完成任务生成。',
    );
  }

  Future<void> _cacheDailyStartup(
    String planId,
    AuroraDailyStartupMessage startup,
  ) async {
    final normalizedPlanId = planId.trim();
    if (normalizedPlanId.isEmpty || startup.message.trim().isEmpty) {
      return;
    }
    final prefs = await SharedPreferences.getInstance();
    final payload = jsonEncode({
      'plan_id': normalizedPlanId,
      'message': startup.message,
      'today_focus': startup.todayFocus,
      'estimated_minutes': startup.estimatedMinutes,
      'adjustment_reason': startup.adjustmentReason,
    });
    await prefs.setString(_cacheKey(normalizedPlanId), payload);
    await prefs.setString(_latestCacheKey, payload);
  }

  String _cacheKey(String planId) =>
      'aurora_daily_startup:last_overview:$planId';
}

class AuroraCachedDailyStartup {
  const AuroraCachedDailyStartup({
    required this.planId,
    required this.message,
  });

  final String planId;
  final AuroraDailyStartupMessage message;
}

String _firstNonEmpty(List<dynamic> values) {
  for (final value in values) {
    final text = value?.toString().trim();
    if (text != null && text.isNotEmpty) {
      return text;
    }
  }
  return '';
}
