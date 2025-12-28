import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';

/// 加载状态枚举
enum LoadingState {
  idle,     // 空闲
  loading,  // 加载中
  success,  // 成功
  error,    // 错误
  empty,    // 空数据
}

/// 加载状态管理器
class LoadingStateManager<T> {
  LoadingState state = LoadingState.idle;
  T? data;
  String? error;
  Object? errorObject;

  /// 开始加载
  void startLoading() {
    state = LoadingState.loading;
    error = null;
    errorObject = null;
  }

  /// 加载成功
  void success(T newData) {
    state = LoadingState.success;
    data = newData;
    error = null;
    errorObject = null;
  }

  /// 加载错误
  void errorOccurred(String errorMessage, [Object? errorObj]) {
    state = LoadingState.error;
    error = errorMessage;
    errorObject = errorObj;
    data = null;
  }

  /// 空数据
  void empty() {
    state = LoadingState.empty;
    data = null;
    error = null;
    errorObject = null;
  }

  /// 重置状态
  void reset() {
    state = LoadingState.idle;
    data = null;
    error = null;
    errorObject = null;
  }

  /// 检查是否正在加载
  bool get isLoading => state == LoadingState.loading;

  /// 检查是否成功
  bool get isSuccess => state == LoadingState.success;

  /// 检查是否错误
  bool get isError => state == LoadingState.error;

  /// 检查是否为空
  bool get isEmpty => state == LoadingState.empty;

  /// 检查是否空闲
  bool get isIdle => state == LoadingState.idle;

  /// 检查是否有数据
  bool get hasData => data != null;

  /// 异步加载数据
  Future<void> load(Future<T> Function() loader) async {
    startLoading();
    try {
      final result = await loader();
      success(result);
    } catch (e) {
      errorOccurred(e.toString(), e);
    }
  }

  /// 复制状态
  LoadingStateManager<T> copyWith({
    LoadingState? state,
    T? data,
    String? error,
    Object? errorObject,
  }) => LoadingStateManager<T>()
      ..state = state ?? this.state
      ..data = data ?? this.data
      ..error = error ?? this.error
      ..errorObject = errorObject ?? this.errorObject;

  @override
  String toString() => 'LoadingStateManager(state: $state, hasData: ${data != null}, error: $error)';
}

/// 便捷扩展方法
extension LoadingStateExtension<T> on LoadingStateManager<T> {
  /// 根据状态构建Widget
  Widget build({
    required Widget Function(T data) successBuilder,
    Widget Function()? loadingBuilder,
    Widget Function(String error)? errorBuilder,
    Widget Function()? emptyBuilder,
    Widget Function()? idleBuilder,
  }) {
    switch (state) {
      case LoadingState.idle:
        return idleBuilder?.call() ?? const SizedBox();
      case LoadingState.loading:
        return loadingBuilder?.call() ?? _defaultLoadingWidget();
      case LoadingState.success:
        if (data != null) {
          return successBuilder(data as T);
        } else {
          return errorBuilder?.call('数据为空') ?? _defaultErrorWidget('数据为空');
        }
      case LoadingState.error:
        return errorBuilder?.call(error ?? '未知错误') ??
            _defaultErrorWidget(error ?? '未知错误');
      case LoadingState.empty:
        return emptyBuilder?.call() ?? _defaultEmptyWidget();
    }
  }

  Widget _defaultLoadingWidget() => const Center(
      child: CircularProgressIndicator(),
    );

  Widget _defaultErrorWidget(String error) => Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.error_outline, size: 48, color: DS.error),
          const SizedBox(height: DS.lg),
          Text('加载失败: $error', textAlign: TextAlign.center),
        ],
      ),
    );

  Widget _defaultEmptyWidget() => const Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.inbox_outlined, size: 48, color: DS.brandPrimary),
          SizedBox(height: DS.lg),
          Text('暂无数据'),
        ],
      ),
    );
}

/// 用于Riverpod的状态包装器
class LoadingStateNotifier<T> extends StateNotifier<LoadingStateManager<T>> {
  LoadingStateNotifier() : super(LoadingStateManager<T>());

  /// 异步加载
  Future<void> load(Future<T> Function() loader) async {
    state = state..startLoading();
    try {
      final result = await loader();
      state = state..success(result);
    } catch (e) {
      state = state..errorOccurred(e.toString(), e);
    }
  }

  /// 手动设置成功
  void setSuccess(T data) {
    state = state..success(data);
  }

  /// 手动设置错误
  void setError(String error, [Object? errorObj]) {
    state = state..errorOccurred(error, errorObj);
  }

  /// 手动设置空状态
  void setEmpty() {
    state = state..empty();
  }

  /// 重置状态
  void resetState() {
    state = state..reset();
  }
}