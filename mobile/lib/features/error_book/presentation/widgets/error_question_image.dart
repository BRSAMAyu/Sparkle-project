import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sparkle_network_image.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/error_book/data/models/question_image_reference.dart';
import 'package:sparkle/features/file/data/repositories/file_repository.dart';

class ErrorQuestionImage extends ConsumerWidget {
  const ErrorQuestionImage({
    required this.imageReference,
    super.key,
    this.height,
    this.width,
    this.fit = BoxFit.cover,
    this.borderRadius,
  });

  final String imageReference;
  final double? height;
  final double? width;
  final BoxFit fit;
  final BorderRadius? borderRadius;

  Future<String> _resolveImageUrl(WidgetRef ref) async {
    final fileId = parseSparkleFileId(imageReference);
    if (fileId == null) {
      return imageReference;
    }

    final presignedUrl =
        await ref.read(fileRepositoryProvider).getDownloadUrl(fileId);
    return presignedUrl.url;
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (imageReference.trim().isEmpty) {
      return const SizedBox.shrink();
    }

    return FutureBuilder<String>(
      future: _resolveImageUrl(ref),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return Container(
            width: width,
            height: height ?? 220,
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surfaceContainerHighest,
              borderRadius: borderRadius ?? BorderRadius.circular(12),
            ),
            alignment: Alignment.center,
            child: const CircularProgressIndicator(),
          );
        }

        final resolvedUrl = snapshot.data;
        if (snapshot.hasError || resolvedUrl == null || resolvedUrl.isEmpty) {
          return Container(
            width: width,
            height: height ?? 220,
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surfaceContainerHighest,
              borderRadius: borderRadius ?? BorderRadius.circular(12),
              border: Border.all(
                color: Theme.of(context).colorScheme.outlineVariant,
              ),
            ),
            alignment: Alignment.center,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.broken_image_outlined, size: 28),
                const SizedBox(height: DS.spacing8),
                Text(
                  context.l10n.errorBookImageLoadFailed,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          );
        }

        return SparkleNetworkImage(
          imageUrl: resolvedUrl,
          width: width,
          height: height,
          fit: fit,
          borderRadius: borderRadius,
        );
      },
    );
  }
}
