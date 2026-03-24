import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:shimmer/shimmer.dart';
import 'package:sparkle/core/design/design_system.dart';

class SparkleNetworkImage extends StatelessWidget {
  const SparkleNetworkImage({
    required this.imageUrl,
    super.key,
    this.width,
    this.height,
    this.fit = BoxFit.cover,
    this.borderRadius,
    this.aspectRatio,
    this.alignment = Alignment.center,
    this.imageBuilder,
    this.errorWidget,
    this.placeholder,
  });

  final String imageUrl;
  final double? width;
  final double? height;
  final BoxFit fit;
  final BorderRadius? borderRadius;
  final double? aspectRatio;
  final Alignment alignment;
  final Widget Function(BuildContext context, ImageProvider imageProvider)?
      imageBuilder;
  final Widget? errorWidget;
  final Widget? placeholder;

  @override
  Widget build(BuildContext context) {
    Widget child = CachedNetworkImage(
      imageUrl: imageUrl,
      fit: fit,
      width: width,
      height: height,
      alignment: alignment,
      fadeInDuration: const Duration(milliseconds: 300),
      imageBuilder: imageBuilder == null
          ? null
          : (context, imageProvider) => imageBuilder!(context, imageProvider),
      placeholder: (context, _) => placeholder ?? _buildPlaceholder(),
      errorWidget: (context, _, __) => errorWidget ?? _buildError(),
    );

    if (imageBuilder == null && borderRadius != null) {
      child = ClipRRect(
        borderRadius: borderRadius!,
        child: child,
      );
    }

    return child;
  }

  Widget _buildPlaceholder() {
    Widget shimmerChild = Container(
      width: width,
      height: height,
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: borderRadius,
      ),
    );

    if (aspectRatio != null && height == null) {
      shimmerChild = AspectRatio(
        aspectRatio: aspectRatio!,
        child: shimmerChild,
      );
    }

    return Shimmer.fromColors(
      baseColor: DS.surfaceSecondary,
      highlightColor: DS.surfaceOverlay,
      period: const Duration(milliseconds: 1200),
      child: shimmerChild,
    );
  }

  Widget _buildError() {
    Widget error = Container(
      width: width,
      height: height,
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: borderRadius,
      ),
      alignment: Alignment.center,
      child: Icon(
        Icons.broken_image_outlined,
        color: DS.textSecondary,
      ),
    );
    if (aspectRatio != null && height == null) {
      error = AspectRatio(
        aspectRatio: aspectRatio!,
        child: error,
      );
    }
    return error;
  }
}
