import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/aurora/data/models/aurora_core_session.dart';
import 'package:sparkle/features/aurora/data/services/aurora_core_session_service.dart';
import 'package:sparkle/features/aurora/data/services/aurora_telemetry_service.dart';
import 'package:sparkle/features/chat/presentation/providers/aurora_status_provider.dart';

// ── Provider ──────────────────────────────────────────────────────────────────

final auroraCoreSessionServiceProvider =
    Provider<AuroraCoreSessionClient>((ref) {
  return AuroraCoreSessionService(ref.read(apiClientProvider));
});

final _telemetryServiceProvider = Provider<AuroraTelemetryService>((ref) {
  return AuroraTelemetryService(ref.read(apiClientProvider));
});

final auroraCoreSessionStateProvider = StateNotifierProvider<
    AuroraCoreSessionStateNotifier, AuroraCoreSessionResumeState>((ref) {
  return AuroraCoreSessionStateNotifier(
    ref.read(auroraCoreSessionServiceProvider),
  );
});

enum AuroraCoreSessionSheetSize { half, expanded, full }

class AuroraCoreSessionResumeState {
  const AuroraCoreSessionResumeState({this.session, this.restored = false});

  factory AuroraCoreSessionResumeState.fromJson(Map<String, dynamic> json) {
    final rawSession = json['session'];
    return AuroraCoreSessionResumeState(
      session: rawSession is Map<String, dynamic>
          ? AuroraCoreSession.fromJson(rawSession)
          : rawSession is Map
              ? AuroraCoreSession.fromJson(
                  Map<String, dynamic>.from(rawSession))
              : null,
      restored: json['restored'] as bool? ?? true,
    );
  }

  final AuroraCoreSession? session;
  final bool restored;

  bool get hasResumableSession => session?.isResumable ?? false;
  bool get hasExpiredSession => session?.isExpired ?? false;
  String? get resumeToken => session?.resumeToken;

  Map<String, dynamic> toJson() => {
        'session': session?.toJson(),
        'restored': restored,
      };
}

class AuroraCoreSessionStateNotifier
    extends StateNotifier<AuroraCoreSessionResumeState> {
  AuroraCoreSessionStateNotifier(this._client)
      : super(const AuroraCoreSessionResumeState()) {
    unawaited(_restore());
  }

  static const _prefsKey = 'aurora_core_session.resume_state.v1';

  final AuroraCoreSessionClient _client;
  bool _hasLiveUpdate = false;

  Future<void> refreshFromBackend() async {
    try {
      final session = await _client.getCurrentSession();
      if (session == null) {
        await clear();
      } else {
        await setSession(session);
      }
    } catch (_) {
      // Local state is still useful while offline or during a cold reconnect.
    }
  }

  Future<AuroraCoreSession?> resumeStoredSession() async {
    final token = state.resumeToken;
    if (token == null || token.isEmpty) return null;
    try {
      final session = await _client.resumeSession(token);
      await setSession(session);
      return session;
    } catch (_) {
      await markStoredSessionExpired();
      return state.session;
    }
  }

  Future<void> setSession(AuroraCoreSession? session) async {
    _hasLiveUpdate = true;
    state = AuroraCoreSessionResumeState(session: session, restored: true);
    await _persist();
  }

  Future<void> markStoredSessionExpired() async {
    final session = state.session;
    if (session == null) return;
    final expired = AuroraCoreSession.fromJson({
      ...session.toJson(),
      'status': 'expired',
      'resume_token': '',
      'pending_option_groups': <Map<String, dynamic>>[],
      'calibration_result': session.calibrationResult?.toJson() ??
          {
            'updates_applied': <Map<String, dynamic>>[],
            'summary': '',
            'user_visible_summary': '',
            'scope_completed': session.scope,
            'strategy_changes': <String>[],
            'state_patches': <Map<String, dynamic>>[],
            'next_changes': <String>[],
            'session_id': session.sessionId,
            'completed_at': DateTime.now().toIso8601String(),
          },
    });
    await setSession(expired);
  }

  Future<void> clear() async {
    _hasLiveUpdate = true;
    state = const AuroraCoreSessionResumeState(restored: true);
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_prefsKey);
    } catch (_) {}
  }

  Future<void> _restore() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final raw = prefs.getString(_prefsKey);
      if (raw == null || raw.isEmpty) {
        if (_hasLiveUpdate) return;
        state = const AuroraCoreSessionResumeState(restored: true);
        return;
      }
      final decoded = jsonDecode(raw);
      if (decoded is! Map) {
        await clear();
        return;
      }
      final restored = AuroraCoreSessionResumeState.fromJson(
        Map<String, dynamic>.from(decoded),
      );
      if (_hasLiveUpdate) return;
      final session = restored.session;
      if (session == null || !(session.isResumable || session.isExpired)) {
        await clear();
        return;
      }
      state = restored;
    } catch (_) {
      state = const AuroraCoreSessionResumeState(restored: true);
    }
  }

  Future<void> _persist() async {
    final session = state.session;
    if (session == null || !(session.isResumable || session.isExpired)) {
      await clear();
      return;
    }
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_prefsKey, jsonEncode(state.toJson()));
    } catch (_) {}
  }
}

class AuroraCoreSessionResumeBanner extends ConsumerWidget {
  const AuroraCoreSessionResumeBanner({
    this.conversationId,
    super.key,
  });

  final String? conversationId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final resumeState = ref.watch(auroraCoreSessionStateProvider);
    final session = resumeState.session;
    if (session == null || !session.isResumable) {
      return const SizedBox.shrink();
    }
    final l10n = context.l10n;
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        DS.spacing16,
        DS.spacing8,
        DS.spacing16,
        DS.spacing4,
      ),
      child: Semantics(
        button: true,
        label: l10n.auroraResumeAction,
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            borderRadius: BorderRadius.circular(DS.radius12),
            onTap: () {
              unawaited(
                showAuroraCoreSession(
                  context: context,
                  bandStatus: 'calibration_available',
                  wakeReasons: const ['standard_layer_uncertainty'],
                  conversationId: conversationId ?? session.conversationId,
                  resumeToken: session.resumeToken,
                ),
              );
            },
            child: Ink(
              decoration: BoxDecoration(
                color: DS.brandPrimary.withValues(alpha: 0.06),
                borderRadius: BorderRadius.circular(DS.radius12),
                border: Border.all(
                  color: DS.brandPrimary.withValues(alpha: 0.16),
                ),
              ),
              padding: const EdgeInsets.symmetric(
                horizontal: DS.spacing12,
                vertical: DS.spacing10,
              ),
              child: Row(
                children: [
                  Icon(Icons.restore_rounded, size: 18, color: DS.brandPrimary),
                  const SizedBox(width: DS.spacing8),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          l10n.auroraResumeTitle,
                          style: DS.bodySmall.copyWith(
                            color: DS.textPrimary,
                            fontWeight: DS.fontWeightSemibold,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          l10n.auroraResumeBannerSubtitle,
                          style: DS.bodySmall.copyWith(
                            color: DS.textSecondary,
                            height: 1.25,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: DS.spacing8),
                  Icon(Icons.chevron_right_rounded,
                      size: 20, color: DS.textSecondary),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

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
  AuroraCoreSessionEntryReason? entryReason,
  String? conversationId,
  String? scope,
  String sessionType = 'user_initiated',
  String? resumeToken,
  AuroraCoreSessionSheetSize initialSize = AuroraCoreSessionSheetSize.half,
  VoidCallback? onViewAdjustedPlan,
}) async {
  await showModalBottomSheet<void>(
    context: context,
    backgroundColor: Colors.transparent,
    isScrollControlled: true,
    isDismissible: false,
    enableDrag: false,
    builder: (ctx) => AuroraCoreSessionSheet(
      bandStatus: bandStatus,
      wakeReasons: wakeReasons,
      entryReason: entryReason,
      conversationId: conversationId,
      scope: scope,
      sessionType: sessionType,
      resumeToken: resumeToken,
      initialSize: initialSize,
      onViewAdjustedPlan: onViewAdjustedPlan,
    ),
  );
}

// ── Sheet widget ──────────────────────────────────────────────────────────────

class AuroraCoreSessionSheet extends ConsumerStatefulWidget {
  const AuroraCoreSessionSheet({
    required this.bandStatus,
    required this.wakeReasons,
    this.entryReason,
    this.conversationId,
    this.scope,
    this.sessionType = 'user_initiated',
    this.resumeToken,
    this.initialSize = AuroraCoreSessionSheetSize.half,
    this.onViewAdjustedPlan,
    super.key,
  });

  final String bandStatus;
  final List<String> wakeReasons;
  final AuroraCoreSessionEntryReason? entryReason;
  final String? conversationId;
  final String? scope;
  final String sessionType;
  final String? resumeToken;
  final AuroraCoreSessionSheetSize initialSize;
  final VoidCallback? onViewAdjustedPlan;

  @override
  ConsumerState<AuroraCoreSessionSheet> createState() =>
      _AuroraCoreSessionSheetState();
}

class _AuroraCoreSessionSheetState extends ConsumerState<AuroraCoreSessionSheet>
    with SingleTickerProviderStateMixin {
  AuroraCoreSession? _session;
  bool _loading = true;
  bool _sending = false;
  String? _error;
  final _freeformController = TextEditingController();
  bool _showFreeformInput = false;
  late AuroraCoreSessionSheetSize _sheetSize;
  late final AnimationController _entryController;
  late final Animation<double> _entryAnimation;
  final ScrollController _scrollController = ScrollController();
  bool _openedFromResumeState = false;

  @override
  void initState() {
    super.initState();
    _sheetSize = widget.initialSize;
    _entryController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 400),
    );
    _entryAnimation = CurvedAnimation(
      parent: _entryController,
      curve: Curves.easeOutCubic,
    );
    unawaited(_startSession());
  }

  @override
  void dispose() {
    _entryController.dispose();
    _freeformController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _startSession() async {
    final service = ref.read(auroraCoreSessionServiceProvider);
    final sessionStore = ref.read(auroraCoreSessionStateProvider.notifier);
    final storedSession = ref.read(auroraCoreSessionStateProvider).session;
    try {
      AuroraCoreSession session;
      if (widget.resumeToken?.isNotEmpty ?? false) {
        session = await service.resumeSession(widget.resumeToken!);
        _openedFromResumeState = true;
      } else if (storedSession?.isResumable ?? false) {
        session = storedSession!;
        _openedFromResumeState = true;
        unawaited(sessionStore.refreshFromBackend());
      } else {
        session = await service.startSession(
          conversationId: widget.conversationId,
          sessionType: widget.sessionType,
          scope: widget.scope,
          wakeReasons: widget.wakeReasons,
          bandStatus: widget.bandStatus,
          entryReason: widget.entryReason,
        );
      }
      await sessionStore.setSession(session);
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
      final service = ref.read(auroraCoreSessionServiceProvider);
      final updated = await service.respond(
        sessionId: _session!.sessionId,
        content: content,
        optionId: optionId,
        semanticValue: semanticValue,
        modelWriteEffect: modelWriteEffect,
        isFreeform: isFreeform,
      );
      if (mounted) {
        await ref
            .read(auroraCoreSessionStateProvider.notifier)
            .setSession(updated);
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
        unawaited(
          _scrollController.animateTo(
            _scrollController.position.maxScrollExtent,
            duration: const Duration(milliseconds: 300),
            curve: Curves.easeOut,
          ),
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
      final service = ref.read(auroraCoreSessionServiceProvider);
      final closed = await service.closeSession(session.sessionId);
      await ref
          .read(auroraCoreSessionStateProvider.notifier)
          .setSession(closed);
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

  Future<void> _pauseSession() async {
    final session = _session;
    if (session == null || !session.isActive) {
      return;
    }
    try {
      final service = ref.read(auroraCoreSessionServiceProvider);
      final paused = await service.pauseSession(session.sessionId);
      await ref
          .read(auroraCoreSessionStateProvider.notifier)
          .setSession(paused);
      if (mounted) {
        setState(() => _session = paused);
        Navigator.of(context).pop(paused.resumeToken);
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(context.l10n.networkErrorRetry)),
        );
      }
    }
  }

  Future<void> _resumePausedSession() async {
    if (_sending) return;
    setState(() => _sending = true);
    final resumed = await ref
        .read(auroraCoreSessionStateProvider.notifier)
        .resumeStoredSession();
    if (!mounted) return;
    setState(() {
      _session = resumed ?? _session;
      _sending = false;
      _openedFromResumeState = true;
    });
    _scrollToBottom();
  }

  Future<void> _startNewAfterExpired() async {
    await ref.read(auroraCoreSessionStateProvider.notifier).clear();
    if (!mounted) return;
    setState(() {
      _session = null;
      _loading = true;
      _sending = false;
      _error = null;
      _openedFromResumeState = false;
    });
    await _startSession();
  }

  @override
  Widget build(BuildContext context) {
    final heightFactor = switch (_sheetSize) {
      AuroraCoreSessionSheetSize.half => 0.56,
      AuroraCoreSessionSheetSize.expanded => 0.76,
      AuroraCoreSessionSheetSize.full => 0.94,
    };
    final maxHeight = MediaQuery.of(context).size.height * heightFactor;
    return AnimatedContainer(
      duration: const Duration(milliseconds: 220),
      curve: Curves.easeOutCubic,
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
    final l10n = context.l10n;
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
                  l10n.auroraCoreSessionTitle,
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
                l10n.auroraTurnsRemaining(session.turnsRemaining),
                style: TextStyle(color: DS.textSecondary, fontSize: 11),
              ),
            ),
          const SizedBox(width: DS.spacing8),
          if (session != null && session.isActive) ...[
            IconButton(
              onPressed: _pauseSession,
              icon:
                  Icon(Icons.pause_rounded, size: 20, color: DS.textSecondary),
              tooltip: l10n.auroraPauseCalibration,
              padding: EdgeInsets.zero,
              constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
            ),
            IconButton(
              onPressed: () => setState(() {
                _sheetSize = switch (_sheetSize) {
                  AuroraCoreSessionSheetSize.half =>
                    AuroraCoreSessionSheetSize.expanded,
                  AuroraCoreSessionSheetSize.expanded =>
                    AuroraCoreSessionSheetSize.full,
                  AuroraCoreSessionSheetSize.full =>
                    AuroraCoreSessionSheetSize.half,
                };
              }),
              icon: Icon(
                _sheetSize == AuroraCoreSessionSheetSize.full
                    ? Icons.unfold_less_rounded
                    : Icons.unfold_more_rounded,
                size: 20,
                color: DS.textSecondary,
              ),
              tooltip: _sheetSize == AuroraCoreSessionSheetSize.full
                  ? l10n.auroraShrinkSheet
                  : l10n.auroraExpandSheet,
              padding: EdgeInsets.zero,
              constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
            ),
          ],
          IconButton(
            onPressed: _closeSession,
            icon: Icon(Icons.close, size: 20, color: DS.textSecondary),
            tooltip: l10n.auroraExitCalibration,
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
    if (session.isExpired) {
      return _buildExpiredBody(session);
    }
    return FadeTransition(
      opacity: _entryAnimation,
      child: ListView(
        controller: _scrollController,
        padding: const EdgeInsets.fromLTRB(
            DS.spacing16, DS.spacing16, DS.spacing16, DS.spacing8),
        children: [
          if (_openedFromResumeState && session.isActive)
            _buildResumeNotice(context.l10n.auroraCoreSessionResumed),
          if (session.isPaused) _buildPausedResumeCard(),
          if (session.agenda?.hasContent ?? false)
            _buildAgendaCard(session.agenda!),
          ...session.messages.asMap().entries.map(
                (entry) => SparkleStaggerItem(
                  index: entry.key,
                  child: _buildMessage(entry.value),
                ),
              ),
          if (_sending) _buildTypingIndicator(),
          if (session.isExited && session.calibrationResult != null)
            _buildCalibrationResult(session.calibrationResult!),
          const SizedBox(height: DS.spacing16),
        ],
      ),
    );
  }

  Widget _buildAgendaCard(AuroraCoreAgenda agenda) {
    final activeIndex =
        agenda.items.indexWhere((item) => item.status == 'in_progress');
    return Container(
      margin: const EdgeInsets.only(bottom: DS.spacing14),
      padding: const EdgeInsets.all(DS.spacing14),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: BorderRadius.circular(DS.radius12),
        border: Border.all(color: DS.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.fact_check_outlined, size: 18, color: DS.brandPrimary),
              const SizedBox(width: DS.spacing8),
              Expanded(
                child: Text(
                  agenda.scope.isEmpty
                      ? context.l10n.auroraCoreSessionTitle
                      : agenda.scope,
                  style: DS.bodyMedium.copyWith(
                    color: DS.textPrimary,
                    fontWeight: DS.fontWeightSemibold,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              if (agenda.estimatedMinutes > 0)
                Text(
                  '${agenda.estimatedMinutes} min',
                  style: DS.bodySmall.copyWith(color: DS.textSecondary),
                ),
            ],
          ),
          if (agenda.preview.isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            Text(
              agenda.preview.take(3).join(' · '),
              style: DS.bodySmall.copyWith(
                color: DS.textSecondary,
                height: 1.35,
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ],
          if (agenda.items.isNotEmpty) ...[
            const SizedBox(height: DS.spacing12),
            ...agenda.items.asMap().entries.map(
                  (entry) => _AgendaStepRow(
                    item: entry.value,
                    isLast: entry.key == agenda.items.length - 1,
                    isActive: entry.key == activeIndex,
                  ),
                ),
          ],
          if (agenda.interruptionPolicyLabel.isNotEmpty ||
              agenda.resumeHint.isNotEmpty) ...[
            const SizedBox(height: DS.spacing10),
            DecoratedBox(
              decoration: BoxDecoration(
                color: DS.info.withValues(alpha: 0.07),
                borderRadius: BorderRadius.circular(DS.radius8),
                border: Border.all(color: DS.info.withValues(alpha: 0.14)),
              ),
              child: Padding(
                padding: const EdgeInsets.all(DS.spacing10),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(
                      Icons.pause_circle_outline_rounded,
                      size: 16,
                      color: DS.info,
                    ),
                    const SizedBox(width: DS.spacing8),
                    Expanded(
                      child: Text(
                        agenda.interruptionPolicyLabel.isNotEmpty
                            ? agenda.interruptionPolicyLabel
                            : agenda.resumeHint,
                        style: DS.bodySmall.copyWith(
                          color: DS.textPrimary,
                          height: 1.35,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
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
    if (result.strategyChanges.isEmpty &&
        result.statePatches.isEmpty &&
        result.nextChanges.isEmpty &&
        result.userVisibleSummary.isEmpty) {
      return const SizedBox.shrink();
    }
    final l10n = context.l10n;
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
                l10n.auroraCalibrationComplete,
                style: DS.bodySmall.copyWith(
                    color: DS.success, fontWeight: DS.fontWeightSemibold),
              ),
            ],
          ),
          if (result.userVisibleSummary.isNotEmpty) ...[
            const SizedBox(height: DS.spacing10),
            Text(
              result.userVisibleSummary,
              style: DS.bodySmall.copyWith(color: DS.textPrimary, height: 1.45),
            ),
          ],
          if (result.statePatches.isNotEmpty) ...[
            const SizedBox(height: DS.spacing12),
            Text(
              l10n.auroraStatePatchesTitle,
              style: DS.bodySmall.copyWith(
                color: DS.textSecondary,
                fontWeight: DS.fontWeightSemibold,
              ),
            ),
            const SizedBox(height: DS.spacing6),
            ...result.statePatches.take(4).map((patch) {
              final key = patch['state_key']?.toString() ?? '';
              final next = patch['new_value']?.toString() ?? '';
              return _ResultBullet(text: '$key -> $next');
            }),
          ],
          if (result.strategyChanges.isNotEmpty) ...[
            const SizedBox(height: DS.spacing10),
            ...result.strategyChanges
                .map((change) => _ResultBullet(text: change)),
          ],
          if (result.nextChanges.isNotEmpty) ...[
            const SizedBox(height: DS.spacing12),
            Text(
              l10n.auroraNextChangesTitle,
              style: DS.bodySmall.copyWith(
                color: DS.textSecondary,
                fontWeight: DS.fontWeightSemibold,
              ),
            ),
            const SizedBox(height: DS.spacing6),
            ...result.nextChanges.map((change) => _ResultBullet(text: change)),
          ],
          const SizedBox(height: DS.spacing12),
          Text(
            l10n.auroraReturnedToBackground,
            style: DS.bodySmall.copyWith(color: DS.textSecondary),
          ),
          const SizedBox(height: DS.spacing8),
          Align(
            alignment: Alignment.centerRight,
            child: Wrap(
              spacing: DS.spacing8,
              children: [
                if (widget.onViewAdjustedPlan != null)
                  TextButton.icon(
                    onPressed: () {
                      Navigator.of(context).pop();
                      widget.onViewAdjustedPlan?.call();
                    },
                    icon: const Icon(Icons.route_outlined, size: 16),
                    label: Text(l10n.auroraViewAdjustedPlan),
                  ),
                TextButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: Text(l10n.auroraClose),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildResumeNotice(String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: DS.spacing12),
      child: Semantics(
        label: text,
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: DS.info.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(DS.radius12),
            border: Border.all(color: DS.info.withValues(alpha: 0.18)),
          ),
          child: Padding(
            padding: const EdgeInsets.all(DS.spacing12),
            child: Row(
              children: [
                Icon(Icons.restore_rounded, size: 18, color: DS.info),
                const SizedBox(width: DS.spacing8),
                Expanded(
                  child: Text(
                    text,
                    style: DS.bodySmall.copyWith(
                      color: DS.textPrimary,
                      height: 1.35,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildPausedResumeCard() {
    final l10n = context.l10n;
    return Container(
      margin: const EdgeInsets.only(bottom: DS.spacing14),
      padding: const EdgeInsets.all(DS.spacing14),
      decoration: BoxDecoration(
        color: DS.brandPrimary.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(DS.radius12),
        border: Border.all(color: DS.brandPrimary.withValues(alpha: 0.16)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.play_circle_outline_rounded,
                  size: 18, color: DS.brandPrimary),
              const SizedBox(width: DS.spacing8),
              Expanded(
                child: Text(
                  l10n.auroraResumeTitle,
                  style: DS.bodyMedium.copyWith(
                    color: DS.textPrimary,
                    fontWeight: DS.fontWeightSemibold,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing6),
          Text(
            l10n.auroraResumeSubtitle,
            style: DS.bodySmall.copyWith(color: DS.textSecondary, height: 1.4),
          ),
          const SizedBox(height: DS.spacing12),
          Align(
            alignment: Alignment.centerRight,
            child: FilledButton.icon(
              onPressed: _sending ? null : _resumePausedSession,
              icon: const Icon(Icons.restore_rounded, size: 16),
              label: Text(l10n.auroraResumeAction),
              style: FilledButton.styleFrom(
                backgroundColor: DS.brandPrimary,
                foregroundColor: DS.textOnPrimary,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(DS.radius8),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildExpiredBody(AuroraCoreSession session) {
    final l10n = context.l10n;
    final summary = session.calibrationResult?.userVisibleSummary ?? '';
    return FadeTransition(
      opacity: _entryAnimation,
      child: ListView(
        controller: _scrollController,
        padding: const EdgeInsets.fromLTRB(
            DS.spacing16, DS.spacing16, DS.spacing16, DS.spacing16),
        children: [
          Container(
            padding: const EdgeInsets.all(DS.spacing16),
            decoration: BoxDecoration(
              color: DS.warning.withValues(alpha: 0.07),
              borderRadius: BorderRadius.circular(DS.radius12),
              border: Border.all(color: DS.warning.withValues(alpha: 0.18)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.schedule_rounded, size: 18, color: DS.warning),
                    const SizedBox(width: DS.spacing8),
                    Expanded(
                      child: Text(
                        l10n.auroraSessionExpiredTitle,
                        style: DS.bodyMedium.copyWith(
                          color: DS.textPrimary,
                          fontWeight: DS.fontWeightSemibold,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: DS.spacing8),
                Text(
                  l10n.auroraSessionExpiredSubtitle,
                  style: DS.bodySmall.copyWith(
                    color: DS.textSecondary,
                    height: 1.45,
                  ),
                ),
                if (summary.isNotEmpty) ...[
                  const SizedBox(height: DS.spacing12),
                  Text(
                    l10n.auroraLastSessionSummary,
                    style: DS.bodySmall.copyWith(
                      color: DS.textSecondary,
                      fontWeight: DS.fontWeightSemibold,
                    ),
                  ),
                  const SizedBox(height: DS.spacing6),
                  Text(
                    summary,
                    style: DS.bodySmall.copyWith(
                      color: DS.textPrimary,
                      height: 1.45,
                    ),
                  ),
                ],
                const SizedBox(height: DS.spacing14),
                Wrap(
                  alignment: WrapAlignment.end,
                  spacing: DS.spacing8,
                  runSpacing: DS.spacing8,
                  children: [
                    TextButton(
                      onPressed: () => Navigator.of(context).pop(),
                      child: Text(l10n.auroraJustChat),
                    ),
                    FilledButton.icon(
                      onPressed: _startNewAfterExpired,
                      icon: const Icon(Icons.auto_fix_high_rounded, size: 16),
                      label: Text(l10n.auroraStartNewSession),
                      style: FilledButton.styleFrom(
                        backgroundColor: DS.brandPrimary,
                        foregroundColor: DS.textOnPrimary,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(DS.radius8),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: DS.spacing12),
          ...session.messages.map(_buildMessage),
        ],
      ),
    );
  }

  // ── Input area ─────────────────────────────────────────────────

  Widget _buildInputArea() {
    final session = _session;
    if (session == null) return const SizedBox.shrink();

    if (!session.canInteract) return const SizedBox.shrink();

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
            context.l10n.auroraExplainPrompt,
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
                        unawaited(
                          _respond(
                            content: text,
                            optionId: 'freeform_correction',
                            semanticValue: 'freeform_correction',
                            isFreeform: true,
                          ),
                        );
                      },
                style: FilledButton.styleFrom(
                  backgroundColor: DS.brandPrimary,
                  foregroundColor: DS.textOnPrimary,
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

class _ResultBullet extends StatelessWidget {
  const _ResultBullet({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: DS.spacing4),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.only(top: 7),
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
                text,
                style:
                    DS.bodySmall.copyWith(color: DS.textPrimary, height: 1.35),
              ),
            ),
          ],
        ),
      );
}

class _AgendaStepRow extends StatelessWidget {
  const _AgendaStepRow({
    required this.item,
    required this.isLast,
    required this.isActive,
  });

  final AuroraCoreAgendaItem item;
  final bool isLast;
  final bool isActive;

  @override
  Widget build(BuildContext context) {
    final color = item.isDone
        ? DS.success
        : isActive
            ? DS.brandPrimary
            : DS.textTertiary;
    final icon = item.isDone
        ? Icons.check_circle_rounded
        : isActive
            ? Icons.radio_button_checked_rounded
            : Icons.radio_button_unchecked_rounded;
    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Column(
            children: [
              Icon(icon, size: 16, color: color),
              if (!isLast)
                Expanded(
                  child: Container(
                    width: 1,
                    margin: const EdgeInsets.symmetric(vertical: 2),
                    color: DS.borderSubtle,
                  ),
                ),
            ],
          ),
          const SizedBox(width: DS.spacing8),
          Expanded(
            child: Padding(
              padding: EdgeInsets.only(
                bottom: isLast ? 0 : DS.spacing8,
              ),
              child: Text(
                item.label,
                style: DS.bodySmall.copyWith(
                  color: item.isDone || isActive
                      ? DS.textPrimary
                      : DS.textSecondary,
                  fontWeight:
                      isActive ? DS.fontWeightSemibold : DS.fontWeightRegular,
                  height: 1.3,
                ),
              ),
            ),
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
    unawaited(_controller.forward());
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
                        context.l10n.auroraFreeformLabel,
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
    return Semantics(
      button: true,
      label: option.label,
      child: GestureDetector(
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
            child: ExcludeSemantics(
              child: Text(
                option.label,
                style: DS.bodySmall.copyWith(
                  color: isDisconfirming ? DS.textSecondary : color,
                  fontWeight: isDisconfirming
                      ? DS.fontWeightRegular
                      : DS.fontWeightMedium,
                ),
              ),
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
    );
    unawaited(_controller.repeat());
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
