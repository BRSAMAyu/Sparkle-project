import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/data/models/plan_model.dart';
import 'package:sparkle/data/models/task_model.dart';

class PlanRepository {
  final ApiClient _apiClient;

  PlanRepository(this._apiClient);

  T _handleDioError<T>(DioException e, String functionName) {
    final errorMessage = e.response?.data?['detail'] ?? 'An unknown error occurred in $functionName';
    throw Exception(errorMessage);
  }

  Future<List<PlanModel>> getPlans({PlanType? type, bool? isActive}) async {
    try {
      final query = <String, dynamic>{};
      if (type != null) query['type'] = type.name;
      if (isActive != null) query['is_active'] = isActive;

      final response = await _apiClient.get(ApiEndpoints.plans, queryParameters: query);
      final List<dynamic> data = response.data;
      return data.map((json) => PlanModel.fromJson(json)).toList();
    } on DioException catch (e) {
      return _handleDioError(e, 'getPlans');
    }
  }

  Future<PlanModel> getPlan(String id) async {
    try {
      final response = await _apiClient.get(ApiEndpoints.plan(id));
      return PlanModel.fromJson(response.data);
    } on DioException catch (e) {
      return _handleDioError(e, 'getPlan');
    }
  }

  Future<List<PlanModel>> getActivePlans() async {
    return getPlans(isActive: true);
  }

  Future<PlanModel> createPlan(PlanCreate plan) async {
    try {
      final response = await _apiClient.post(ApiEndpoints.plans, data: plan.toJson());
      return PlanModel.fromJson(response.data);
    } on DioException catch (e) {
      return _handleDioError(e, 'createPlan');
    }
  }

  Future<PlanModel> updatePlan(String id, PlanUpdate plan) async {
    try {
      final response = await _apiClient.put(ApiEndpoints.plan(id), data: plan.toJson());
      return PlanModel.fromJson(response.data);
    } on DioException catch (e) {
      return _handleDioError(e, 'updatePlan');
    }
  }

  Future<void> deletePlan(String id) async {
    try {
      await _apiClient.delete(ApiEndpoints.plan(id));
    } on DioException catch (e) {
      return _handleDioError(e, 'deletePlan');
    }
  }
  
  Future<PlanModel> _updateActivation(String id, bool activate) async {
     try {
       final planUpdate = PlanUpdate(isActive: activate);
      final response = await _apiClient.put(ApiEndpoints.plan(id), data: planUpdate.toJson());
      return PlanModel.fromJson(response.data);
    } on DioException catch (e) {
      return _handleDioError(e, activate ? 'activatePlan' : 'deactivatePlan');
    }
  }

  Future<PlanModel> activatePlan(String id) async {
    return _updateActivation(id, true);
  }

  Future<PlanModel> deactivatePlan(String id) async {
    return _updateActivation(id, false);
  }

  Future<List<TaskModel>> generateTasks(String planId, {int count = 5}) async {
    try {
      final response = await _apiClient.post(ApiEndpoints.generateTasks(planId), data: {'count': count});
       final List<dynamic> data = response.data;
      return data.map((json) => TaskModel.fromJson(json)).toList();
    } on DioException catch (e) {
      return _handleDioError(e, 'generateTasks');
    }
  }
}

final planRepositoryProvider = Provider<PlanRepository>((ref) {
  return PlanRepository(ref.watch(apiClientProvider));
});
