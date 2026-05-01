import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/aurora/data/models/aurora_core_session.dart';
import 'package:sparkle/features/aurora/data/services/aurora_core_session_service.dart';
import 'package:sparkle/features/aurora/data/services/aurora_telemetry_service.dart';
import 'package:sparkle/features/chat/presentation/providers/aurora_status_provider.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

// ── Provider ──────────────────────────────────────────────────────────────────

final _coreSessionServiceProvider = Provider<AuroraCoreSessionService>((ref) {
  return AuroraCoreSessionService(ref.read(apiClientProvider));
});

final _telemetryServiceProvider = Provider<AuroraTelemetryService>((ref) {
  return AuroraTelemetryService(ref.read(apiClientProvider));
});

// ── Entry point ───────────────────────────────────────────────────────────────

/// Shows the Aurora Core Session (L3) as a persistent bottom sheet.
///
/// The sheet handles the full session lifecycle:
/// - Entry declaration with ritualized opening
/// - Multi-message Aurora monologue
/// - Predicted reply options (semantic chips + freeform correction)
/// - Session exit with calibration result summary
Future<void> showAuroraCoreSession({
  required BuildContext context,
  required String bandStatus,
  required List<String> wakeReasons,
  String? conversationId,
  String? scope,
  String sessionType = 'user_initiated',
}) async {
  await showModalBottomSheet<void>(
    context: context,
    backgroundColor: Colors.transparent,
    isScrollControlled: true,
    isDismissible: false,
    enableDrag: false,
    builder: (ctx) => _AuroraCoreSessionSheet(
      bandStatus: bandStatus,
      wakeReasons: wakeReasons,
      conversationId: conversationId,
      scope: scope,
      sessionType: sessionType,
    ),
  );
}

// ── Sheet widget ──────────────────────────────────────────────────────────────

class _AuroraCoreSessionSheet extends ConsumerStatefulWidget {
  const _AuroraCoreSessionSheet({
    required this.bandStatus,
    required this.wakeReasons,
    this.conversationId,
    this.scope,
    this.sessionType = 'user_initiated',
  });

  final String bandStatus;
  final List<String> wakeReasons;
  final String? conversationId;
  final String? scope;
  final String sessionType;

  @override
  ConsumerState<_AuroraCoreSessionSheet> createState() =>
      _AuroraCoreSessionSheetState();
}

class _AuroraCoreSessionSheetState
    extends ConsumerState<_AuroraCoreSessionSheet>
    with SingleTickerProviderStateMixin {
  AuroraCoreSession? _session;
  bool _loading = true;
  bool _sending = false;
  String? _error;
  final _freeformController = TextEditingController();
  bool _showFreeformInput = false;
  late final AnimationController _entryController;
  late final Animation<double> _entryAnimation;
  final ScrollController _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _entryController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 400),
    );
    _entryAnimation = CurvedAnimation(
      parent: _entryController,
      curve: Curves.easeOutCubic,
    );
    _startSession();
  }

  @override
  void dispose() {
    _entryController.dispose();
    _freeformController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _startSession() async {
    final service = ref.read(_coreSessionServiceProvider);
    try {
      final session = await service.startSession(
        conversationId: widget.conversationId,
        sessionType: widget.sessionType,
        scope: widget.scope,
        wakeReasons: widget.wakeReasons,
        bandStatus: widget.bandStatus,
      );
      if (mounted) {
        setState(() {
          _session = session;
          _loading = false;
        });
        unawaited(_entryController.forward());
        _scrollToBottom();
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = context.l10n.auroraStartFailed;
          _loading = false;
        });
      }
    }
  }

  Future<void> _respond({
    required String content,
    String? optionId,
    String? semanticValue,
    Map<String, dynamic>? modelWriteEffect,
    bool isFreeform = false,
    AuroraPredictedReplyOption? option,
    String? groupId,
  }) async {
    if (_session == null || _sending) return;

    // Record telemetry for chip selections
    if (option != null) {
      unawaited(ref.read(_telemetryServiceProvider).recordChipSelected(
            option: option,
            groupId: groupId ?? '',
            bandStatus: widget.bandStatus,
            conversationId: widget.conversationId,
            sessionId: _session!.sessionId,
          ));
    }

    setState(() => _sending = true);

    try {
      final service = ref.read(_coreSessionServiceProvider);
      final updated = await service.respond(
        sessionId: _session!.sessionId,
        content: content,
        optionId: optionId,
        semanticValue: semanticValue,
        modelWriteEffect: modelWriteEffect,
        isFreeform: isFreeform,
      );
      if (mounted) {
        setState(() {
          _session = updated;
          _sending = false;
          _showFreeformInput = false;
        });
        _freeformController.clear();
        _scrollToBottom();
      }
    } catch (e) {
      if (mounted) {
        setState(() => _sending = false);
      }
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _closeSession() async {
    final session = _session;
    if (session == null) {
      if (mounted) Navigator.of(context).pop();
      return;
    }
    try {
      final service = ref.read(_coreSessionServiceProvider);
      await service.closeSession(session.sessionId);
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              context.l10n.networkErrorRetry,
            ),
          ),
        );
      }
      return;
    }
    if (mounted) Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    final maxHeight = MediaQuery.of(context).size.height * 0.85;
    return Container(
      constraints: BoxConstraints(maxHeight: maxHeight),
      decoration: BoxDecoration(
        color: DS.surfacePrimary,
        borderRadius:
            const BorderRadius.vertical(top: Radius.circular(DS.radius20)),
        boxShadow: DS.shadowLg,
      ),
      child: SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            _buildHandle(),
            _buildHeader(),
            Flexible(child: _buildBody()),
            if (!(_session?.isExited ?? false)) _buildInputArea(),
          ],
        ),
      ),
    );
  }

  Widget _buildHandle() => Center(
        child: Container(
          margin: const EdgeInsets.only(top: DS.spacing12),
          width: 40,
          height: 4,
          decoration: BoxDecoration(
            color: DS.borderSubtle,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
      );

  Widget _buildHeader() {
    final session = _session;
    return Padding(
      padding: const EdgeInsets.fromLTRB(
          DS.spacing20, DS.spacing12, DS.spacing12, 0),
      child: Row(
        children: [
          Container(
            width: 32,
            height: 32,
            decoration: BoxDecoration(
              color: DS.brandPrimary.withValues(alpha: 0.1),
              shape: BoxShape.circle,
            ),
            child: Icon(Icons.auto_fix_high_rounded,
                size: 18, color: DS.brandPrimary),
          ),
          const SizedBox(width: DS.spacing10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Aurora 深度校准',
                  style: DS.titleMedium.copyWith(
                    color: DS.textPrimary,
                    fontWeight: DS.fontWeightBold,
                  ),
                ),
                if (session != null && session.scope.isNotEmpty)
                  Text(
                    session.scope,
                    style: TextStyle(
                        color: DS.textSecondary, fontSize: DS.fontSizeXs),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
              ],
            ),
          ),
          // Turn counter
          if (session != null && session.isActive)
            Container(
              padding: const EdgeInsets.symmetric(
                  horizontal: DS.spacing8, vertical: DS.spacing4),
              decoration: BoxDecoration(
                color: DS.borderSubtle,
                borderRadius: BorderRadius.circular(999),
              ),
              child: Text(
                '${session.turnsRemaining} 轮剩余',
                style: TextStyle(color: DS.textSecondary, fontSize: 11),
              ),
            ),
          const SizedBox(width: DS.spacing8),
          IconButton(
            onPressed: _closeSession,
            icon: Icon(Icons.close, size: 20, color: DS.textSecondary),
            tooltip: context.l10n.auroraExitCalibration,
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
          ),
        ],
      ),
    );
  }

  Widget _buildBody() {
    if (_loading) return _buildLoading();
    if (_error != null) return _buildError();
    final session = _session!;
    return FadeTransition(
      opacity: _entryAnimation,
      child: ListView(
        controller: _scrollController,
        padding: const EdgeInsets.fromLTRB(
            DS.spacing16, DS.spacing16, DS.spacing16, DS.spacing8),
        children: [
          ...session.messages.map(_buildMessage),
          if (_sending) _buildTypingIndicator(),
          if (session.isExited && session.calibrationResult != null)
            _buildCalibrationResult(session.calibrationResult!),
          const SizedBox(height: DS.spacing16),
        ],
      ),
    );
  }

  Widget _buildLoading() => Padding(
        padding: const EdgeInsets.all(DS.spacing32),
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const CircularProgressIndicator(strokeWidth: 2),
              const SizedBox(height: DS.spacing12),
              Text(context.l10n.auroraPreparing,
                  style: TextStyle(color: DS.textSecondary)),
            ],
          ),
        ),
      );

  Widget _buildError() => Padding(
        padding: const EdgeInsets.all(DS.spacing24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.error_outline, color: DS.error, size: 40),
            const SizedBox(height: DS.spacing12),
            Text(_error!,
                textAlign: TextAlign.center,
                style: TextStyle(color: DS.textSecondary)),
            const SizedBox(height: DS.spacing16),
            TextButton(
                onPressed: () => Navigator.of(context).pop(),
                child: Text(context.l10n.auroraClose)),
          ],
        ),
      );

  Widget _buildMessage(AuroraCoreMessage msg) {
    if (msg.isAurora) {
      return _AuroraMessageBubble(message: msg);
    } else {
      return _UserMessageBubble(message: msg);
    }
  }

  Widget _buildTypingIndicator() => Padding(
        padding: const EdgeInsets.only(top: DS.spacing8, bottom: DS.spacing4),
        child: Row(
          children: [
            Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: DS.brandPrimary.withValues(alpha: 0.08),
                shape: BoxShape.circle,
              ),
              child: Icon(Icons.auto_fix_high_rounded,
                  size: 16, color: DS.brandPrimary),
            ),
            const SizedBox(width: DS.spacing10),
            const _TypingDots(),
          ],
        ),
      );

  Widget _buildCalibrationResult(AuroraCalibrationResult result) {
    if (result.strategyChanges.isEmpty && result.summary.isEmpty) {
      return const SizedBox.shrink();
    }
    return Container(
      margin: const EdgeInsets.only(top: DS.spacing16),
      padding: const EdgeInsets.all(DS.spacing14),
      decoration: BoxDecoration(
        color: DS.success.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(DS.radius12),
        border: Border.all(color: DS.success.withValues(alpha: 0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.check_circle_outline_rounded,
                  size: 16, color: DS.success),
              const SizedBox(width: DS.spacing8),
              Text(
                '校准完成',
                style: DS.bodySmall.copyWith(
                    color: DS.success, fontWeight: DS.fontWeightSemibold),
              ),
            ],
          ),
          if (result.strategyChanges.isNotEmpty) ...[
            const SizedBox(height: DS.spacing10),
            ...result.strategyChanges.map((change) => Padding(
                  padding: const EdgeInsets.only(bottom: DS.spacing4),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Padding(
                        padding: const EdgeInsets.only(top: 4),
                        child: Container(
                          width: 4,
                          height: 4,
                          decoration: BoxDecoration(
                            color: DS.success,
                            shape: BoxShape.circle,
                          ),
                        ),
                      ),
                      const SizedBox(width: DS.spacing8),
                      Expanded(
                        child: Text(
                          change,
                          style: DS.bodySmall.copyWith(color: DS.textPrimary),
                        ),
                      ),
                    ],
                  ),
                )),
          ],
          const SizedBox(height: DS.spacing12),
          Text(
            'Aurora 已退回后台',
            style: DS.bodySmall.copyWith(color: DS.textSecondary),
          ),
          const SizedBox(height: DS.spacing8),
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: Text(context.l10n.auroraClose),
            ),
          ),
        ],
      ),
    );
  }

  // ── Input area ─────────────────────────────────────────────────

  Widget _buildInputArea() {
    final session = _session;
    if (session == null) return const SizedBox.shrink();

    final topGroup = session.topOptionGroup;
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        if (topGroup != null && !_showFreeformInput)
          _buildOptionChips(topGroup, session),
        if (_showFreeformInput) _buildFreeformInput(session),
        const SizedBox(height: DS.spacing8),
      ],
    );
  }

  Widget _buildOptionChips(
      AuroraPredictedReplyGroup group, AuroraCoreSession session) {
    return Container(
      padding: const EdgeInsets.fromLTRB(
          DS.spacing16, DS.spacing12, DS.spacing16, 0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          if (group.question.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing10),
              child: Text(
                group.question,
                style: DS.bodyMedium.copyWith(color: DS.textPrimary),
              ),
            ),
          if (group.contextNote.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing8),
              child: Text(
                group.contextNote,
                style: DS.bodySmall.copyWith(color: DS.textSecondary),
              ),
            ),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              // Primary options
              ...group.primaryOptions.map((option) => _SessionOptionChip(
                    option: option,
                    onTap: _sending
                        ? null
                        : () => _respond(
                              content: option.label,
                              optionId: option.id,
                              semanticValue: option.semanticValue,
                              modelWriteEffect:
                                  option.modelWriteEffect?.toJson(),
                              option: option,
                              groupId: group.groupId,
                            ),
                  )),
              // Freeform correction chip
              if (group.freeformOption != null)
                _SessionOptionChip(
                  option: group.freeformOption!,
                  onTap: _sending
                      ? null
                      : () => setState(() => _showFreeformInput = true),
                ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildFreeformInput(AuroraCoreSession session) {
    return Container(
      padding: const EdgeInsets.fromLTRB(
          DS.spacing16, DS.spacing12, DS.spacing16, 0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            '解释一下',
            style: DS.bodyMedium.copyWith(
                color: DS.textPrimary, fontWeight: DS.fontWeightSemibold),
          ),
          const SizedBox(height: DS.spacing8),
          TextField(
            controller: _freeformController,
            autofocus: true,
            maxLines: 3,
            minLines: 1,
            style: DS.bodyMedium.copyWith(color: DS.textPrimary),
            decoration: InputDecoration(
              hintText: context.l10n.auroraWhatDoYouThink,
              hintStyle: TextStyle(color: DS.textSecondary),
              filled: true,
              fillColor: DS.surfaceSecondary,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(DS.radius12),
                borderSide: BorderSide(color: DS.borderSubtle),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(DS.radius12),
                borderSide: BorderSide(color: DS.borderSubtle),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(DS.radius12),
                borderSide: BorderSide(color: DS.brandPrimary, width: 1.5),
              ),
              contentPadding: const EdgeInsets.all(DS.spacing12),
            ),
          ),
          const SizedBox(height: DS.spacing10),
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              TextButton(
                onPressed: () => setState(() {
                  _showFreeformInput = false;
                  _freeformController.clear();
                }),
                child: Text(context.l10n.toolsWbCancel),
              ),
              const SizedBox(width: DS.spacing8),
              FilledButton(
                onPressed: _sending
                    ? null
                    : () {
                        final text = _freeformController.text.trim();
                        if (text.isEmpty) return;
                        _respond(
                          content: text,
                          optionId: 'freeform_correction',
                          semanticValue: 'freeform_correction',
                          isFreeform: true,
                        );
                      },
                style: FilledButton.styleFrom(
                  backgroundColor: DS.brandPrimary,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(DS.radius8),
                  ),
                ),
                child: Text(context.l10n.auroraSend),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// ── Message bubbles ────────────────────────────────────────────────────────────

class _AuroraMessageBubble extends StatefulWidget {
  const _AuroraMessageBubble({required this.message});
  final AuroraCoreMessage message;

  @override
  State<_AuroraMessageBubble> createState() => _AuroraMessageBubbleState();
}

class _AuroraMessageBubbleState extends State<_AuroraMessageBubble>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _fadeAnim;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 300),
    );
    _fadeAnim = CurvedAnimation(parent: _controller, curve: Curves.easeIn);
    _controller.forward();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _fadeAnim,
      child: Padding(
        padding: const EdgeInsets.only(bottom: DS.spacing12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 28,
              height: 28,
              decoration: BoxDecoration(
                color: DS.brandPrimary.withValues(alpha: 0.08),
                shape: BoxShape.circle,
              ),
              child: Icon(
                Icons.auto_fix_high_rounded,
                size: 14,
                color: DS.brandPrimary,
              ),
            ),
            const SizedBox(width: DS.spacing10),
            Flexible(
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: DS.spacing12,
                  vertical: DS.spacing10,
                ),
                decoration: BoxDecoration(
                  color: DS.brandPrimary.withValues(alpha: 0.05),
                  borderRadius: const BorderRadius.only(
                    topRight: Radius.circular(DS.radius12),
                    bottomLeft: Radius.circular(DS.radius12),
                    bottomRight: Radius.circular(DS.radius12),
                  ),
                  border: Border.all(
                      color: DS.brandPrimary.withValues(alpha: 0.12)),
                ),
                child: Text(
                  widget.message.content,
                  style: DS.bodyMedium
                      .copyWith(color: DS.textPrimary, height: 1.5),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _UserMessageBubble extends StatelessWidget {
  const _UserMessageBubble({required this.message});
  final AuroraCoreMessage message;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: DS.spacing12),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.end,
        children: [
          Flexible(
            child: Container(
              padding: const EdgeInsets.symmetric(
                horizontal: DS.spacing12,
                vertical: DS.spacing10,
              ),
              decoration: BoxDecoration(
                color: DS.info.withValues(alpha: 0.08),
                borderRadius: const BorderRadius.only(
                  topLeft: Radius.circular(DS.radius12),
                  topRight: Radius.circular(DS.radius12),
                  bottomLeft: Radius.circular(DS.radius12),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    message.content,
                    style: DS.bodyMedium.copyWith(color: DS.textPrimary),
                  ),
                  if (message.isFreeform)
                    Padding(
                      padding: const EdgeInsets.only(top: DS.spacing4),
                      child: Text(
                        '自由描述',
                        style: DS.bodySmall.copyWith(color: DS.textSecondary),
                      ),
                    ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Option chip ────────────────────────────────────────────────────────────────

class _SessionOptionChip extends StatelessWidget {
  const _SessionOptionChip({
    required this.option,
    required this.onTap,
  });

  final AuroraPredictedReplyOption option;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final isDisconfirming = option.isDisconfirming || option.isFreeform;
    final color = isDisconfirming ? DS.textSecondary : DS.brandPrimary;
    return GestureDetector(
      onTap: onTap,
      child: AnimatedOpacity(
        opacity: onTap == null ? 0.5 : 1.0,
        duration: const Duration(milliseconds: 150),
        child: Container(
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing14,
            vertical: DS.spacing8,
          ),
          decoration: BoxDecoration(
            color: isDisconfirming
                ? Colors.transparent
                : color.withValues(alpha: 0.06),
            borderRadius: BorderRadius.circular(999),
            border: Border.all(
              color: isDisconfirming
                  ? DS.borderSubtle
                  : color.withValues(alpha: 0.25),
            ),
          ),
          child: Text(
            option.label,
            style: DS.bodySmall.copyWith(
              color: isDisconfirming ? DS.textSecondary : color,
              fontWeight:
                  isDisconfirming ? DS.fontWeightRegular : DS.fontWeightMedium,
            ),
          ),
        ),
      ),
    );
  }
}

// ── Typing indicator ───────────────────────────────────────────────────────────

class _TypingDots extends StatefulWidget {
  const _TypingDots();

  @override
  State<_TypingDots> createState() => _TypingDotsState();
}

class _TypingDotsState extends State<_TypingDots>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (_, __) {
        final phase = _controller.value;
        return Row(
          children: List.generate(3, (i) {
            final opacity = ((phase * 3 - i) % 1).clamp(0.2, 1.0);
            return Padding(
              padding: const EdgeInsets.symmetric(horizontal: 2),
              child: Opacity(
                opacity: opacity,
                child: Container(
                  width: 6,
                  height: 6,
                  decoration: BoxDecoration(
                    color: DS.brandPrimary,
                    shape: BoxShape.circle,
                  ),
                ),
              ),
            );
          }),
        );
      },
    );
  }
}
