import 'package:flutter/material.dart';
import 'package:shimmer/shimmer.dart';
import 'package:sparkle/core/design/design_tokens.dart';

class LoadingIndicator extends StatelessWidget {
  final Widget? skeletonChild;
  final bool isLoading;

  const LoadingIndicator({
    super.key,
    this.skeletonChild,
    required this.isLoading,
  });

  @override
  Widget build(BuildContext context) {
    if (!isLoading) {
      return const SizedBox.shrink();
    }

    if (skeletonChild != null) {
      return Shimmer.fromColors(
        baseColor: AppDesignTokens.neutral200,
        highlightColor: AppDesignTokens.neutral50,
        child: skeletonChild!,
      );
    }

    // Default loading indicator if no skeletonChild is provided
    return Center(
      child: CircularProgressIndicator(
        valueColor: AlwaysStoppedAnimation<Color>(Theme.of(context).primaryColor),
      ),
    );
  }
}
