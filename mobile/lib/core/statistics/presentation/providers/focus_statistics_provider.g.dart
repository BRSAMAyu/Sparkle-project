// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'focus_statistics_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$focusStatsRepositoryHash() =>
    r'5ee698e9c0b56a19144c9397af178e7ef90dac8f';

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
String _$focusStatisticsHash() => r'aa2eb89f1ad16bdb76aa2ed0a21d0f47d633701b';

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
