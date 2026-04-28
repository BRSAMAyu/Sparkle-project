import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/openclaw_connection_service.dart';

class OpenClawConnectionDiagnosticsSheet extends StatefulWidget {
  const OpenClawConnectionDiagnosticsSheet({
    required this.service,
    super.key,
  });

  final OpenClawConnectionService service;

  @override
  State<OpenClawConnectionDiagnosticsSheet> createState() =>
      _OpenClawConnectionDiagnosticsSheetState();
}

class _OpenClawConnectionDiagnosticsSheetState
    extends State<OpenClawConnectionDiagnosticsSheet> {
  late Future<OpenClawConnectionDiagnosticReport> _future;

  @override
  void initState() {
    super.initState();
    _future = widget.service.diagnoseConnection();
  }

  void _reload() => setState(() {
        _future = widget.service.diagnoseConnection();
      });

  @override
  Widget build(BuildContext context) => SafeArea(
        child: FractionallySizedBox(
          heightFactor: 0.88,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(
              DS.spacing16,
              DS.spacing12,
              DS.spacing16,
              DS.spacing16,
            ),
            child: FutureBuilder<OpenClawConnectionDiagnosticReport>(
              future: _future,
              builder: (context, snapshot) {
                if (snapshot.connectionState != ConnectionState.done) {
                  return const Center(
                    child: CircularProgressIndicator.adaptive(),
                  );
                }
                if (snapshot.hasError) {
                  return _DiagnosticsErrorState(
                    message: '${snapshot.error}',
                    onRetry: _reload,
                  );
                }
                final report = snapshot.data ??
                    OpenClawConnectionDiagnosticReport.fallback(
                      config: widget.service.config,
                      info: widget.service.info,
                    );
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                context.l10n.openclawConnectionDiagnostics,
                                style: DS.titleMedium.copyWith(
                                  fontWeight: DS.fontWeightBold,
                                ),
                              ),
                              const SizedBox(height: DS.spacing4),
                              Text(
                                report.summary,
                                style: DS.bodySmall.copyWith(
                                  color: DS.textSecondary,
                                  height: 1.45,
                                ),
                              ),
                            ],
                          ),
                        ),
                        IconButton(
                          onPressed: _reload,
                          tooltip: context.l10n.openclawRediagnose,
                          icon: const Icon(Icons.refresh_rounded),
                        ),
                      ],
                    ),
                    const SizedBox(height: DS.spacing12),
                    Wrap(
                      spacing: DS.spacing8,
                      runSpacing: DS.spacing8,
                      children: [
                        _DiagnosticPill(
                          icon: _statusIcon(report.overallStatus),
                          label: _statusLabel(context, report.overallStatus),
                          color: _statusColor(report.overallStatus),
                        ),
                        if ((report.transport ?? '').isNotEmpty)
                          _DiagnosticPill(
                            icon: Icons.swap_horiz_rounded,
                            label: report.transport!,
                            color: DS.textSecondary,
                          ),
                        if ((report.connectionSource ?? '').isNotEmpty)
                          _DiagnosticPill(
                            icon: Icons.account_tree_rounded,
                            label: report.connectionSource!,
                            color: DS.textSecondary,
                          ),
                      ],
                    ),
                    const SizedBox(height: DS.spacing12),
                    GraphiteCardSurface(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          if ((report.gatewayUrl ?? '').isNotEmpty)
                            Text(
                              'Gateway: ${report.gatewayUrl}',
                              style: DS.bodySmall.copyWith(
                                color: DS.textPrimary,
                              ),
                            ),
                          if ((report.wsUrl ?? '').isNotEmpty) ...[
                            if ((report.gatewayUrl ?? '').isNotEmpty)
                              const SizedBox(height: DS.spacing6),
                            Text(
                              'WS: ${report.wsUrl}',
                              style: DS.bodySmall.copyWith(
                                color: DS.textSecondary,
                              ),
                            ),
                          ],
                          const SizedBox(height: DS.spacing6),
                          Text(
                            context.l10n.openclawGeneratedAt(_formatDateTime(report.generatedAt)),
                            style: DS.bodySmall.copyWith(
                              color: DS.textSecondary,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: DS.spacing12),
                    Expanded(
                      child: ListView.separated(
                        itemCount: report.checks.length,
                        separatorBuilder: (_, __) =>
                            const SizedBox(height: DS.spacing10),
                        itemBuilder: (context, index) =>
                            _DiagnosticCheckCard(check: report.checks[index]),
                      ),
                    ),
                  ],
                );
              },
            ),
          ),
        ),
      );

  static String _formatDateTime(DateTime value) {
    final hour = value.hour.toString().padLeft(2, '0');
    final minute = value.minute.toString().padLeft(2, '0');
    final second = value.second.toString().padLeft(2, '0');
    return '${value.month}-${value.day} $hour:$minute:$second';
  }

  static IconData _statusIcon(OpenClawDiagnosticCheckStatus status) {
    switch (status) {
      case OpenClawDiagnosticCheckStatus.passed:
        return Icons.check_circle_rounded;
      case OpenClawDiagnosticCheckStatus.warning:
        return Icons.warning_amber_rounded;
      case OpenClawDiagnosticCheckStatus.skipped:
        return Icons.fast_forward_rounded;
      case OpenClawDiagnosticCheckStatus.failed:
        return Icons.error_outline_rounded;
    }
  }

  static String _statusLabel(BuildContext context, OpenClawDiagnosticCheckStatus status) {
    switch (status) {
      case OpenClawDiagnosticCheckStatus.passed:
        return context.l10n.openclawConnectionNormal;
      case OpenClawDiagnosticCheckStatus.warning:
        return context.l10n.openclawConnectionWarning;
      case OpenClawDiagnosticCheckStatus.skipped:
        return context.l10n.openclawConnectionSkipped;
      case OpenClawDiagnosticCheckStatus.failed:
        return context.l10n.openclawConnectionFixNeeded;
    }
  }

  static Color _statusColor(OpenClawDiagnosticCheckStatus status) {
    switch (status) {
      case OpenClawDiagnosticCheckStatus.passed:
        return DS.semanticSuccess;
      case OpenClawDiagnosticCheckStatus.warning:
        return DS.semanticWarning;
      case OpenClawDiagnosticCheckStatus.skipped:
        return DS.info;
      case OpenClawDiagnosticCheckStatus.failed:
        return DS.semanticError;
    }
  }
}

class _DiagnosticPill extends StatelessWidget {
  const _DiagnosticPill({
    required this.icon,
    required this.label,
    required this.color,
  });

  final IconData icon;
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) => DecoratedBox(
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(999),
        ),
        child: Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing10,
            vertical: DS.spacing8,
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: 16, color: color),
              const SizedBox(width: DS.spacing6),
              Text(
                label,
                style: DS.bodySmall.copyWith(
                  color: color,
                  fontWeight: DS.fontWeightSemiBold,
                ),
              ),
            ],
          ),
        ),
      );
}

class _DiagnosticCheckCard extends StatelessWidget {
  const _DiagnosticCheckCard({required this.check});

  final OpenClawConnectionDiagnosticCheck check;

  @override
  Widget build(BuildContext context) {
    final color = _OpenClawConnectionDiagnosticsSheetState._statusColor(
      check.status,
    );
    final icon = _OpenClawConnectionDiagnosticsSheetState._statusIcon(
      check.status,
    );
    final detailEntries = check.details.entries.take(3).toList(growable: false);

    return GraphiteCardSurface(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(icon, color: color),
              const SizedBox(width: DS.spacing10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      check.label,
                      style: DS.bodyMedium.copyWith(
                        fontWeight: DS.fontWeightSemiBold,
                        color: DS.textPrimary,
                      ),
                    ),
                    const SizedBox(height: DS.spacing6),
                    Text(
                      check.message,
                      style: DS.bodySmall.copyWith(
                        color: DS.textSecondary,
                        height: 1.45,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          if ((check.suggestion ?? '').isNotEmpty) ...[
            const SizedBox(height: DS.spacing10),
            Text(
              context.l10n.openclawSuggestion(check.suggestion!),
              style: DS.bodySmall.copyWith(
                color: color,
                fontWeight: DS.fontWeightSemiBold,
              ),
            ),
          ],
          if (detailEntries.isNotEmpty) ...[
            const SizedBox(height: DS.spacing10),
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              children: detailEntries
                  .map(
                    (entry) => _DiagnosticPill(
                      icon: Icons.data_object_rounded,
                      label: '${entry.key}: ${entry.value}',
                      color: DS.textSecondary,
                    ),
                  )
                  .toList(growable: false),
            ),
          ],
        ],
      ),
    );
  }
}

class _DiagnosticsErrorState extends StatelessWidget {
  const _DiagnosticsErrorState({
    required this.message,
    required this.onRetry,
  });

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Center(
        child: GraphiteCardSurface(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.error_outline_rounded, color: DS.semanticError),
              const SizedBox(height: DS.spacing12),
              Text(
                context.l10n.openclawDiagnoseFailed,
                style: DS.titleMedium.copyWith(
                  fontWeight: DS.fontWeightBold,
                ),
              ),
              const SizedBox(height: DS.spacing8),
              Text(
                message,
                style: DS.bodySmall.copyWith(
                  color: DS.textSecondary,
                  height: 1.45,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: DS.spacing12),
              FilledButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh_rounded),
                label: Text(context.l10n.openclawRediagnose),
              ),
            ],
          ),
        ),
      );
}
