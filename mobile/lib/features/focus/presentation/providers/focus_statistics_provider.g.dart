// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'focus_statistics_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$localStatisticsRepoHash() =>
    r'211c2ef8cee5a9a8553192fd23be0f11c7a4f658';

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
String _$focusStatisticsHash() => r'f1068fd742e5a385f08920ea783b7e76e7e4ac4c';

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
