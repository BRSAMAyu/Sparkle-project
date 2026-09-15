// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'agent_statistics_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$agentStatsRepositoryHash() =>
    r'd4c28e02220695393f031d5a6861f967ef98cd4c';

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
String _$agentStatisticsHash() => r'6e63b2b6ea6ce8ccce49ffb463d9f04e2f744011';

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
