// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'capsule_statistics_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$capsuleStatsRepositoryHash() =>
    r'6e9311758a3b2a8d876edabca185933a0ac0ad65';

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
String _$capsuleStatisticsHash() => r'5f41c5de21a3b090c5d911f73f6c64dbe830c4bd';

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
