import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/constants/app_constants.dart';
import 'package:sparkle/core/design/components/atoms/semantic_pill.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/memory_api_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/chat/presentation/providers/aurora_status_provider.dart';
import 'package:sparkle/features/chat/presentation/widgets/status_awareness_bar.dart';
import 'package:sparkle/features/chat/presentation/widgets/working_memory_drawer.dart';

/// §5 空间纪律 / D8 推送宪法第 5 条的 chat 域收容件。
///
/// chat 屏撤出常驻系统面板（S8）后的三个合法系统件落点（§5.2）：
/// - [ChatInboxEntryIcon]：收件箱唯一入口（AppBar action），并承接
///   Aurora 快照的轻量轮询与 BGM 感官联动（原常驻 StatusAwarenessBar 的
///   生命周期职责迁移到此）；
/// - [ChatWorkingMemorySignal]：「AI 当前记住」消息旁微内联信号
///   （chip 级，0 条时不渲染——S8 审计「空状态占最贵顶部位置」）；
/// - [ChatAuroraConfirmSignal]：Aurora 确认队列的按需单行入口，
///   仅在有待确认/风险/可校准动作时出现，点开按需确认面板。
///
/// 本文件内所有件在无数据时不占任何面积。

/// 会话工作记忆条数（null = 不可用/关闭，UI 不渲染）。
final chatWorkingMemoryCountProvider =
    FutureProvider.family<int?, String?>((ref, sessionId) async {
  if (!AppFeatureFlags.enableWorkingMemoryDrawer) {
    return null;
  }
  final trimmed = sessionId?.trim() ?? '';
  if (trimmed.isEmpty) {
    return null;
  }
  try {
    final session = await ref
        .read(memoryApiServiceProvider)
        .getWorkingMemorySession(sessionId: trimmed);
    return session.items.length;
  } catch (_) {
    return null;
  }
});

/// Aurora 快照是否携带「需要用户动作」的确认队列。
bool auroraSnapshotActionable(AuroraControlSurfaceSnapshot? snapshot) {
  if (snapshot == null || !snapshot.auroraActive) {
    return false;
  }
  const actionableStatuses = {
    'needs_confirm',
    'risk_found',
    'calibration_available',
  };
  return actionableStatuses.contains(snapshot.overallStatus);
}

/// AppBar 收件箱入口（D8 第 5 条：app 内主动性集中制）。
///
/// 同时承接 Aurora 快照轮询（自有 Timer，独立于 [StatusAwarenessBar]
/// 的 startPeriodicRefresh 生命周期，避免双实例互相停表）与 BGM 感官
/// 联动（原常驻 bar 的 `_syncAuroraSensoryState` 职责迁移）。
class ChatInboxEntryIcon extends ConsumerStatefulWidget {
  const ChatInboxEntryIcon({
    required this.conversationId,
    super.key,
  });

  final String? conversationId;

  @override
  ConsumerState<ChatInboxEntryIcon> createState() =>
      _ChatInboxEntryIconState();
}

class _ChatInboxEntryIconState extends ConsumerState<ChatInboxEntryIcon> {
  static const _refreshInterval = Duration(seconds: 30);
  Timer? _refreshTimer;
  String? _lastSyncedAuroraStatus;
  Object? _auroraBgmToken;

  @override
  void initState() {
    super.initState();
    _refreshTimer = Timer.periodic(_refreshInterval, (_) => _refresh());
    unawaited(_refresh());
    ref.listenManual(auroraStatusProvider, (previous, next) {
      _syncAuroraSensoryState(next);
    });
  }

  @override
  void didUpdateWidget(covariant ChatInboxEntryIcon oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.conversationId != widget.conversationId) {
      unawaited(_refresh());
    }
  }

  Future<void> _refresh() async {
    await ref.read(auroraStatusProvider.notifier).refresh(
          conversationId: widget.conversationId,
        );
  }

  Future<void> _applyAuroraSensoryState(
    String? nextStatus,
    String? previousStatus,
  ) async {
    try {
      final enabled = await SensoryFeedbackService.isAuroraLinkageEnabled();
      _auroraBgmToken = await BgmService.applyAuroraStatus(
        status: nextStatus,
        token: _auroraBgmToken,
        sceneTrack: BgmTrack.chat,
        enabled: enabled,
      );
      if (enabled && previousStatus != null && nextStatus != null) {
        await SensoryFeedbackService.emitAuroraEvent(
          AuroraSensoryEvent.statusChanged,
          enableSound: nextStatus == 'calibration_available',
        );
      }
    } catch (_) {
      // Sensory linkage is deliberately best effort.
    }
  }

  void _syncAuroraSensoryState(AuroraControlSurfaceSnapshot? snapshot) {
    final nextStatus = snapshot?.overallStatus;
    if (_lastSyncedAuroraStatus == nextStatus) {
      return;
    }
    final previousStatus = _lastSyncedAuroraStatus;
    _lastSyncedAuroraStatus = nextStatus;
    unawaited(_applyAuroraSensoryState(nextStatus, previousStatus));
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    unawaited(BgmService.clearAuroraStatus(_auroraBgmToken));
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final snapshot = ref.watch(auroraStatusProvider);
    final actionable = auroraSnapshotActionable(snapshot);
    // B4-INBOX: badge carries the real unprocessed confirmation count when
    // the engine provides it; otherwise falls back to the plain dot, so the
    // B3-CHAT containment semantics (actionable -> visible) are unchanged.
    final pendingCount = snapshot?.pendingConfirmCount ?? 0;
    final badgeLabel = pendingCount > 0
        ? Text(
            pendingCount > 99 ? '99+' : '$pendingCount',
            style: DS.labelSmall.copyWith(
              color: DS.onBrandPrimary,
              fontWeight: DS.fontWeightBold,
              fontFeatures: const [FontFeature.tabularFigures()],
            ),
          )
        : null;
    return SparkleIconButton(
      icon: Badge(
        isLabelVisible: actionable,
        backgroundColor: DS.info,
        smallSize: 8,
        label: badgeLabel,
        child: Icon(
          Icons.inbox_rounded,
          color: actionable ? DS.info : DS.textSecondary,
        ),
      ),
      onPressed: () => unawaited(
        context.push('/notification-center'),
      ),
      semanticLabel: context.l10n.chatOpenInboxButton,
      variant: ButtonVariant.ghost,
    );
  }
}

/// 「AI 当前记住」微内联信号（§5.2 内联微件，chip 级）。
///
/// 仅在本会话工作记忆 >0 条时渲染；点开按需抽屉承载原
/// [ChatWorkingMemoryPanel] 全量操作（查看原 turn/忘记/标记正确）。
class ChatWorkingMemorySignal extends ConsumerWidget {
  const ChatWorkingMemorySignal({
    required this.sessionId,
    required this.onViewSource,
    super.key,
  });

  final String? sessionId;
  final ValueChanged<String> onViewSource;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (!AppFeatureFlags.enableWorkingMemoryDrawer) {
      return const SizedBox.shrink();
    }
    final count = ref.watch(chatWorkingMemoryCountProvider(sessionId));
    final resolved = count.valueOrNull;
    if (resolved == null || resolved <= 0) {
      return const SizedBox.shrink();
    }
    return SemanticPill(
      label: context.l10n.chatMemoryInlineChip(resolved),
      tone: PillTone.info,
      dense: true,
      icon: Icons.psychology_alt_outlined,
      onTap: () => _openMemorySheet(context),
    );
  }

  void _openMemorySheet(BuildContext context) {
    unawaited(
      showSensoryModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
        builder: (sheetContext) => FractionallySizedBox(
          heightFactor: 0.62,
          child: SafeArea(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(
                    DS.spacing16,
                    DS.spacing12,
                    DS.spacing16,
                    0,
                  ),
                  child: Text(
                    context.l10n.chatMemoryInlineSheetTitle,
                    style: TextStyle(
                      color: DS.textPrimary,
                      fontWeight: DS.fontWeightBold,
                      fontSize: DS.fontSizeLg,
                    ),
                  ),
                ),
                Expanded(
                  child: SingleChildScrollView(
                    child: ChatWorkingMemoryPanel(
                      sessionId: sessionId,
                      onViewSource: (token) {
                        Navigator.of(sheetContext).pop();
                        onViewSource(token);
                      },
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
}

/// Aurora 确认队列按需入口（§5.2 收件箱形态的 chat 侧快捷件）。
///
/// 仅在快照携带待确认/风险/可校准动作时渲染单行 chip；点开按需
/// 承载 [StatusAwarenessBar] 的确认队列（展开层含确认 chip，确认
/// 对象同屏可见——§4.2.3）。常规状态（sensing/calibrated/cooling）零面积。
class ChatAuroraConfirmSignal extends ConsumerWidget {
  const ChatAuroraConfirmSignal({
    required this.conversationId,
    required this.hasActiveRun,
    super.key,
  });

  final String? conversationId;
  final bool hasActiveRun;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final snapshot = ref.watch(auroraStatusProvider);
    if (!auroraSnapshotActionable(snapshot)) {
      return const SizedBox.shrink();
    }
    return SemanticPill(
      label: context.l10n.chatAuroraConfirmChip(
        '${snapshot!.readyCount}/${snapshot.totalCount}',
      ),
      tone: PillTone.info,
      dense: true,
      icon: Icons.auto_awesome_outlined,
      onTap: () => _openConfirmationSheet(context),
    );
  }

  void _openConfirmationSheet(BuildContext context) {
    unawaited(
      showSensoryModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
        builder: (sheetContext) => FractionallySizedBox(
          heightFactor: 0.55,
          child: SafeArea(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(DS.spacing16),
              child: StatusAwarenessBar(
                conversationId: conversationId,
                hasActiveRun: hasActiveRun,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
