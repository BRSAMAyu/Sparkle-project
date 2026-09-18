// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'focus_statistics_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$focusStatsRepositoryHash() =>
    r'2e6ac603aefe5be045f6152183d7bdb191fee0e9';

/// Provider for focus statistics repository
///
/// Copied from [focusStatsRepository].
@ProviderFor(focusStatsRepository)
final focusStatsRepositoryProvider =
    AutoDisposeProvider<FocusStatsRepository>.internal(
  focusStatsRepository,
  name: r'focusStatsRepositoryProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$focusStatsRepositoryHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

typedef FocusStatsRepositoryRef = AutoDisposeProviderRef<FocusStatsRepository>;
String _$focusStatisticsHash() => r'b8a0685d49dcf4b4e41ab5870d08067288a3e5d6';

/// Provider for focus statistics state
///
/// Copied from [FocusStatistics].
@ProviderFor(FocusStatistics)
final focusStatisticsProvider = AutoDisposeNotifierProvider<FocusStatistics,
    StatisticsState<FocusStatisticsData>>.internal(
  FocusStatistics.new,
  name: r'focusStatisticsProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$focusStatisticsHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

typedef _$FocusStatistics
    = AutoDisposeNotifier<StatisticsState<FocusStatisticsData>>;
// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member
