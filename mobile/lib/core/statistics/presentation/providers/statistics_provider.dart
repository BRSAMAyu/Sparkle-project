import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:sparkle/core/statistics/domain/statistics_domain.dart';

part 'statistics_provider.g.dart';

/// State for statistics provider
class StatisticsState<T> {
  /// The current statistics data
  final T? data;

  /// Whether data is being loaded
  final bool isLoading;

  /// Whether there was an error
  final bool hasError;

  /// Error message if hasError is true
  final String? errorMessage;

  /// The last period that was loaded
  final StatisticsPeriod? lastPeriod;

  const StatisticsState({
    this.data,
    this.isLoading = false,
    this.hasError = false,
    this.errorMessage,
    this.lastPeriod,
  });

  /// Initial state
  const StatisticsState.initial()
      : data = null,
        isLoading = false,
        hasError = false,
        errorMessage = null,
        lastPeriod = null;

  /// Loading state
  const StatisticsState.loading({StatisticsPeriod? period})
      : data = null,
        isLoading = true,
        hasError = false,
        errorMessage = null,
        lastPeriod = period;

  /// Data loaded state
  StatisticsState withData(T newData, {StatisticsPeriod? newPeriod}) {
    return StatisticsState<T>(
      data: newData,
      isLoading: false,
      hasError: false,
      errorMessage: null,
      lastPeriod: newPeriod ?? lastPeriod,
    );
  }

  /// Error state
  StatisticsState withError(String newErrorMessage) {
    return StatisticsState<T>(
      data: data,
      isLoading: false,
      hasError: true,
      errorMessage: newErrorMessage,
      lastPeriod: lastPeriod,
    );
  }

  /// Copy with
  StatisticsState<T> copyWith({
    T? data,
    bool? isLoading,
    bool? hasError,
    String? errorMessage,
    StatisticsPeriod? lastPeriod,
  }) {
    return StatisticsState<T>(
      data: data ?? this.data,
      isLoading: isLoading ?? this.isLoading,
      hasError: hasError ?? this.hasError,
      errorMessage: errorMessage ?? this.errorMessage,
      lastPeriod: lastPeriod ?? this.lastPeriod,
    );
  }
}
