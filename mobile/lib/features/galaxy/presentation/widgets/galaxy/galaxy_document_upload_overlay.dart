import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart' hide AnimatedSlide;
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/galaxy/presentation/providers/galaxy_document_upload_provider.dart';

class GalaxyDocumentUploadOverlay extends StatelessWidget {
  const GalaxyDocumentUploadOverlay({
    required this.session,
    required this.targetScreenPosition,
    required this.onRetry,
    required this.onDismiss,
    super.key,
  });

  final GalaxyDocumentUploadSession session;
  final Offset targetScreenPosition;
  final VoidCallback onRetry;
  final VoidCallback onDismiss;

  @override
  Widget build(BuildContext context) {
    final safeTop = MediaQuery.paddingOf(context).top;
    final safeBottom = MediaQuery.paddingOf(context).bottom;
    final statusColor = _statusColor(session.phase);

    return Positioned.fill(
      child: IgnorePointer(
        ignoring: session.phase != GalaxyDocumentUploadPhase.failed,
        child: Stack(
          children: [
            Positioned.fill(
              child: IgnorePointer(
                child: _GalaxyUploadFlightLayer(
                  session: session,
                  targetScreenPosition: targetScreenPosition,
                ),
              ),
            ),
            Positioned(
              top: safeTop + 12,
              left: 16,
              right: 16,
              child: IgnorePointer(
                child: Center(
                  child: AnimatedOpacity(
                    duration: const Duration(milliseconds: 240),
                    opacity: session.isDismissing ? 0 : 1,
                    child: Container(
                      constraints: const BoxConstraints(maxWidth: 320),
                      padding: const EdgeInsets.symmetric(
                        horizontal: DS.spacing14,
                        vertical: DS.spacing10,
                      ),
                      decoration: BoxDecoration(
                        color: const Color(0xFF0A1320).withValues(alpha: 0.9),
                        borderRadius: BorderRadius.circular(999),
                        border: Border.all(
                          color: statusColor.withValues(alpha: 0.36),
                        ),
                        boxShadow: [
                          BoxShadow(
                            color: statusColor.withValues(alpha: 0.18),
                            blurRadius: 24,
                            spreadRadius: 1,
                          ),
                        ],
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          _ChipPulse(color: statusColor),
                          const SizedBox(width: DS.spacing10),
                          Flexible(
                            child: Text(
                              _chipLabel(context, session),
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: Theme.of(context)
                                  .textTheme
                                  .labelLarge
                                  ?.copyWith(
                                    color: Colors.white,
                                    fontWeight: FontWeight.w700,
                                  ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ),
            Positioned(
              left: 16,
              right: 16,
              bottom: safeBottom + 96,
              child: Align(
                alignment: Alignment.bottomCenter,
                child: AnimatedSlide(
                  duration: const Duration(milliseconds: 320),
                  curve: Curves.easeOutCubic,
                  offset: session.isDismissing
                      ? const Offset(0, 0.12)
                      : Offset.zero,
                  child: AnimatedOpacity(
                    duration: const Duration(milliseconds: 240),
                    opacity: session.isDismissing ? 0 : 1,
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 420),
                      child: _GalaxyUploadStatusCard(
                        session: session,
                        onRetry: onRetry,
                        onDismiss: onDismiss,
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  static Color _statusColor(GalaxyDocumentUploadPhase phase) {
    switch (phase) {
      case GalaxyDocumentUploadPhase.success:
        return DS.success;
      case GalaxyDocumentUploadPhase.failed:
        return DS.error;
      case GalaxyDocumentUploadPhase.uploading:
      case GalaxyDocumentUploadPhase.queued:
      case GalaxyDocumentUploadPhase.extracting:
      case GalaxyDocumentUploadPhase.findingKnowledge:
      case GalaxyDocumentUploadPhase.buildingNodes:
      case GalaxyDocumentUploadPhase.idle:
        return const Color(0xFF7BE7FF);
    }
  }

  static String _chipLabel(
    BuildContext context,
    GalaxyDocumentUploadSession session,
  ) {
    final l10n = context.l10n;
    switch (session.phase) {
      case GalaxyDocumentUploadPhase.uploading:
        return l10n.galaxyUploadStatusUploading;
      case GalaxyDocumentUploadPhase.queued:
        return l10n.galaxyUploadStatusQueued;
      case GalaxyDocumentUploadPhase.extracting:
        return l10n.galaxyUploadStatusExtracting;
      case GalaxyDocumentUploadPhase.findingKnowledge:
        return l10n.galaxyUploadStatusFindingKnowledge;
      case GalaxyDocumentUploadPhase.buildingNodes:
        return l10n.galaxyUploadStatusBuildingNodes;
      case GalaxyDocumentUploadPhase.success:
        return l10n.galaxyUploadSuccessChip(
          session.nodesFound ?? 0,
        );
      case GalaxyDocumentUploadPhase.failed:
        return l10n.galaxyUploadFailedTitle;
      case GalaxyDocumentUploadPhase.idle:
        return '';
    }
  }
}

class _GalaxyUploadStatusCard extends StatelessWidget {
  const _GalaxyUploadStatusCard({
    required this.session,
    required this.onRetry,
    required this.onDismiss,
  });

  final GalaxyDocumentUploadSession session;
  final VoidCallback onRetry;
  final VoidCallback onDismiss;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = context.l10n;
    final accentColor = _accentColor;
    final details = _details(context);

    return GraphiteCardSurface(
      padding: const EdgeInsets.all(DS.spacing18),
      motionToken: SparkleMotionToken.scene,
      backgroundColor: const Color(0xFF0B1523).withValues(alpha: 0.92),
      borderColor: accentColor.withValues(alpha: 0.22),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: LinearGradient(
                    colors: [
                      accentColor.withValues(alpha: 0.35),
                      accentColor.withValues(alpha: 0.1),
                    ],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  border: Border.all(
                    color: accentColor.withValues(alpha: 0.38),
                  ),
                ),
                child: Icon(
                  _phaseIcon,
                  color: accentColor,
                ),
              ),
              const SizedBox(width: DS.spacing14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _title(context),
                      style: theme.textTheme.titleMedium?.copyWith(
                        color: Colors.white,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      details,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: Colors.white.withValues(alpha: 0.7),
                        height: 1.4,
                      ),
                    ),
                  ],
                ),
              ),
              if (session.phase == GalaxyDocumentUploadPhase.success)
                IconButton(
                  onPressed: onDismiss,
                  icon: const Icon(Icons.close_rounded),
                  color: Colors.white.withValues(alpha: 0.72),
                ),
            ],
          ),
          const SizedBox(height: DS.spacing16),
          _StageStepper(session: session),
          const SizedBox(height: DS.spacing14),
          ClipRRect(
            borderRadius: BorderRadius.circular(999),
            child: LinearProgressIndicator(
              minHeight: 8,
              value: session.overallProgress.clamp(0, 1),
              backgroundColor: Colors.white.withValues(alpha: 0.08),
              valueColor: AlwaysStoppedAnimation<Color>(accentColor),
            ),
          ),
          const SizedBox(height: DS.spacing10),
          Row(
            children: [
              Expanded(
                child: Text(
                  session.fileName,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: theme.textTheme.labelLarge?.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              const SizedBox(width: DS.spacing12),
              Text(
                '${(session.overallProgress * 100).round()}%',
                style: theme.textTheme.labelLarge?.copyWith(
                  color: accentColor,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
          if (session.phase == GalaxyDocumentUploadPhase.failed) ...[
            const SizedBox(height: DS.spacing14),
            Text(
              session.errorMessage ?? l10n.galaxyUploadFailedBody,
              style: theme.textTheme.bodySmall?.copyWith(
                color: Colors.white.withValues(alpha: 0.74),
                height: 1.5,
              ),
            ),
            const SizedBox(height: DS.spacing14),
            Row(
              children: [
                Expanded(
                  child: SparkleButton.primary(
                    label: l10n.galaxyUploadRetry,
                    onPressed: onRetry,
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Color get _accentColor {
    switch (session.phase) {
      case GalaxyDocumentUploadPhase.success:
        return DS.success;
      case GalaxyDocumentUploadPhase.failed:
        return DS.error;
      case GalaxyDocumentUploadPhase.uploading:
      case GalaxyDocumentUploadPhase.queued:
      case GalaxyDocumentUploadPhase.extracting:
      case GalaxyDocumentUploadPhase.findingKnowledge:
      case GalaxyDocumentUploadPhase.buildingNodes:
      case GalaxyDocumentUploadPhase.idle:
        return const Color(0xFF7BE7FF);
    }
  }

  IconData get _phaseIcon {
    switch (session.phase) {
      case GalaxyDocumentUploadPhase.success:
        return Icons.auto_awesome_rounded;
      case GalaxyDocumentUploadPhase.failed:
        return Icons.refresh_rounded;
      case GalaxyDocumentUploadPhase.uploading:
      case GalaxyDocumentUploadPhase.queued:
      case GalaxyDocumentUploadPhase.extracting:
      case GalaxyDocumentUploadPhase.findingKnowledge:
      case GalaxyDocumentUploadPhase.buildingNodes:
      case GalaxyDocumentUploadPhase.idle:
        return Icons.menu_book_rounded;
    }
  }

  String _title(BuildContext context) {
    final l10n = context.l10n;
    switch (session.phase) {
      case GalaxyDocumentUploadPhase.uploading:
        return l10n.galaxyUploadStatusUploading;
      case GalaxyDocumentUploadPhase.queued:
        return l10n.galaxyUploadStatusQueued;
      case GalaxyDocumentUploadPhase.extracting:
        return l10n.galaxyUploadStatusExtracting;
      case GalaxyDocumentUploadPhase.findingKnowledge:
        return l10n.galaxyUploadStatusFindingKnowledge;
      case GalaxyDocumentUploadPhase.buildingNodes:
        return l10n.galaxyUploadStatusBuildingNodes;
      case GalaxyDocumentUploadPhase.success:
        return l10n.galaxyUploadSuccessTitle;
      case GalaxyDocumentUploadPhase.failed:
        return l10n.galaxyUploadFailedTitle;
      case GalaxyDocumentUploadPhase.idle:
        return '';
    }
  }

  String _details(BuildContext context) {
    final l10n = context.l10n;
    if (session.phase == GalaxyDocumentUploadPhase.success) {
      return l10n.galaxyUploadSuccessBody(session.nodesFound ?? 0);
    }
    if (session.phase == GalaxyDocumentUploadPhase.failed) {
      return l10n.galaxyUploadFailedBody;
    }
    return l10n.galaxyUploadHeadingTo(session.target.label);
  }
}

class _StageStepper extends StatelessWidget {
  const _StageStepper({required this.session});

  final GalaxyDocumentUploadSession session;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final items = <({String label, bool complete, bool active})>[
      (
        label: l10n.galaxyUploadStepUpload,
        complete:
            session.phase.index > GalaxyDocumentUploadPhase.uploading.index,
        active: session.phase == GalaxyDocumentUploadPhase.uploading,
      ),
      (
        label: l10n.galaxyUploadStepExtract,
        complete:
            session.phase.index > GalaxyDocumentUploadPhase.extracting.index,
        active: session.phase == GalaxyDocumentUploadPhase.extracting ||
            session.phase == GalaxyDocumentUploadPhase.queued,
      ),
      (
        label: l10n.galaxyUploadStepFind,
        complete: session.phase.index >
            GalaxyDocumentUploadPhase.findingKnowledge.index,
        active: session.phase == GalaxyDocumentUploadPhase.findingKnowledge,
      ),
      (
        label: l10n.galaxyUploadStepComplete,
        complete: session.phase == GalaxyDocumentUploadPhase.success,
        active: session.phase == GalaxyDocumentUploadPhase.buildingNodes ||
            session.phase == GalaxyDocumentUploadPhase.success,
      ),
    ];

    return Row(
      children: items
          .map(
            (item) => Expanded(
              child: Padding(
                padding: EdgeInsets.only(
                  right: item == items.last ? 0 : DS.spacing8,
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    AnimatedContainer(
                      duration: const Duration(milliseconds: 220),
                      height: 4,
                      decoration: BoxDecoration(
                        color: item.complete || item.active
                            ? (item.complete
                                ? DS.success
                                : const Color(0xFF7BE7FF))
                            : Colors.white.withValues(alpha: 0.08),
                        borderRadius: BorderRadius.circular(999),
                      ),
                    ),
                    const SizedBox(height: DS.spacing6),
                    Text(
                      item.label,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(
                            color: item.complete || item.active
                                ? Colors.white
                                : Colors.white.withValues(alpha: 0.52),
                            fontWeight:
                                item.active ? FontWeight.w700 : FontWeight.w500,
                          ),
                    ),
                  ],
                ),
              ),
            ),
          )
          .toList(growable: false),
    );
  }
}

class _GalaxyUploadFlightLayer extends StatelessWidget {
  const _GalaxyUploadFlightLayer({
    required this.session,
    required this.targetScreenPosition,
  });

  final GalaxyDocumentUploadSession session;
  final Offset targetScreenPosition;

  @override
  Widget build(BuildContext context) {
    final travelProgress = session.phase == GalaxyDocumentUploadPhase.uploading
        ? Curves.easeOutCubic.transform(
            session.uploadProgress.clamp(0.08, 1),
          )
        : 1.0;
    final currentPosition = _pointOnQuadratic(
      session.originScreenPosition,
      targetScreenPosition,
      travelProgress,
    );

    return Stack(
      children: [
        Positioned.fill(
          child: CustomPaint(
            painter: _GalaxyUploadTrailPainter(
              origin: session.originScreenPosition,
              target: targetScreenPosition,
              progress: travelProgress,
              phase: session.phase,
            ),
          ),
        ),
        Positioned(
          left: currentPosition.dx - 22,
          top: currentPosition.dy - 22,
          child: _GlowingDocumentOrb(
            phase: session.phase,
          ),
        ),
        Positioned(
          left: targetScreenPosition.dx - 48,
          top: targetScreenPosition.dy - 48,
          child: _TargetGlow(
            phase: session.phase,
          ),
        ),
      ],
    );
  }

  Offset _pointOnQuadratic(Offset start, Offset end, double t) {
    final control = Offset(
      (start.dx + end.dx) / 2,
      math.min(start.dy, end.dy) - 120,
    );
    final oneMinusT = 1 - t;
    return Offset(
      (oneMinusT * oneMinusT * start.dx) +
          (2 * oneMinusT * t * control.dx) +
          (t * t * end.dx),
      (oneMinusT * oneMinusT * start.dy) +
          (2 * oneMinusT * t * control.dy) +
          (t * t * end.dy),
    );
  }
}

class _GalaxyUploadTrailPainter extends CustomPainter {
  const _GalaxyUploadTrailPainter({
    required this.origin,
    required this.target,
    required this.progress,
    required this.phase,
  });

  final Offset origin;
  final Offset target;
  final double progress;
  final GalaxyDocumentUploadPhase phase;

  @override
  void paint(Canvas canvas, Size size) {
    final control = Offset(
      (origin.dx + target.dx) / 2,
      math.min(origin.dy, target.dy) - 120,
    );
    final path = Path()
      ..moveTo(origin.dx, origin.dy)
      ..quadraticBezierTo(
        control.dx,
        control.dy,
        target.dx,
        target.dy,
      );
    final metrics = path.computeMetrics();
    if (metrics.isEmpty) {
      return;
    }
    final metric = metrics.first;
    final extract = metric.extractPath(0, metric.length * progress);
    final accent = switch (phase) {
      GalaxyDocumentUploadPhase.success => DS.success,
      GalaxyDocumentUploadPhase.failed => DS.error,
      _ => const Color(0xFF7BE7FF),
    };

    final glowPaint = Paint()
      ..color = accent.withValues(alpha: 0.16)
      ..strokeWidth = 8
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 12);
    final corePaint = Paint()
      ..color = accent.withValues(alpha: 0.54)
      ..strokeWidth = 2.2
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    canvas
      ..drawPath(extract, glowPaint)
      ..drawPath(extract, corePaint);
  }

  @override
  bool shouldRepaint(covariant _GalaxyUploadTrailPainter oldDelegate) =>
      oldDelegate.origin != origin ||
      oldDelegate.target != target ||
      oldDelegate.progress != progress ||
      oldDelegate.phase != phase;
}

class _GlowingDocumentOrb extends StatelessWidget {
  const _GlowingDocumentOrb({required this.phase});

  final GalaxyDocumentUploadPhase phase;

  @override
  Widget build(BuildContext context) {
    final color = switch (phase) {
      GalaxyDocumentUploadPhase.success => DS.success,
      GalaxyDocumentUploadPhase.failed => DS.error,
      _ => const Color(0xFF7BE7FF),
    };

    return SparkleAttentionPulse(
      active: phase != GalaxyDocumentUploadPhase.failed,
      glowColor: color,
      scaleRange: 0.04,
      child: Container(
        width: 44,
        height: 44,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: RadialGradient(
            colors: [
              Colors.white,
              color.withValues(alpha: 0.9),
              color.withValues(alpha: 0.22),
            ],
          ),
          boxShadow: [
            BoxShadow(
              color: color.withValues(alpha: 0.3),
              blurRadius: 24,
              spreadRadius: 4,
            ),
          ],
        ),
        child: const Icon(
          Icons.menu_book_rounded,
          color: Color(0xFF04111F),
          size: 22,
        ),
      ),
    );
  }
}

class _TargetGlow extends StatelessWidget {
  const _TargetGlow({required this.phase});

  final GalaxyDocumentUploadPhase phase;

  @override
  Widget build(BuildContext context) {
    final color = switch (phase) {
      GalaxyDocumentUploadPhase.success => DS.success,
      GalaxyDocumentUploadPhase.failed => DS.error,
      _ => const Color(0xFF7BE7FF),
    };

    final ringCount = phase == GalaxyDocumentUploadPhase.success ? 3 : 2;
    return IgnorePointer(
      child: SizedBox(
        width: 96,
        height: 96,
        child: Stack(
          alignment: Alignment.center,
          children: List.generate(ringCount, (index) {
            final delay = index * 0.1;
            return TweenAnimationBuilder<double>(
              tween: Tween(begin: 0.4 + delay, end: 1 + delay),
              duration: const Duration(milliseconds: 1400),
              curve: Curves.easeOut,
              builder: (context, value, _) {
                final scale = 0.6 + (value % 1) * 0.8;
                final opacity = (1 - (value % 1)).clamp(0.0, 1.0);
                return Transform.scale(
                  scale: scale,
                  child: Container(
                    width: 42,
                    height: 42,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      border: Border.all(
                        color: color.withValues(alpha: opacity * 0.55),
                        width: phase == GalaxyDocumentUploadPhase.success
                            ? 2.2
                            : 1.6,
                      ),
                    ),
                  ),
                );
              },
            );
          }),
        ),
      ),
    );
  }
}

class _ChipPulse extends StatelessWidget {
  const _ChipPulse({required this.color});

  final Color color;

  @override
  Widget build(BuildContext context) => SparkleAttentionPulse(
        glowColor: color,
        scaleRange: 0.05,
        child: Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: color,
          ),
        ),
      );
}
