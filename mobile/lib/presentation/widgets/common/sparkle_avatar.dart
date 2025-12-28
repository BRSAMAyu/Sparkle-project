import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'dart:io';
import 'package:sparkle/data/models/user_model.dart';

class SparkleAvatar extends StatelessWidget {
  final String? url;
  final double radius;
  final String? fallbackText;
  final Color? backgroundColor;
  final AvatarStatus status;

  const SparkleAvatar({
    super.key,
    this.url,
    this.radius = 20,
    this.fallbackText,
    this.backgroundColor,
    this.status = AvatarStatus.approved,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    
    final effectiveBackgroundColor = backgroundColor ?? 
        (isDark ? DS.brandPrimary.shade800 : DS.brandPrimary.shade200);

    Widget avatar;
    if (url == null || url!.isEmpty) {
      avatar = _buildFallback(effectiveBackgroundColor);
    } else if (!url!.startsWith('http')) {
      avatar = CircleAvatar(
        radius: radius,
        backgroundColor: effectiveBackgroundColor,
        backgroundImage: FileImage(File(url!)),
      );
    } else if (url!.toLowerCase().contains('/svg') || url!.toLowerCase().endsWith('.svg')) {
      avatar = Container(
        width: radius * 2,
        height: radius * 2,
        decoration: BoxDecoration(
          color: effectiveBackgroundColor,
          shape: BoxShape.circle,
        ),
        clipBehavior: Clip.antiAlias,
        child: SvgPicture.network(
          url!,
          placeholderBuilder: (context) => _buildFallback(effectiveBackgroundColor),
          errorBuilder: (context, error, stackTrace) => _buildFallback(effectiveBackgroundColor),
        ),
      );
    } else {
      avatar = CachedNetworkImage(
        imageUrl: url!,
        imageBuilder: (context, imageProvider) => CircleAvatar(
          radius: radius,
          backgroundColor: effectiveBackgroundColor,
          backgroundImage: imageProvider,
        ),
        placeholder: (context, url) => _buildFallback(effectiveBackgroundColor),
        errorWidget: (context, url, error) => _buildFallback(effectiveBackgroundColor),
      );
    }

    if (status == AvatarStatus.pending) {
      return Stack(
        alignment: Alignment.center,
        children: [
          avatar,
          Container(
            width: radius * 2,
            height: radius * 2,
            decoration: BoxDecoration(
              color: DS.brandPrimary.withValues(alpha: 0.5),
              shape: BoxShape.circle,
            ),
            child: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  SizedBox(
                    width: radius * 0.6,
                    height: radius * 0.6,
                    child: const CircularProgressIndicator(
                      strokeWidth: 2,
                      valueColor: AlwaysStoppedAnimation<Color>(DS.brandPrimary70),
                    ),
                  ),
                  if (radius > 25) ...[
                    const SizedBox(height: DS.xs),
                    Text(
                      '审核中',
                      style: TextStyle(
                        color: DS.brandPrimary,
                        fontSize: radius * 0.3,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ],
      );
    }

    return avatar;
  }

  Widget _buildFallback(Color bgColor) {
    return CircleAvatar(
      radius: radius,
      backgroundColor: bgColor,
      child: Text(
        (fallbackText != null && fallbackText!.isNotEmpty) 
            ? fallbackText![0].toUpperCase() 
            : '?',
        style: TextStyle(
          color: DS.brandPrimary.shade600,
          fontSize: radius * 0.8,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }
}
