// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'agent_statistics_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$agentStatsRepositoryHash() =>
    r'df4bc459f905125b1fc89d98863a9c7cfccf0818';

/// Provider for agent statistics repository
///
/// Copied from [agentStatsRepository].
@ProviderFor(agentStatsRepository)
final agentStatsRepositoryProvider =
    AutoDisposeProvider<AgentStatsRepository>.internal(
  agentStatsRepository,
  name: r'agentStatsRepositoryProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$agentStatsRepositoryHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

typedef AgentStatsRepositoryRef = AutoDisposeProviderRef<AgentStatsRepository>;
String _$agentStatisticsHash() => r'6892903504f410b59fbe7ea510e8d1c40ccf5144';

/// Provider for agent statistics state
///
/// Copied from [AgentStatistics].
@ProviderFor(AgentStatistics)
final agentStatisticsProvider = AutoDisposeNotifierProvider<AgentStatistics,
    StatisticsState<AgentStatisticsData>>.internal(
  AgentStatistics.new,
  name: r'agentStatisticsProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$agentStatisticsHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

typedef _$AgentStatistics
    = AutoDisposeNotifier<StatisticsState<AgentStatisticsData>>;
// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member
