// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'error_book_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$errorBookRepositoryHash() =>
    r'c94bc66a98f61ff461ea42fc9b90adf00c9c18fb';

/// ErrorBookRepository Provider
///
/// 提供 Repository 的单例实例
///
/// Copied from [errorBookRepository].
@ProviderFor(errorBookRepository)
final errorBookRepositoryProvider =
    AutoDisposeProvider<ErrorBookRepository>.internal(
  errorBookRepository,
  name: r'errorBookRepositoryProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$errorBookRepositoryHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

typedef ErrorBookRepositoryRef = AutoDisposeProviderRef<ErrorBookRepository>;
String _$errorListHash() => r'92a6d7652f9cddadea9c94739ac6557addf3d4a6';

/// Copied from Dart SDK
class _SystemHash {
  _SystemHash._();

  static int combine(int hash, int value) {
    // ignore: parameter_assignments
    hash = 0x1fffffff & (hash + value);
    // ignore: parameter_assignments
    hash = 0x1fffffff & (hash + ((0x0007ffff & hash) << 10));
    return hash ^ (hash >> 6);
  }

  static int finish(int hash) {
    // ignore: parameter_assignments
    hash = 0x1fffffff & (hash + ((0x03ffffff & hash) << 3));
    // ignore: parameter_assignments
    hash = hash ^ (hash >> 11);
    return 0x1fffffff & (hash + ((0x00003fff & hash) << 15));
  }
}

/// 错题列表 Provider（支持参数化查询）
///
/// 使用方式：
/// ```dart
/// final listState = ref.watch(errorListProvider(
///   ErrorListQuery(subject: 'math', needReview: true)
/// ));
/// ```
///
/// Copied from [errorList].
@ProviderFor(errorList)
const errorListProvider = ErrorListFamily();

/// 错题列表 Provider（支持参数化查询）
///
/// 使用方式：
/// ```dart
/// final listState = ref.watch(errorListProvider(
///   ErrorListQuery(subject: 'math', needReview: true)
/// ));
/// ```
///
/// Copied from [errorList].
class ErrorListFamily extends Family<AsyncValue<ErrorListResponse>> {
  /// 错题列表 Provider（支持参数化查询）
  ///
  /// 使用方式：
  /// ```dart
  /// final listState = ref.watch(errorListProvider(
  ///   ErrorListQuery(subject: 'math', needReview: true)
  /// ));
  /// ```
  ///
  /// Copied from [errorList].
  const ErrorListFamily();

  /// 错题列表 Provider（支持参数化查询）
  ///
  /// 使用方式：
  /// ```dart
  /// final listState = ref.watch(errorListProvider(
  ///   ErrorListQuery(subject: 'math', needReview: true)
  /// ));
  /// ```
  ///
  /// Copied from [errorList].
  ErrorListProvider call(
    ErrorListQuery query,
  ) {
    return ErrorListProvider(
      query,
    );
  }

  @override
  ErrorListProvider getProviderOverride(
    covariant ErrorListProvider provider,
  ) {
    return call(
      provider.query,
    );
  }

  static const Iterable<ProviderOrFamily>? _dependencies = null;

  @override
  Iterable<ProviderOrFamily>? get dependencies => _dependencies;

  static const Iterable<ProviderOrFamily>? _allTransitiveDependencies = null;

  @override
  Iterable<ProviderOrFamily>? get allTransitiveDependencies =>
      _allTransitiveDependencies;

  @override
  String? get name => r'errorListProvider';
}

/// 错题列表 Provider（支持参数化查询）
///
/// 使用方式：
/// ```dart
/// final listState = ref.watch(errorListProvider(
///   ErrorListQuery(subject: 'math', needReview: true)
/// ));
/// ```
///
/// Copied from [errorList].
class ErrorListProvider extends AutoDisposeFutureProvider<ErrorListResponse> {
  /// 错题列表 Provider（支持参数化查询）
  ///
  /// 使用方式：
  /// ```dart
  /// final listState = ref.watch(errorListProvider(
  ///   ErrorListQuery(subject: 'math', needReview: true)
  /// ));
  /// ```
  ///
  /// Copied from [errorList].
  ErrorListProvider(
    ErrorListQuery query,
  ) : this._internal(
          (ref) => errorList(
            ref as ErrorListRef,
            query,
          ),
          from: errorListProvider,
          name: r'errorListProvider',
          debugGetCreateSourceHash:
              const bool.fromEnvironment('dart.vm.product')
                  ? null
                  : _$errorListHash,
          dependencies: ErrorListFamily._dependencies,
          allTransitiveDependencies: ErrorListFamily._allTransitiveDependencies,
          query: query,
        );

  ErrorListProvider._internal(
    super._createNotifier, {
    required super.name,
    required super.dependencies,
    required super.allTransitiveDependencies,
    required super.debugGetCreateSourceHash,
    required super.from,
    required this.query,
  }) : super.internal();

  final ErrorListQuery query;

  @override
  Override overrideWith(
    FutureOr<ErrorListResponse> Function(ErrorListRef provider) create,
  ) {
    return ProviderOverride(
      origin: this,
      override: ErrorListProvider._internal(
        (ref) => create(ref as ErrorListRef),
        from: from,
        name: null,
        dependencies: null,
        allTransitiveDependencies: null,
        debugGetCreateSourceHash: null,
        query: query,
      ),
    );
  }

  @override
  AutoDisposeFutureProviderElement<ErrorListResponse> createElement() {
    return _ErrorListProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is ErrorListProvider && other.query == query;
  }

  @override
  int get hashCode {
    var hash = _SystemHash.combine(0, runtimeType.hashCode);
    hash = _SystemHash.combine(hash, query.hashCode);

    return _SystemHash.finish(hash);
  }
}

mixin ErrorListRef on AutoDisposeFutureProviderRef<ErrorListResponse> {
  /// The parameter `query` of this provider.
  ErrorListQuery get query;
}

class _ErrorListProviderElement
    extends AutoDisposeFutureProviderElement<ErrorListResponse>
    with ErrorListRef {
  _ErrorListProviderElement(super.provider);

  @override
  ErrorListQuery get query => (origin as ErrorListProvider).query;
}

String _$errorDetailHash() => r'0954a29e360e8ed5f8d534d008db077b703d5789';

/// 错题详情 Provider
///
/// 根据错题 ID 获取详细信息（包含 AI 分析）
///
/// Copied from [errorDetail].
@ProviderFor(errorDetail)
const errorDetailProvider = ErrorDetailFamily();

/// 错题详情 Provider
///
/// 根据错题 ID 获取详细信息（包含 AI 分析）
///
/// Copied from [errorDetail].
class ErrorDetailFamily extends Family<AsyncValue<ErrorRecord>> {
  /// 错题详情 Provider
  ///
  /// 根据错题 ID 获取详细信息（包含 AI 分析）
  ///
  /// Copied from [errorDetail].
  const ErrorDetailFamily();

  /// 错题详情 Provider
  ///
  /// 根据错题 ID 获取详细信息（包含 AI 分析）
  ///
  /// Copied from [errorDetail].
  ErrorDetailProvider call(
    String errorId,
  ) {
    return ErrorDetailProvider(
      errorId,
    );
  }

  @override
  ErrorDetailProvider getProviderOverride(
    covariant ErrorDetailProvider provider,
  ) {
    return call(
      provider.errorId,
    );
  }

  static const Iterable<ProviderOrFamily>? _dependencies = null;

  @override
  Iterable<ProviderOrFamily>? get dependencies => _dependencies;

  static const Iterable<ProviderOrFamily>? _allTransitiveDependencies = null;

  @override
  Iterable<ProviderOrFamily>? get allTransitiveDependencies =>
      _allTransitiveDependencies;

  @override
  String? get name => r'errorDetailProvider';
}

/// 错题详情 Provider
///
/// 根据错题 ID 获取详细信息（包含 AI 分析）
///
/// Copied from [errorDetail].
class ErrorDetailProvider extends AutoDisposeFutureProvider<ErrorRecord> {
  /// 错题详情 Provider
  ///
  /// 根据错题 ID 获取详细信息（包含 AI 分析）
  ///
  /// Copied from [errorDetail].
  ErrorDetailProvider(
    String errorId,
  ) : this._internal(
          (ref) => errorDetail(
            ref as ErrorDetailRef,
            errorId,
          ),
          from: errorDetailProvider,
          name: r'errorDetailProvider',
          debugGetCreateSourceHash:
              const bool.fromEnvironment('dart.vm.product')
                  ? null
                  : _$errorDetailHash,
          dependencies: ErrorDetailFamily._dependencies,
          allTransitiveDependencies:
              ErrorDetailFamily._allTransitiveDependencies,
          errorId: errorId,
        );

  ErrorDetailProvider._internal(
    super._createNotifier, {
    required super.name,
    required super.dependencies,
    required super.allTransitiveDependencies,
    required super.debugGetCreateSourceHash,
    required super.from,
    required this.errorId,
  }) : super.internal();

  final String errorId;

  @override
  Override overrideWith(
    FutureOr<ErrorRecord> Function(ErrorDetailRef provider) create,
  ) {
    return ProviderOverride(
      origin: this,
      override: ErrorDetailProvider._internal(
        (ref) => create(ref as ErrorDetailRef),
        from: from,
        name: null,
        dependencies: null,
        allTransitiveDependencies: null,
        debugGetCreateSourceHash: null,
        errorId: errorId,
      ),
    );
  }

  @override
  AutoDisposeFutureProviderElement<ErrorRecord> createElement() {
    return _ErrorDetailProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is ErrorDetailProvider && other.errorId == errorId;
  }

  @override
  int get hashCode {
    var hash = _SystemHash.combine(0, runtimeType.hashCode);
    hash = _SystemHash.combine(hash, errorId.hashCode);

    return _SystemHash.finish(hash);
  }
}

mixin ErrorDetailRef on AutoDisposeFutureProviderRef<ErrorRecord> {
  /// The parameter `errorId` of this provider.
  String get errorId;
}

class _ErrorDetailProviderElement
    extends AutoDisposeFutureProviderElement<ErrorRecord> with ErrorDetailRef {
  _ErrorDetailProviderElement(super.provider);

  @override
  String get errorId => (origin as ErrorDetailProvider).errorId;
}

String _$todayReviewListHash() => r'e527a5b0538e58c4853187022bc383fa9b22b8e7';

/// 今日待复习列表 Provider
///
/// 自动获取需要在今天复习的错题
///
/// Copied from [todayReviewList].
@ProviderFor(todayReviewList)
final todayReviewListProvider =
    AutoDisposeFutureProvider<List<ErrorRecord>>.internal(
  todayReviewList,
  name: r'todayReviewListProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$todayReviewListHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

typedef TodayReviewListRef = AutoDisposeFutureProviderRef<List<ErrorRecord>>;
String _$errorStatsHash() => r'fbcc38c6ef8256327c44b1a25aa230d42a25e02e';

/// 错题统计数据 Provider
///
/// Copied from [errorStats].
@ProviderFor(errorStats)
final errorStatsProvider = AutoDisposeFutureProvider<ReviewStats>.internal(
  errorStats,
  name: r'errorStatsProvider',
  debugGetCreateSourceHash:
      const bool.fromEnvironment('dart.vm.product') ? null : _$errorStatsHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

typedef ErrorStatsRef = AutoDisposeFutureProviderRef<ReviewStats>;
String _$errorOperationsHash() => r'22c9d4b7ec8864bb553b8d17c03a5e4662f99e23';

/// 错题操作 Notifier
///
/// 提供错题的增删改操作（带状态管理）
/// 使用示例：
/// ```dart
/// await ref.read(errorOperationsProvider.notifier).createError(...);
/// ```
///
/// Copied from [ErrorOperations].
@ProviderFor(ErrorOperations)
final errorOperationsProvider =
    AutoDisposeNotifierProvider<ErrorOperations, ErrorOperationState>.internal(
  ErrorOperations.new,
  name: r'errorOperationsProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$errorOperationsHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

typedef _$ErrorOperations = AutoDisposeNotifier<ErrorOperationState>;
String _$errorFilterHash() => r'c0cc217ef00d3a37fa409e17df0c2b5a800139e5';

/// 错题筛选器 Provider
///
/// 管理列表页的筛选状态（科目、章节、只看需复习等）
///
/// Copied from [ErrorFilter].
@ProviderFor(ErrorFilter)
final errorFilterProvider =
    AutoDisposeNotifierProvider<ErrorFilter, ErrorFilterState>.internal(
  ErrorFilter.new,
  name: r'errorFilterProvider',
  debugGetCreateSourceHash:
      const bool.fromEnvironment('dart.vm.product') ? null : _$errorFilterHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

typedef _$ErrorFilter = AutoDisposeNotifier<ErrorFilterState>;
// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member
