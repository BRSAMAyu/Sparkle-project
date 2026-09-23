// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'capsule_statistics_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$capsuleStatsRepositoryHash() =>
    r'b83ecd7380f888c593335ddfc85c2840c01299cc';

/// Provider for capsule statistics repository
///
/// Copied from [capsuleStatsRepository].
@ProviderFor(capsuleStatsRepository)
final capsuleStatsRepositoryProvider =
    AutoDisposeProvider<CapsuleStatsRepository>.internal(
  capsuleStatsRepository,
  name: r'capsuleStatsRepositoryProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$capsuleStatsRepositoryHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

typedef CapsuleStatsRepositoryRef
    = AutoDisposeProviderRef<CapsuleStatsRepository>;
String _$capsuleStatisticsHash() => r'ad61ae7883de53140faccaeff69dc1558d7622bb';

/// Provider for capsule statistics state
///
/// Copied from [CapsuleStatistics].
@ProviderFor(CapsuleStatistics)
final capsuleStatisticsProvider = AutoDisposeNotifierProvider<CapsuleStatistics,
    StatisticsState<CapsuleStatisticsData>>.internal(
  CapsuleStatistics.new,
  name: r'capsuleStatisticsProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$capsuleStatisticsHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

typedef _$CapsuleStatistics
    = AutoDisposeNotifier<StatisticsState<CapsuleStatisticsData>>;
// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member
