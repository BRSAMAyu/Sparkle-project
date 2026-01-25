// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'focus_statistics_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$localStatisticsRepoHash() =>
    r'd0b5e9289c0450955c3c5a905d9d8c4d5d49dc0d';

/// Local repository provider
///
/// Copied from [localStatisticsRepo].
@ProviderFor(localStatisticsRepo)
final localStatisticsRepoProvider =
    AutoDisposeProvider<FocusStatisticsRepository>.internal(
  localStatisticsRepo,
  name: r'localStatisticsRepoProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$localStatisticsRepoHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

typedef LocalStatisticsRepoRef
    = AutoDisposeProviderRef<FocusStatisticsRepository>;
String _$focusStatisticsHash() => r'cef2845e68e8d3be885eb61a4d8f9de59d657457';

/// Focus statistics provider
///
/// Copied from [FocusStatistics].
@ProviderFor(FocusStatistics)
final focusStatisticsProvider =
    AutoDisposeNotifierProvider<FocusStatistics, FocusStatisticsState>.internal(
  FocusStatistics.new,
  name: r'focusStatisticsProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$focusStatisticsHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

typedef _$FocusStatistics = AutoDisposeNotifier<FocusStatisticsState>;
// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member
