import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/user/data/repositories/user_repository.dart';

class ExportDataScreen extends ConsumerStatefulWidget {
  const ExportDataScreen({super.key});

  @override
  ConsumerState<ExportDataScreen> createState() => _ExportDataScreenState();
}

class _ExportDataScreenState extends ConsumerState<ExportDataScreen> {
  bool _exporting = false;
  String? _error;
  String? _lastFilePath;

  Future<void> _startExport() async {
    if (_exporting) return;
    final emptyFileMessage = context.l10n.profileExportEmptyFile;
    final shareSubject = context.l10n.profileExportShareSubject;
    setState(() {
      _exporting = true;
      _error = null;
    });

    try {
      final bytes = await ref.read(userRepositoryProvider).exportUserData();
      if (bytes.isEmpty) {
        throw Exception(emptyFileMessage);
      }

      final dir = await getTemporaryDirectory();
      final now = DateTime.now();
      final filename =
          'sparkle_export_${now.year}${now.month.toString().padLeft(2, '0')}${now.day.toString().padLeft(2, '0')}.zip';
      final file = File('${dir.path}/$filename');
      await file.writeAsBytes(bytes, flush: true);

      if (!mounted) return;
      setState(() {
        _lastFilePath = file.path;
      });

      await SharePlus.instance.share(
        ShareParams(
          files: [XFile(file.path, mimeType: 'application/zip')],
          subject: shareSubject,
        ),
      );
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = context.l10n.profileExportFailed(e.toString());
      });
    } finally {
      if (mounted) {
        setState(() {
          _exporting = false;
        });
      }
    }
  }

  void _goBack() {
    final navigator = Navigator.maybeOf(context);
    if (navigator?.canPop() ?? false) {
      navigator!.pop();
    } else {
      try {
        context.go('/profile');
      } catch (_) {
        // The screen can be rendered in isolated widget tests without GoRouter.
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return GraphiteScaffold(
      role: SparklePageRole.settings,
      safeArea: false,
      appBar: AppBar(
        leading: SparkleIconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: _goBack,
          variant: ButtonVariant.ghost,
          semanticLabel: l10n.back,
        ),
        title: Text(
          l10n.profileExportData,
          style: DS.titleLarge.copyWith(
            color: DS.textPrimary,
            fontWeight: DS.fontWeightBold,
          ),
        ),
        iconTheme: IconThemeData(color: DS.textPrimary),
        backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
        elevation: 0,
      ),
      child: ContentConstraint(
        child: ListView(
          padding: const EdgeInsets.all(DS.lg),
          children: [
            GraphiteCardSurface(
              surfaceRole: SparkleSurfaceRole.panel,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        width: 42,
                        height: 42,
                        decoration: BoxDecoration(
                          color: DS.primaryBase.withValues(alpha: 0.12),
                          borderRadius: DS.borderRadius12,
                        ),
                        child: Icon(
                          Icons.archive_outlined,
                          color: DS.primaryBase,
                        ),
                      ),
                      const SizedBox(width: DS.spacing12),
                      Expanded(
                        child: Text(
                          context.l10n.userPrepareDataArchive,
                          style: DS.titleMedium.copyWith(
                            color: DS.textPrimary,
                            fontWeight: DS.fontWeightBold,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: DS.spacing12),
                  Text(
                    context.l10n.userExportDescription,
                    style: DS.bodyMedium.copyWith(
                      color: DS.textSecondary,
                      height: 1.45,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: DS.lg),
            GraphiteCardSurface(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const _InfoRow(
                    icon: Icons.lock_outline_rounded,
                    title: context.l10n.userPrivacyReminder,
                    body: context.l10n.userPrivacyReminderBody,
                  ),
                  const Divider(height: DS.xl),
                  _InfoRow(
                    icon: Icons.cloud_download_outlined,
                    title: context.l10n.userCurrentStatus,
                    body: _exporting
                        ? l10n.profileExportPreparing
                        : _lastFilePath == null
                            ? context.l10n.userNotGeneratedYet
                            : context.l10n.userAlreadyGenerated,
                  ),
                  if (_lastFilePath != null) ...[
                    const SizedBox(height: DS.spacing8),
                    Text(
                      _lastFilePath!,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: DS.bodySmall.copyWith(color: DS.textSecondary),
                    ),
                  ],
                ],
              ),
            ),
            if (_error != null) ...[
              const SizedBox(height: DS.lg),
              GraphiteCardSurface(
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.error_outline, color: DS.error),
                    const SizedBox(width: DS.spacing12),
                    Expanded(
                      child: Text(
                        _error!,
                        style: DS.bodyMedium.copyWith(
                          color: DS.error,
                          height: 1.4,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
            const SizedBox(height: DS.xl),
            SparkleButton.primary(
              label: _exporting ? '导出中...' : l10n.profileExportData,
              onPressed: _exporting ? () {} : _startExport,
            ),
          ],
        ),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({
    required this.icon,
    required this.title,
    required this.body,
  });

  final IconData icon;
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) => Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: DS.textSecondary, size: 22),
          const SizedBox(width: DS.spacing12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: DS.bodyLarge.copyWith(
                    color: DS.textPrimary,
                    fontWeight: DS.fontWeightSemibold,
                  ),
                ),
                const SizedBox(height: DS.spacing4),
                Text(
                  body,
                  style: DS.bodySmall.copyWith(
                    color: DS.textSecondary,
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),
        ],
      );
}
