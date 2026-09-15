import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/core/errors/user_facing_error.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// Skeleton variant for [SparkleAsyncBuilder] loading state.
enum SkeletonVariant {
  listItem,
  card,
  chatBubble,
}

/// Wraps Riverpod's [AsyncValue.when()] with consistent loading/empty/data/error
/// states using the project's design system components.
///
/// Never exposes raw `e.toString()` — uses [UserFacingError] for safe messages.
class SparkleAsyncBuilder<T> extends StatelessWidget {
  const SparkleAsyncBuilder({
    required this.state,
    required this.dataBuilder,
    super.key,
    this.skeletonVariant = SkeletonVariant.listItem,
    this.skeletonCount = 4,
    this.emptyStateType = EmptyStateType.general,
    this.emptyTitle,
    this.emptyDescription,
    this.emptyIcon,
    this.emptyActionText,
    this.onEmptyAction,
    this.onRetry,
  });

  /// The [AsyncValue] to react to.
  final AsyncValue<T> state;

  /// Builder for the data state.
  final Widget Function(BuildContext context, T data) dataBuilder;

  /// Which skeleton style to show during loading.
  final SkeletonVariant skeletonVariant;

  /// How many skeleton items to show.
  final int skeletonCount;

  /// Which empty state type to show when data is null-ish.
  final EmptyStateType emptyStateType;

  /// Optional overrides for empty state.
  final String? emptyTitle;
  final String? emptyDescription;
  final IconData? emptyIcon;
  final String? emptyActionText;
  final VoidCallback? onEmptyAction;

  /// Retry callback for error state.
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) => state.when(
        data: (T data) => dataBuilder(context, data),
        loading: _buildSkeleton,
        error: (Object error, StackTrace? _) => _buildError(context, error),
      );

  Widget _buildSkeleton() => switch (skeletonVariant) {
      SkeletonVariant.listItem => SparkleListSkeleton(count: skeletonCount),
      SkeletonVariant.card => Column(
          children: List.generate(
            skeletonCount,
            (_) => const Padding(
              padding: EdgeInsets.all(8),
              child: SparkleCardSkeleton(),
            ),
          ),
        ),
      SkeletonVariant.chatBubble => Column(
          children: List.generate(
            skeletonCount,
            (_) => const Padding(
              padding: EdgeInsets.all(8),
              child: SparkleChatBubbleSkeleton(),
            ),
          ),
        ),
    };

  Widget _buildError(BuildContext context, Object error) => CustomErrorWidget(
        message: UserFacingError.from(error),
        onRetry: onRetry,
        l10n: AppLocalizations.of(context),
      );
}

/// Extension of [SparkleAsyncBuilder] for list data that automatically shows
/// [EmptyState] when the list is empty.
class SparkleAsyncListBuilder<T> extends SparkleAsyncBuilder<List<T>> {
  const SparkleAsyncListBuilder({
    required super.state,
    required super.dataBuilder,
    super.key,
    super.skeletonVariant,
    super.skeletonCount,
    super.emptyStateType,
    super.emptyTitle,
    super.emptyDescription,
    super.emptyIcon,
    super.emptyActionText,
    super.onEmptyAction,
    super.onRetry,
  });

  @override
  Widget build(BuildContext context) => state.when(
        data: (List<T> data) {
          if (data.isEmpty) return _buildEmpty(context);
          return dataBuilder(context, data);
        },
        loading: _buildSkeleton,
        error: (Object error, StackTrace? _) => _buildError(context, error),
      );

  Widget _buildEmpty(BuildContext context) => EmptyState(
        type: emptyStateType,
        title: emptyTitle,
        description: emptyDescription,
        icon: emptyIcon,
        actionText: emptyActionText,
        onAction: onEmptyAction,
      );
}
