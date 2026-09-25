import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/state/staged_loading.dart';

/// 加载状态枚举
enum LoadingState {
  idle, // 空闲
  loading, // 加载中
  success, // 成功
  error, // 错误
  empty, // 空数据
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

  /// 异步加载
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
  }) =>
      LoadingStateManager<T>()
        ..state = state ?? this.state
        ..data = data ?? this.data
        ..error = error ?? this.error
        ..errorObject = errorObject ?? this.errorObject;

  @override
  String toString() =>
      'LoadingStateManager(state: $state, hasData: ${data != null}, error: $error)';
}

final _i18n = I18nService.instance;

/// 便捷扩展方法
extension LoadingStateExtension<T> on LoadingStateManager<T> {
  /// 根据状态构建Widget
  ///
  /// U-06：默认分支收敛到统一状态体系——loading 默认渲染分阶加载
  /// （>500ms 升格 stage feedback，不再是无界裸 spinner）；error 默认
  /// 给人话文案 + 可选重试（传入 [onRetry] 即有下一步，不留死胡同）；
  /// empty 默认统一 EmptyState。
  Widget build({
    required Widget Function(T data) successBuilder,
    Widget Function()? loadingBuilder,
    Widget Function(String error)? errorBuilder,
    Widget Function()? emptyBuilder,
    Widget Function()? idleBuilder,
    VoidCallback? onRetry,
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
          final msg = _i18n.isChinese ? '数据为空' : 'Data is empty';
          return errorBuilder?.call(msg) ?? _defaultErrorWidget(msg);
        }
      case LoadingState.error:
        final msg = error ?? (_i18n.isChinese ? '未知错误' : 'Unknown error');
        return errorBuilder?.call(msg) ?? _defaultErrorWidget(msg, onRetry);
      case LoadingState.empty:
        return emptyBuilder?.call() ?? _defaultEmptyWidget();
    }
  }

  /// U-06：分阶加载默认渲染（替代原裸 CircularProgressIndicator——
  /// 加载悬死时用户至少看到阶段说明，而不是无解释的转圈）。
  Widget _defaultLoadingWidget() =>
      const StagedSurfaceLoader(compact: true, height: 96);

  Widget _defaultErrorWidget(String error, [VoidCallback? onRetry]) =>
      Builder(
        builder: (context) => Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CustomErrorWidget.inline(message: error, context: context),
            if (onRetry != null) ...[
              const SizedBox(height: DS.spacing8),
              TextButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh_rounded, size: 18),
                label: Text(context.l10n.retry),
              ),
            ],
          ],
        ),
      );

  Widget _defaultEmptyWidget() => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.inbox_outlined, size: 48, color: DS.brandPrimary),
            const SizedBox(height: DS.lg),
            Text(_i18n.isChinese ? '暂无数据' : 'No data yet'),
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
