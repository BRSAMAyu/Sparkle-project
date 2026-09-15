import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';

class ExecutionPreferenceRecommendation {
  const ExecutionPreferenceRecommendation({
    required this.recommendedMode,
    required this.reason,
    this.targetEnv,
    this.confidence = 0,
  });

  factory ExecutionPreferenceRecommendation.fromJson(
    Map<String, dynamic> json,
  ) =>
      ExecutionPreferenceRecommendation(
        recommendedMode: json['recommended_mode']?.toString() ?? 'balanced',
        reason: json['reason']?.toString() ?? '',
        targetEnv: json['target_env']?.toString(),
        confidence: (json['confidence'] as num?)?.toDouble() ?? 0,
      );

  final String recommendedMode;
  final String reason;
  final String? targetEnv;
  final double confidence;
}

class OpenClawExecutionBudget {
  const OpenClawExecutionBudget({
    this.dailyTokenLimit,
    this.monthlyTokenLimit,
    this.dailyUsed = 0,
    this.monthlyUsed = 0,
    this.resetDate,
    this.monthBucket,
  });

  factory OpenClawExecutionBudget.fromJson(Map<String, dynamic> json) =>
      OpenClawExecutionBudget(
        dailyTokenLimit: (json['daily_token_limit'] as num?)?.toInt(),
        monthlyTokenLimit: (json['monthly_token_limit'] as num?)?.toInt(),
        dailyUsed: (json['daily_used'] as num?)?.toInt() ?? 0,
        monthlyUsed: (json['monthly_used'] as num?)?.toInt() ?? 0,
        resetDate: json['reset_date']?.toString(),
        monthBucket: json['month_bucket']?.toString(),
      );

  final int? dailyTokenLimit;
  final int? monthlyTokenLimit;
  final int dailyUsed;
  final int monthlyUsed;
  final String? resetDate;
  final String? monthBucket;

  Map<String, dynamic> toJson() => {
        'daily_token_limit': dailyTokenLimit,
        'monthly_token_limit': monthlyTokenLimit,
        'daily_used': dailyUsed,
        'monthly_used': monthlyUsed,
        'reset_date': resetDate,
        'month_bucket': monthBucket,
      };

  OpenClawExecutionBudget copyWith({
    int? dailyTokenLimit,
    int? monthlyTokenLimit,
    int? dailyUsed,
    int? monthlyUsed,
    String? resetDate,
    String? monthBucket,
  }) =>
      OpenClawExecutionBudget(
        dailyTokenLimit: dailyTokenLimit ?? this.dailyTokenLimit,
        monthlyTokenLimit: monthlyTokenLimit ?? this.monthlyTokenLimit,
        dailyUsed: dailyUsed ?? this.dailyUsed,
        monthlyUsed: monthlyUsed ?? this.monthlyUsed,
        resetDate: resetDate ?? this.resetDate,
        monthBucket: monthBucket ?? this.monthBucket,
      );
}

class OpenClawExecutionPreferences {
  const OpenClawExecutionPreferences({
    this.mode = 'balanced',
    this.customRules = const <String, String>{},
    this.nodeAffinity = const <String, String>{},
    this.notificationLevel = 'essential',
    this.autoExtendTimeout = true,
    this.trustAutoUpgrade = true,
    this.executionBudget = const OpenClawExecutionBudget(),
    this.summary = '',
    this.recommendations = const <ExecutionPreferenceRecommendation>[],
  });

  factory OpenClawExecutionPreferences.fromJson(Map<String, dynamic> json) {
    final customRulesRaw = json['custom_rules'];
    final customRules = <String, String>{};
    if (customRulesRaw is Map) {
      for (final entry in customRulesRaw.entries) {
        customRules[entry.key.toString()] = entry.value.toString();
      }
    }
    final nodeAffinityRaw = json['node_affinity'];
    final nodeAffinity = <String, String>{};
    if (nodeAffinityRaw is Map) {
      for (final entry in nodeAffinityRaw.entries) {
        nodeAffinity[entry.key.toString()] = entry.value.toString();
      }
    }
    final recommendationsRaw = json['recommendations'];
    return OpenClawExecutionPreferences(
      mode: json['mode']?.toString() ?? 'balanced',
      customRules: customRules,
      nodeAffinity: nodeAffinity,
      notificationLevel: json['notification_level']?.toString() ?? 'essential',
      autoExtendTimeout: json['auto_extend_timeout'] as bool? ?? true,
      trustAutoUpgrade: json['trust_auto_upgrade'] as bool? ?? true,
      executionBudget: json['execution_budget'] is Map
          ? OpenClawExecutionBudget.fromJson(
              Map<String, dynamic>.from(json['execution_budget'] as Map),
            )
          : const OpenClawExecutionBudget(),
      summary: json['summary']?.toString() ?? '',
      recommendations: recommendationsRaw is List
          ? recommendationsRaw
              .whereType<Map<dynamic, dynamic>>()
              .map(
                (item) => ExecutionPreferenceRecommendation.fromJson(
                  Map<String, dynamic>.from(item),
                ),
              )
              .toList()
          : const <ExecutionPreferenceRecommendation>[],
    );
  }

  final String mode;
  final Map<String, String> customRules;
  final Map<String, String> nodeAffinity;
  final String notificationLevel;
  final bool autoExtendTimeout;
  final bool trustAutoUpgrade;
  final OpenClawExecutionBudget executionBudget;
  final String summary;
  final List<ExecutionPreferenceRecommendation> recommendations;

  Map<String, dynamic> toJson() => {
        'mode': mode,
        'custom_rules': customRules,
        'node_affinity': nodeAffinity,
        'notification_level': notificationLevel,
        'auto_extend_timeout': autoExtendTimeout,
        'trust_auto_upgrade': trustAutoUpgrade,
        'execution_budget': executionBudget.toJson(),
      };

  OpenClawExecutionPreferences copyWith({
    String? mode,
    Map<String, String>? customRules,
    Map<String, String>? nodeAffinity,
    String? notificationLevel,
    bool? autoExtendTimeout,
    bool? trustAutoUpgrade,
    OpenClawExecutionBudget? executionBudget,
    String? summary,
    List<ExecutionPreferenceRecommendation>? recommendations,
  }) =>
      OpenClawExecutionPreferences(
        mode: mode ?? this.mode,
        customRules: customRules ?? this.customRules,
        nodeAffinity: nodeAffinity ?? this.nodeAffinity,
        notificationLevel: notificationLevel ?? this.notificationLevel,
        autoExtendTimeout: autoExtendTimeout ?? this.autoExtendTimeout,
        trustAutoUpgrade: trustAutoUpgrade ?? this.trustAutoUpgrade,
        executionBudget: executionBudget ?? this.executionBudget,
        summary: summary ?? this.summary,
        recommendations: recommendations ?? this.recommendations,
      );
}

class OpenClawExecutionPreferencesService extends ChangeNotifier {
  OpenClawExecutionPreferencesService({
    required Future<Map<String, dynamic>> Function() loader,
    required Future<Map<String, dynamic>> Function(Map<String, dynamic> payload)
        saver,
  })  : _loader = loader,
        _saver = saver;

  final Future<Map<String, dynamic>> Function() _loader;
  final Future<Map<String, dynamic>> Function(Map<String, dynamic> payload)
      _saver;

  OpenClawExecutionPreferences _preferences =
      const OpenClawExecutionPreferences();
  bool _isLoading = false;
  bool _isSaving = false;
  String? _error;

  OpenClawExecutionPreferences get preferences => _preferences;
  bool get isLoading => _isLoading;
  bool get isSaving => _isSaving;
  String? get error => _error;

  Future<void> initialize() async {
    if (_isLoading) {
      return;
    }
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      final payload = await _loader();
      _preferences = OpenClawExecutionPreferences.fromJson(payload);
    } catch (error) {
      _error = error.toString();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> savePreferences(OpenClawExecutionPreferences next) async {
    if (_isSaving) {
      return false;
    }
    _isSaving = true;
    _error = null;
    notifyListeners();
    try {
      final payload = await _saver(next.toJson());
      _preferences = OpenClawExecutionPreferences.fromJson(payload);
      return true;
    } catch (error) {
      _error = error.toString();
      return false;
    } finally {
      _isSaving = false;
      notifyListeners();
    }
  }
}

final openClawExecutionPreferencesProvider =
    ChangeNotifierProvider<OpenClawExecutionPreferencesService>((ref) {
  final apiClient = ref.read(apiClientProvider);
  final service = OpenClawExecutionPreferencesService(
    loader: () async {
      final response = await apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.executionPreferences,
      );
      return ApiResponseParser.unwrapMap(
        response.data,
        action: 'executionPreferences',
      );
    },
    saver: (payload) async {
      final response = await apiClient.put<Map<String, dynamic>>(
        ApiEndpoints.executionPreferences,
        data: payload,
      );
      return ApiResponseParser.unwrapMap(
        response.data,
        action: 'saveExecutionPreferences',
      );
    },
  );
  unawaited(service.initialize());
  return service;
});
