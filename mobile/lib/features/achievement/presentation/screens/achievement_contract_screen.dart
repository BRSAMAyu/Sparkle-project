import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/utils/formatters.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';

// ---------------------------------------------------------------------------
// Main Screen
// ---------------------------------------------------------------------------

class AchievementContractScreen extends ConsumerStatefulWidget {
  const AchievementContractScreen({super.key});

  @override
  ConsumerState<AchievementContractScreen> createState() =>
      _AchievementContractScreenState();
}

class _AchievementContractScreenState
    extends ConsumerState<AchievementContractScreen>
    with TickerProviderStateMixin {
  late final TextEditingController _minutesController;
  late final TextEditingController _daysController;
  late final TextEditingController _stakeController;
  bool _submitting = false;

  // Celebration overlay
  OverlayEntry? _celebrationOverlay;

  @override
  void initState() {
    super.initState();
    _minutesController = TextEditingController(text: '60');
    _daysController = TextEditingController(text: '7');
    _stakeController = TextEditingController(text: '100');
  }

  @override
  void dispose() {
    _minutesController.dispose();
    _daysController.dispose();
    _stakeController.dispose();
    _celebrationOverlay?.remove();
    _celebrationOverlay = null;
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final state = ref.watch(achievementProvider);
    final contract = state.activeContract;

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        title: Text(l10n.contractTitle),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(DS.spacing16),
        child: AnimatedSwitcher(
          duration: const Duration(milliseconds: 400),
          switchInCurve: Curves.easeOutCubic,
          switchOutCurve: Curves.easeInCubic,
          transitionBuilder: (child, animation) => FadeTransition(
              opacity: animation,
              child: SlideTransition(
                position: Tween<Offset>(
                  begin: const Offset(0, 0.04),
                  end: Offset.zero,
                ).animate(animation),
                child: child,
              ),
            ),
          child: contract == null
              ? _buildCreateSection(l10n)
              : _buildActiveSection(contract, l10n),
        ),
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Create section
  // ---------------------------------------------------------------------------

  Widget _buildCreateSection(AppLocalizations l10n) => Column(
      key: const ValueKey('create'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          l10n.contractCreateTitle,
          style: const TextStyle(
            fontSize: DS.fontSizeLg,
            fontWeight: DS.fontWeightSemibold,
          ),
        ),
        const SizedBox(height: DS.spacing8),
        Text(
          l10n.contractCreateSubtitle,
          style: TextStyle(color: DS.textSecondary),
        ),
        const SizedBox(height: DS.spacing16),
        _buildNumberField(
          label: l10n.contractTargetMinutes,
          controller: _minutesController,
        ),
        const SizedBox(height: DS.spacing12),
        _buildNumberField(
          label: l10n.contractTargetDays,
          controller: _daysController,
        ),
        const SizedBox(height: DS.spacing12),
        _buildNumberField(
          label: l10n.contractPhotonStake,
          controller: _stakeController,
        ),
        const SizedBox(height: DS.spacing20),
        SizedBox(
          width: double.infinity,
          child: SparkleButton.primary(
            label: l10n.contractCreateAction,
            onPressed: _submitting ? () {} : _createContract,
            loading: _submitting,
          ),
        ),
      ],
    );

  // ---------------------------------------------------------------------------
  // Active section
  // ---------------------------------------------------------------------------

  Widget _buildActiveSection(SparkContract contract, AppLocalizations l10n) {
    final progress = contract.progressPercent;
    final daysRemaining = contract.endDate.difference(DateTime.now()).inDays;

    return Column(
      key: const ValueKey('active'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          l10n.contractActiveTitle,
          style: const TextStyle(
            fontSize: DS.fontSizeLg,
            fontWeight: DS.fontWeightSemibold,
          ),
        ),
        const SizedBox(height: DS.spacing8),
        Container(
          padding: const EdgeInsets.all(DS.spacing16),
          decoration: BoxDecoration(
            color: DS.surfaceSecondary,
            borderRadius: DS.borderRadius16,
            border: Border.all(color: DS.border),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                l10n.contractProgressLabel(
                  contract.currentDays,
                  contract.targetDays,
                ),
                style: TextStyle(
                  fontSize: DS.fontSizeSm,
                  color: DS.textSecondary,
                ),
              ),
              const SizedBox(height: DS.spacing8),

              // Animated progress bar with milestone markers
              _AnimatedProgressBar(progress: progress),

              const SizedBox(height: DS.spacing12),

              // Staggered animated rows
              _AnimatedRow(
                index: 0,
                child: _buildContractRow(
                  l10n.contractDailyTarget,
                  l10n.contractMinutesTarget(
                    contract.currentMinutes,
                    contract.targetStudyMinutes,
                  ),
                ),
              ),
              _AnimatedRow(
                index: 1,
                child: _buildContractRow(
                  l10n.contractEndsAt,
                  Formatters.formatDateMedium(contract.endDate),
                ),
              ),
              _AnimatedRow(
                index: 2,
                child: _buildContractRow(
                  l10n.contractPhotonStake,
                  '${contract.photonStake}',
                ),
              ),

              // Countdown to deadline
              _AnimatedRow(
                index: 3,
                child: _buildDeadlineRow(daysRemaining, l10n),
              ),

              // Reward multiplier highlight
              _AnimatedRow(
                index: 4,
                child: _RewardMultiplierRow(
                  multiplier: contract.rewardMultiplier,
                  label: l10n.contractRewardMultiplier,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: DS.spacing16),
        SizedBox(
          width: double.infinity,
          child: SparkleButton.destructive(
            label: l10n.contractCancelAction,
            onPressed: _submitting ? () {} : _cancelContract,
          ),
        ),
      ],
    );
  }

  // ---------------------------------------------------------------------------
  // Contract rows
  // ---------------------------------------------------------------------------

  Widget _buildContractRow(String label, String value) => Padding(
      padding: const EdgeInsets.only(top: DS.spacing8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: TextStyle(
              fontSize: DS.fontSizeSm,
              color: DS.textSecondary,
            ),
          ),
          Text(
            value,
            style: TextStyle(
              fontSize: DS.fontSizeSm,
              fontWeight: DS.fontWeightSemibold,
              color: DS.textPrimary,
            ),
          ),
        ],
      ),
    );

  Widget _buildDeadlineRow(int daysRemaining, AppLocalizations l10n) {
    final Color deadlineColor;
    if (daysRemaining > 3) {
      deadlineColor = DS.semanticSuccess;
    } else if (daysRemaining >= 1) {
      deadlineColor = DS.semanticWarning;
    } else {
      deadlineColor = DS.semanticError;
    }

    final label = daysRemaining > 0
        ? l10n.contractDaysRemaining(daysRemaining)
        : l10n.contractDeadlineReached;

    return Padding(
      padding: const EdgeInsets.only(top: DS.spacing8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            l10n.contractCountdown,
            style: TextStyle(
              fontSize: DS.fontSizeSm,
              color: DS.textSecondary,
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing8,
              vertical: DS.spacing4,
            ),
            decoration: BoxDecoration(
              color: deadlineColor.withValues(alpha: 0.12),
              borderRadius: DS.borderRadius8,
            ),
            child: Text(
              label,
              style: TextStyle(
                fontSize: DS.fontSizeSm,
                fontWeight: DS.fontWeightSemibold,
                color: deadlineColor,
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Form field with focus micro-interaction
  // ---------------------------------------------------------------------------

  Widget _buildNumberField({
    required String label,
    required TextEditingController controller,
  }) => _FocusHighlightField(
      label: label,
      controller: controller,
    );

  // ---------------------------------------------------------------------------
  // Contract actions
  // ---------------------------------------------------------------------------

  Future<void> _createContract() async {
    final l10n = context.l10n;
    final minutes = int.tryParse(_minutesController.text.trim()) ?? 0;
    final days = int.tryParse(_daysController.text.trim()) ?? 0;
    final stake = int.tryParse(_stakeController.text.trim()) ?? 0;

    if (minutes <= 0 || days <= 0 || stake <= 0) {
      AppFeedback.error(context, l10n.contractInputInvalid);
      return;
    }

    setState(() => _submitting = true);
    final contract =
        await ref.read(achievementProvider.notifier).createContract(
              targetStudyMinutes: minutes,
              targetDays: days,
              photonStake: stake,
            );
    if (!mounted) return;
    setState(() => _submitting = false);

    if (contract == null) {
      AppFeedback.error(context, l10n.contractCreateFailed);
    } else {
      unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm));
      _showCelebration();
    }
  }

  Future<void> _cancelContract() async {
    final l10n = context.l10n;
    setState(() => _submitting = true);
    final success =
        await ref.read(achievementProvider.notifier).cancelContract();
    if (!mounted) return;
    setState(() => _submitting = false);

    if (success) {
      AppFeedback.success(context, l10n.contractCancelSuccess);
    } else {
      AppFeedback.error(context, l10n.contractCancelFailed);
    }
  }

  // ---------------------------------------------------------------------------
  // Celebration overlay
  // ---------------------------------------------------------------------------

  void _showCelebration() {
    _celebrationOverlay?.remove();
    final overlay = Overlay.of(context);
    _celebrationOverlay = OverlayEntry(
      builder: (_) => _ContractCelebration(
        celebrationLabel: context.l10n.contractCreatedCelebration,
        onDismiss: () {
          _celebrationOverlay?.remove();
          _celebrationOverlay = null;
        },
      ),
    );
    overlay.insert(_celebrationOverlay!);
  }
}

// =============================================================================
// Celebration Overlay Widget
// =============================================================================

class _ContractCelebration extends StatefulWidget {
  const _ContractCelebration({
    required this.onDismiss,
    required this.celebrationLabel,
  });

  final VoidCallback onDismiss;
  final String celebrationLabel;

  @override
  State<_ContractCelebration> createState() => _ContractCelebrationState();
}

class _ContractCelebrationState extends State<_ContractCelebration>
    with TickerProviderStateMixin {
  late final AnimationController _iconController;
  late final AnimationController _textController;
  late final AnimationController _confettiController;
  late final Animation<double> _iconScale;
  late final Animation<double> _textOpacity;

  late final List<_ConfettiParticle> _particles;

  @override
  void initState() {
    super.initState();

    // Icon scale with elastic curve
    _iconController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 600),
    );
    _iconScale = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _iconController, curve: Curves.elasticOut),
    );

    // Text fade-in
    _textController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 400),
    );
    _textOpacity = CurvedAnimation(
      parent: _textController,
      curve: Curves.easeOut,
    );

    // Confetti
    _confettiController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000),
    );

    final rng = math.Random();
    _particles = List.generate(20, (_) => _ConfettiParticle(
        angle: rng.nextDouble() * 2 * math.pi,
        speed: 80 + rng.nextDouble() * 160,
        size: 4 + rng.nextDouble() * 6,
        color: [
          DS.brandPrimary,
          DS.semanticSuccess,
          DS.semanticWarning,
          DS.brandSecondary,
        ][rng.nextInt(4)],
        rotationSpeed: (rng.nextDouble() - 0.5) * 6,
      ),);

    // Start sequence
    _iconController.forward();
    Future.delayed(const Duration(milliseconds: 200), () {
      if (mounted) _textController.forward();
    });
    _confettiController.forward();

    // Auto-dismiss after 2 seconds
    Future.delayed(const Duration(seconds: 2), () {
      if (mounted) widget.onDismiss();
    });
  }

  @override
  void dispose() {
    _iconController.dispose();
    _textController.dispose();
    _confettiController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Material(
      color: Colors.black.withValues(alpha: 0.4),
      child: GestureDetector(
        onTap: widget.onDismiss,
        behavior: HitTestBehavior.opaque,
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              SizedBox(
                width: 200,
                height: 200,
                child: AnimatedBuilder(
                  animation: Listenable.merge([
                    _iconController,
                    _confettiController,
                  ]),
                  builder: (context, child) => CustomPaint(
                      painter: _ConfettiPainter(
                        particles: _particles,
                        progress: _confettiController.value,
                      ),
                      child: child,
                    ),
                  child: ScaleTransition(
                    scale: _iconScale,
                    child: Container(
                      width: 80,
                      height: 80,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: DS.semanticSuccess,
                        boxShadow: [
                          BoxShadow(
                            color:
                                DS.semanticSuccess.withValues(alpha: 0.4),
                            blurRadius: 24,
                            spreadRadius: 4,
                          ),
                        ],
                      ),
                      child: const Icon(
                        Icons.check_rounded,
                        color: Colors.white,
                        size: 44,
                      ),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: DS.spacing16),
              FadeTransition(
                opacity: _textOpacity,
                child: Text(
                  widget.celebrationLabel,
                  style: const TextStyle(
                    fontSize: DS.fontSizeXl,
                    fontWeight: DS.fontWeightBold,
                    color: Colors.white,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
}

// =============================================================================
// Confetti Particle Model & Painter
// =============================================================================

class _ConfettiParticle {
  _ConfettiParticle({
    required this.angle,
    required this.speed,
    required this.size,
    required this.color,
    required this.rotationSpeed,
  });

  final double angle;
  final double speed;
  final double size;
  final Color color;
  final double rotationSpeed;
}

class _ConfettiPainter extends CustomPainter {
  _ConfettiPainter({
    required this.particles,
    required this.progress,
  });

  final List<_ConfettiParticle> particles;
  final double progress;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);

    for (final p in particles) {
      // Ease-out trajectory: fast start, slow end
      final t = Curves.easeOut.transform(progress);
      final distance = p.speed * t;

      final dx = center.dx + math.cos(p.angle) * distance;
      // Add gravity pull downward
      final dy =
          center.dy + math.sin(p.angle) * distance + 40 * progress * progress;

      // Fade out towards the end
      final opacity = (1.0 - progress).clamp(0.0, 1.0);

      final paint = Paint()
        ..color = p.color.withValues(alpha: opacity)
        ..style = PaintingStyle.fill;

      canvas.save();
      canvas.translate(dx, dy);
      canvas.rotate(p.rotationSpeed * progress * math.pi);

      // Draw small rectangles for confetti effect
      canvas.drawRRect(
        RRect.fromRectAndRadius(
          Rect.fromCenter(center: Offset.zero, width: p.size, height: p.size * 0.6),
          Radius.circular(p.size * 0.15),
        ),
        paint,
      );

      canvas.restore();
    }
  }

  @override
  bool shouldRepaint(_ConfettiPainter old) => old.progress != progress;
}

// =============================================================================
// Animated Progress Bar with Milestone Markers
// =============================================================================

class _AnimatedProgressBar extends StatefulWidget {
  const _AnimatedProgressBar({required this.progress});

  final double progress;

  @override
  State<_AnimatedProgressBar> createState() => _AnimatedProgressBarState();
}

class _AnimatedProgressBarState extends State<_AnimatedProgressBar>
    with SingleTickerProviderStateMixin {
  late final AnimationController _glowController;

  @override
  void initState() {
    super.initState();
    _glowController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    );
    if (widget.progress >= 1.0) {
      _glowController.repeat(reverse: true);
    }
  }

  @override
  void didUpdateWidget(_AnimatedProgressBar old) {
    super.didUpdateWidget(old);
    if (widget.progress >= 1.0 && !_glowController.isAnimating) {
      _glowController.repeat(reverse: true);
    } else if (widget.progress < 1.0 && _glowController.isAnimating) {
      _glowController.stop();
      _glowController.value = 0;
    }
  }

  @override
  void dispose() {
    _glowController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => TweenAnimationBuilder<double>(
      tween: Tween<double>(begin: 0, end: widget.progress),
      duration: const Duration(milliseconds: 800),
      curve: Curves.easeOutCubic,
      builder: (context, animatedProgress, _) => AnimatedBuilder(
          animation: _glowController,
          builder: (context, _) {
            final glowOpacity =
                widget.progress >= 1.0 ? _glowController.value * 0.5 : 0.0;

            return Container(
              height: 10,
              decoration: BoxDecoration(
                borderRadius: DS.borderRadiusFull,
                boxShadow: glowOpacity > 0
                    ? [
                        BoxShadow(
                          color: DS.semanticSuccess
                              .withValues(alpha: glowOpacity),
                          blurRadius: 12,
                          spreadRadius: 2,
                        ),
                      ]
                    : null,
              ),
              child: CustomPaint(
                size: const Size(double.infinity, 10),
                painter: _ProgressBarPainter(
                  progress: animatedProgress,
                  trackColor: DS.surfacePrimary,
                  startColor: DS.brandPrimary,
                  endColor: DS.semanticSuccess,
                  milestones: const [0.25, 0.50, 0.75, 1.0],
                  milestoneColor: DS.textTertiary,
                  activeMilestoneColor: DS.semanticSuccess,
                ),
              ),
            );
          },
        ),
    );
}

class _ProgressBarPainter extends CustomPainter {
  _ProgressBarPainter({
    required this.progress,
    required this.trackColor,
    required this.startColor,
    required this.endColor,
    required this.milestones,
    required this.milestoneColor,
    required this.activeMilestoneColor,
  });

  final double progress;
  final Color trackColor;
  final Color startColor;
  final Color endColor;
  final List<double> milestones;
  final Color milestoneColor;
  final Color activeMilestoneColor;

  @override
  void paint(Canvas canvas, Size size) {
    final radius = size.height / 2;
    final trackRRect = RRect.fromRectAndRadius(
      Rect.fromLTWH(0, 0, size.width, size.height),
      Radius.circular(radius),
    );

    // Draw track
    canvas.drawRRect(trackRRect, Paint()..color = trackColor);

    // Draw filled portion with gradient
    if (progress > 0) {
      final fillWidth = size.width * progress.clamp(0.0, 1.0);
      final fillRect = Rect.fromLTWH(0, 0, fillWidth, size.height);
      final fillRRect = RRect.fromRectAndRadius(
        fillRect,
        Radius.circular(radius),
      );

      final gradient = LinearGradient(colors: [startColor, endColor]);
      final paint = Paint()
        ..shader = gradient.createShader(
          Rect.fromLTWH(0, 0, size.width, size.height),
        );

      canvas.drawRRect(fillRRect, paint);
    }

    // Draw milestone dots
    for (final m in milestones) {
      final x = size.width * m;
      final isReached = progress >= m;
      final dotRadius = 3.5;
      final dotPaint = Paint()
        ..color = isReached ? activeMilestoneColor : milestoneColor;

      canvas.drawCircle(Offset(x.clamp(dotRadius, size.width - dotRadius), size.height / 2), dotRadius, dotPaint);
    }
  }

  @override
  bool shouldRepaint(_ProgressBarPainter old) =>
      old.progress != progress ||
      old.trackColor != trackColor ||
      old.startColor != startColor;
}

// =============================================================================
// Animated Row (stagger fade + slide from right)
// =============================================================================

class _AnimatedRow extends StatelessWidget {
  const _AnimatedRow({
    required this.index,
    required this.child,
  });

  final int index;
  final Widget child;

  @override
  Widget build(BuildContext context) => TweenAnimationBuilder<double>(
      tween: Tween<double>(begin: 0, end: 1),
      duration: Duration(milliseconds: 400 + index * 80),
      curve: Curves.easeOutCubic,
      builder: (context, value, _) => Opacity(
          opacity: value.clamp(0.0, 1.0),
          child: Transform.translate(
            offset: Offset(20 * (1 - value), 0),
            child: child,
          ),
        ),
    );
}

// =============================================================================
// Reward Multiplier Row with Golden Pulse
// =============================================================================

class _RewardMultiplierRow extends StatefulWidget {
  const _RewardMultiplierRow({
    required this.multiplier,
    required this.label,
  });

  final double multiplier;
  final String label;

  @override
  State<_RewardMultiplierRow> createState() => _RewardMultiplierRowState();
}

class _RewardMultiplierRowState extends State<_RewardMultiplierRow>
    with SingleTickerProviderStateMixin {
  late final AnimationController _pulseController;
  late final Animation<double> _pulseScale;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1600),
    )..repeat(reverse: true);

    _pulseScale = Tween<double>(begin: 1.0, end: 1.08).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    const goldenAccent = Color(0xFFFFB300);

    return Padding(
      padding: const EdgeInsets.only(top: DS.spacing8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(
                Icons.auto_awesome,
                size: 16,
                color: goldenAccent,
              ),
              const SizedBox(width: DS.spacing4),
              Text(
                widget.label,
                style: TextStyle(
                  fontSize: DS.fontSizeSm,
                  color: DS.textSecondary,
                ),
              ),
            ],
          ),
          ScaleTransition(
            scale: _pulseScale,
            child: Container(
              padding: const EdgeInsets.symmetric(
                horizontal: DS.spacing8,
                vertical: DS.spacing4,
              ),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFFFFC107), Color(0xFFFFB300)],
                ),
                borderRadius: DS.borderRadius8,
                boxShadow: [
                  BoxShadow(
                    color: goldenAccent.withValues(alpha: 0.3),
                    blurRadius: 8,
                  ),
                ],
              ),
              child: Text(
                '${widget.multiplier.toStringAsFixed(1)}x',
                style: const TextStyle(
                  fontSize: DS.fontSizeSm,
                  fontWeight: DS.fontWeightBold,
                  color: Colors.white,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// =============================================================================
// Focus Highlight Text Field
// =============================================================================

class _FocusHighlightField extends StatefulWidget {
  const _FocusHighlightField({
    required this.label,
    required this.controller,
  });

  final String label;
  final TextEditingController controller;

  @override
  State<_FocusHighlightField> createState() => _FocusHighlightFieldState();
}

class _FocusHighlightFieldState extends State<_FocusHighlightField>
    with SingleTickerProviderStateMixin {
  late final AnimationController _borderController;
  late final Animation<Color?> _borderColor;
  final FocusNode _focusNode = FocusNode();

  @override
  void initState() {
    super.initState();
    _borderController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 250),
    );

    _focusNode.addListener(_onFocusChanged);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _borderColor = ColorTween(
      begin: DS.border,
      end: DS.brandPrimary,
    ).animate(CurvedAnimation(
      parent: _borderController,
      curve: Curves.easeOut,
    ),);
  }

  void _onFocusChanged() {
    if (_focusNode.hasFocus) {
      _borderController.forward();
    } else {
      _borderController.reverse();
    }
  }

  @override
  void dispose() {
    _focusNode.removeListener(_onFocusChanged);
    _focusNode.dispose();
    _borderController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
      animation: _borderColor,
      builder: (context, child) {
        final currentBorder = _borderColor.value ?? DS.border;
        return TextField(
          controller: widget.controller,
          focusNode: _focusNode,
          keyboardType: TextInputType.number,
          decoration: InputDecoration(
            labelText: widget.label,
            filled: true,
            fillColor: DS.surfaceSecondary,
            border: OutlineInputBorder(
              borderRadius: DS.borderRadius12,
              borderSide: BorderSide(color: currentBorder),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: DS.borderRadius12,
              borderSide: BorderSide(color: currentBorder),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: DS.borderRadius12,
              borderSide: BorderSide(color: currentBorder, width: 1.5),
            ),
          ),
        );
      },
    );
}
