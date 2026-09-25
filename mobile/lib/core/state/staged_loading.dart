import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// U-06 分阶等待组件——STATE_MATRIX「loading <500ms / long-running stage」
/// 两行的统一渲染真源。
///
/// 契约（验收「>500ms 有 stage feedback；无 terminal spinner」）：
/// - 前 [stageFeedbackThreshold] 只出骨架（快路径零文案噪音）；
/// - 超过阈值仍未决 → 升格为 stage feedback：阶段文案按 [stageInterval]
///   推进（准备中 → 加载中 → 快好了），并给可解释的「可离开」提示——
///   用户永远知道「现在发生什么」；
/// - 全程**不渲染裸的无界圆形 spinner**（终结态 spinner 的唯一根形）。
///
/// 阶段文案经调用方注入（默认取 arb 词条），本组件不持判定逻辑。
class StagedSurfaceLoader extends StatefulWidget {
  const StagedSurfaceLoader({
    super.key,
    this.stageMessages = const [],
    this.stageFeedbackThreshold = const Duration(milliseconds: 500),
    this.stageInterval = const Duration(milliseconds: 2600),
    this.longWaitHint,
    this.compact = false,
    this.height,
    this.skeletonRows = 3,
    this.onLeave,
  });

  /// 阶段文案序列（已本地化）。空序列时使用 arb 默认三阶段。
  final List<String> stageMessages;

  /// stage feedback 升格阈值（STATE_MATRIX 的 500ms 线）。
  final Duration stageFeedbackThreshold;

  /// 阶段文案推进间隔。
  final Duration stageInterval;

  /// 长等待提示（「可以离开，回来会恢复」一类可解释文案）。
  final String? longWaitHint;

  /// 紧凑形态：用于卡内/区块内接缝（单行进度 + 阶段文案）。
  final bool compact;

  /// 固定高度（紧凑形态常用；null 时自适应）。
  final double? height;

  /// 骨架行数（非紧凑形态）。
  final int skeletonRows;

  /// 长等待的退路（CORE_INTERACTION_PATTERNS #5「Recoverable wait：长任务
  /// 可离开」）——stage 升格后渲染「返回」；null 时不渲染。
  final VoidCallback? onLeave;

  @override
  State<StagedSurfaceLoader> createState() => _StagedSurfaceLoaderState();
}

class _StagedSurfaceLoaderState extends State<StagedSurfaceLoader> {
  Timer? _thresholdTimer;
  Timer? _stageTimer;
  bool _stageVisible = false;
  int _stageIndex = 0;

  @override
  void initState() {
    super.initState();
    _armThresholdTimer();
  }

  @override
  void didUpdateWidget(covariant StagedSurfaceLoader oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.stageMessages != widget.stageMessages) {
      _stageIndex = 0;
    }
  }

  void _armThresholdTimer() {
    _thresholdTimer = Timer(widget.stageFeedbackThreshold, () {
      if (!mounted) return;
      setState(() => _stageVisible = true);
      _armStageTimer();
    });
  }

  void _armStageTimer() {
    _stageTimer = Timer.periodic(widget.stageInterval, (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }
      setState(() {
        final max = _effectiveStageCount;
        if (max > 0) {
          _stageIndex = (_stageIndex + 1) % max;
        }
      });
    });
  }

  int get _effectiveStageCount {
    if (widget.stageMessages.isNotEmpty) return widget.stageMessages.length;
    final l10n = AppLocalizations.of(context);
    return l10n == null ? 0 : 3; // arb 默认三阶段
  }

  String? _stageText(AppLocalizations? l10n) {
    if (!_stageVisible) return null;
    if (widget.stageMessages.isNotEmpty) {
      return widget.stageMessages[_stageIndex % widget.stageMessages.length];
    }
    if (l10n == null) return null;
    return switch (_stageIndex % 3) {
      0 => l10n.stateStagePreparing,
      1 => l10n.stateStageLoading,
      _ => l10n.stateStageAlmost,
    };
  }

  @override
  void dispose() {
    _thresholdTimer?.cancel();
    _stageTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final stageText = _stageText(l10n);
    final showLongWaitHint =
        _stageVisible && (widget.longWaitHint ?? l10n?.stateLongWaitHint) != null;

    if (widget.compact) {
      return SizedBox(
        height: widget.height,
        child: Center(
          child: Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing16,
              vertical: DS.spacing12,
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(DS.radius8),
                  child: LinearProgressIndicator(
                    minHeight: 3,
                    backgroundColor: DS.brandPrimary200,
                    valueColor: AlwaysStoppedAnimation(DS.brandPrimary),
                  ),
                ),
                if (stageText != null) ...[
                  const SizedBox(height: DS.spacing8),
                  Text(
                    stageText,
                    style: TextStyle(
                      fontSize: DS.fontSizeSm,
                      color: DS.textSecondary,
                    ),
                    textAlign: TextAlign.center,
                  ),
                ],
              ],
            ),
          ),
        ),
      );
    }

    final skeleton = Column(
      children: [
        for (var i = 0; i < widget.skeletonRows; i++) ...[
          const SparkleSkeleton(width: double.infinity),
          if (i != widget.skeletonRows - 1) const SizedBox(height: DS.spacing12),
        ],
      ],
    );

    if (!_stageVisible) {
      return skeleton;
    }

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        skeleton,
        const SizedBox(height: DS.spacing16),
        if (stageText != null)
          Text(
            stageText,
            style: TextStyle(
              fontSize: DS.fontSizeSm,
              color: DS.textSecondary,
            ),
            textAlign: TextAlign.center,
          ),
        if (showLongWaitHint) ...[
          const SizedBox(height: DS.spacing4),
          Text(
            widget.longWaitHint ?? l10n!.stateLongWaitHint,
            style: TextStyle(
              fontSize: DS.fontSizeXs,
              color: DS.textTertiary,
            ),
            textAlign: TextAlign.center,
          ),
        ],
        if (widget.onLeave != null && l10n != null) ...[
          const SizedBox(height: DS.spacing4),
          TextButton.icon(
            onPressed: widget.onLeave,
            icon: const Icon(Icons.arrow_back_rounded, size: 16),
            label: Text(l10n.back),
          ),
        ],
      ],
    );
  }
}

/// 纯文案版 stage feedback——已渲染骨架的既有表面（如 dashboard 骨架段）
/// 只需在其上叠加「>500ms 升格」的阶段性提示，不必换掉自家骨架。
class StagedStageHint extends StatefulWidget {
  const StagedStageHint({
    super.key,
    this.threshold = const Duration(milliseconds: 500),
  });

  final Duration threshold;

  @override
  State<StagedStageHint> createState() => _StagedStageHintState();
}

class _StagedStageHintState extends State<StagedStageHint> {
  Timer? _timer;
  bool _visible = false;

  @override
  void initState() {
    super.initState();
    _timer = Timer(widget.threshold, () {
      if (mounted) setState(() => _visible = true);
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!_visible) return const SizedBox.shrink();
    final l10n = AppLocalizations.of(context);
    if (l10n == null) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: DS.spacing8),
      child: Text(
        l10n.stateStageLoading,
        style: TextStyle(
          fontSize: DS.fontSizeSm,
          color: DS.textSecondary,
        ),
        textAlign: TextAlign.center,
      ),
    );
  }
}
