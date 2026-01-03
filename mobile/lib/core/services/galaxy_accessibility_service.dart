import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter/services.dart';
import 'package:sparkle/data/models/galaxy_model.dart';
import 'package:sparkle/presentation/widgets/galaxy/sector_config.dart';

/// Galaxy accessibility service for screen readers and haptic feedback
///
/// Features:
/// 1. Semantic labels for nodes and clusters
/// 2. Haptic feedback for interactions
/// 3. VoiceOver/TalkBack support
/// 4. Reduced motion support
/// 5. High contrast mode detection
class GalaxyAccessibilityService {
  GalaxyAccessibilityService();

  bool _isScreenReaderEnabled = false;
  bool _reduceMotionEnabled = false;
  bool _highContrastEnabled = false;

  /// Check if screen reader is enabled
  bool get isScreenReaderEnabled => _isScreenReaderEnabled;

  /// Check if reduce motion is enabled
  bool get reduceMotionEnabled => _reduceMotionEnabled;

  /// Check if high contrast is enabled
  bool get highContrastEnabled => _highContrastEnabled;

  /// Whether haptic feedback is enabled (can be changed at runtime)
  bool hapticEnabled = true;

  /// Initialize accessibility settings from platform
  void initialize(BuildContext context) {
    final mediaQuery = MediaQuery.of(context);
    _isScreenReaderEnabled = mediaQuery.accessibleNavigation;
    _reduceMotionEnabled = mediaQuery.disableAnimations;
    _highContrastEnabled = mediaQuery.highContrast;
  }

  /// Update accessibility settings
  void update({
    bool? screenReaderEnabled,
    bool? reduceMotion,
    bool? highContrast,
    bool? hapticEnabled,
  }) {
    if (screenReaderEnabled != null) _isScreenReaderEnabled = screenReaderEnabled;
    if (reduceMotion != null) _reduceMotionEnabled = reduceMotion;
    if (highContrast != null) _highContrastEnabled = highContrast;
    if (hapticEnabled != null) this.hapticEnabled = hapticEnabled;
  }

  // ============================================
  // Haptic Feedback
  // ============================================

  /// Light haptic for subtle interactions
  Future<void> lightHaptic() async {
    if (!hapticEnabled) return;
    await HapticFeedback.lightImpact();
  }

  /// Medium haptic for standard interactions
  Future<void> mediumHaptic() async {
    if (!hapticEnabled) return;
    await HapticFeedback.mediumImpact();
  }

  /// Heavy haptic for significant actions
  Future<void> heavyHaptic() async {
    if (!hapticEnabled) return;
    await HapticFeedback.heavyImpact();
  }

  /// Selection haptic for UI selection
  Future<void> selectionHaptic() async {
    if (!hapticEnabled) return;
    await HapticFeedback.selectionClick();
  }

  /// Vibration pattern for special events
  Future<void> patternHaptic(HapticPattern pattern) async {
    if (!hapticEnabled) return;

    switch (pattern) {
      case HapticPattern.success:
        await HapticFeedback.lightImpact();
        await Future<void>.delayed(const Duration(milliseconds: 100));
        await HapticFeedback.lightImpact();

      case HapticPattern.error:
        await HapticFeedback.heavyImpact();
        await Future<void>.delayed(const Duration(milliseconds: 100));
        await HapticFeedback.heavyImpact();
        await Future<void>.delayed(const Duration(milliseconds: 100));
        await HapticFeedback.heavyImpact();

      case HapticPattern.warning:
        await HapticFeedback.mediumImpact();
        await Future<void>.delayed(const Duration(milliseconds: 150));
        await HapticFeedback.mediumImpact();

      case HapticPattern.unlock:
        await HapticFeedback.lightImpact();
        await Future<void>.delayed(const Duration(milliseconds: 50));
        await HapticFeedback.mediumImpact();
        await Future<void>.delayed(const Duration(milliseconds: 50));
        await HapticFeedback.heavyImpact();

      case HapticPattern.sparkle:
        for (var i = 0; i < 3; i++) {
          await HapticFeedback.selectionClick();
          await Future<void>.delayed(const Duration(milliseconds: 80));
        }
    }
  }

  // ============================================
  // Semantic Labels
  // ============================================

  /// Generate semantic label for a node
  String getNodeSemanticLabel(GalaxyNodeModel node) {
    final sectorStyle = SectorConfig.getStyle(node.sector);
    final buffer = StringBuffer()
      ..write('${sectorStyle.name}领域的知识节点: ${node.name}. ');

    if (node.isUnlocked) {
      buffer
        ..write('已解锁. ')
        ..write('掌握度: ${node.masteryScore.toStringAsFixed(0)}%. ')
        ..write('学习次数: ${node.studyCount}次. ');
    } else {
      buffer.write('未解锁. ');
    }

    buffer.write('重要程度: ${_importanceLabel(node.importance)}. ');

    return buffer.toString();
  }

  String _importanceLabel(int importance) => switch (importance) {
        1 => '入门级',
        2 => '基础级',
        3 => '进阶级',
        4 => '高级',
        5 => '核心级',
        _ => '普通',
      };

  /// Generate semantic label for a cluster
  String getClusterSemanticLabel(String name, int nodeCount, double avgMastery) =>
      '知识集群: $name. 包含$nodeCount个知识点. 平均掌握度: ${avgMastery.toStringAsFixed(0)}%.';

  /// Generate semantic label for a sector
  String getSectorSemanticLabel(SectorEnum sector, int nodeCount) {
    final style = SectorConfig.getStyle(sector);
    return '${style.name}领域. 包含$nodeCount个知识点. 双击查看详情.';
  }

  /// Generate hint for navigation
  String getNavigationHint() => '使用双指捏合缩放, 单指拖动平移, 双击节点查看详情.';

  // ============================================
  // Accessibility Actions
  // ============================================

  /// Build semantic node for a galaxy node
  CustomSemanticsAction buildNodeAction(GalaxyNodeModel node) =>
      CustomSemanticsAction(label: node.isUnlocked ? '开始学习' : '解锁节点');

  /// Announce message for screen readers
  Future<void> announce(String message) async {
    // Use the non-deprecated API for announcements
    // ignore: deprecated_member_use
    await SemanticsService.announce(message, TextDirection.ltr);
  }

  /// Announce node selection
  Future<void> announceNodeSelection(GalaxyNodeModel node) async {
    final label = getNodeSemanticLabel(node);
    await announce(label);

    // Haptic feedback for selection
    await selectionHaptic();
  }

  /// Announce zoom level change
  Future<void> announceZoomLevel(double scale) async {
    final percentage = (scale * 100).toStringAsFixed(0);
    await announce('缩放级别: $percentage%');
  }

  /// Announce navigation to new area
  Future<void> announceNavigation(String areaName) async {
    await announce('导航至: $areaName');
  }

  // ============================================
  // Animation Settings
  // ============================================

  /// Get animation duration based on accessibility settings
  Duration getAnimationDuration(Duration normalDuration) {
    if (_reduceMotionEnabled) {
      // Reduce animation duration significantly
      return Duration(milliseconds: (normalDuration.inMilliseconds * 0.1).round());
    }
    return normalDuration;
  }

  /// Check if animations should be disabled
  bool get shouldDisableAnimations => _reduceMotionEnabled;

  /// Get appropriate curve for animations
  Curve getAnimationCurve() => _reduceMotionEnabled ? Curves.linear : Curves.easeOutCubic;

  // ============================================
  // Color Adjustments
  // ============================================

  /// Adjust color for high contrast mode
  Color adjustColorForContrast(Color color, {bool isBackground = false}) {
    if (!_highContrastEnabled) return color;

    // Increase saturation and adjust brightness for high contrast
    final hsl = HSLColor.fromColor(color);

    if (isBackground) {
      // Make backgrounds darker
      return hsl.withLightness((hsl.lightness * 0.3).clamp(0.0, 1.0)).toColor();
    } else {
      // Make foregrounds brighter and more saturated
      return hsl
          .withLightness((hsl.lightness * 1.3).clamp(0.0, 1.0))
          .withSaturation((hsl.saturation * 1.2).clamp(0.0, 1.0))
          .toColor();
    }
  }

  /// Get contrasting text color
  Color getContrastingTextColor(Color background) {
    final luminance = background.computeLuminance();
    return luminance > 0.5 ? Colors.black : Colors.white;
  }
}

/// Haptic feedback patterns
enum HapticPattern {
  success,
  error,
  warning,
  unlock,
  sparkle,
}

/// Accessibility wrapper widget for galaxy nodes
class GalaxyNodeSemantics extends StatelessWidget {
  const GalaxyNodeSemantics({
    required this.node,
    required this.child,
    required this.accessibilityService,
    this.onTap,
    this.onDoubleTap,
    this.onLongPress,
    super.key,
  });

  final GalaxyNodeModel node;
  final Widget child;
  final GalaxyAccessibilityService accessibilityService;
  final VoidCallback? onTap;
  final VoidCallback? onDoubleTap;
  final VoidCallback? onLongPress;

  @override
  Widget build(BuildContext context) => Semantics(
      label: accessibilityService.getNodeSemanticLabel(node),
      hint: node.isUnlocked ? '双击开始学习' : '双击解锁',
      button: true,
      onTap: onTap,
      onLongPress: onLongPress,
      child: child,
    );
}

/// Focus management for galaxy navigation
class GalaxyFocusManager {
  GalaxyFocusManager();

  final Map<String, FocusNode> _focusNodes = {};
  String? _currentFocusedNodeId;

  /// Get or create focus node for a galaxy node
  FocusNode getFocusNode(String nodeId) {
    _focusNodes.putIfAbsent(nodeId, FocusNode.new);
    return _focusNodes[nodeId]!;
  }

  /// Focus a specific node
  void focusNode(String nodeId) {
    final focusNode = _focusNodes[nodeId];
    if (focusNode != null) {
      focusNode.requestFocus();
      _currentFocusedNodeId = nodeId;
    }
  }

  /// Get currently focused node ID
  String? get currentFocusedNodeId => _currentFocusedNodeId;

  /// Move focus to next node in list
  void focusNext(List<String> orderedNodeIds) {
    if (_currentFocusedNodeId == null) {
      if (orderedNodeIds.isNotEmpty) {
        focusNode(orderedNodeIds.first);
      }
      return;
    }

    final currentIndex = orderedNodeIds.indexOf(_currentFocusedNodeId!);
    if (currentIndex < orderedNodeIds.length - 1) {
      focusNode(orderedNodeIds[currentIndex + 1]);
    }
  }

  /// Move focus to previous node in list
  void focusPrevious(List<String> orderedNodeIds) {
    if (_currentFocusedNodeId == null) {
      if (orderedNodeIds.isNotEmpty) {
        focusNode(orderedNodeIds.last);
      }
      return;
    }

    final currentIndex = orderedNodeIds.indexOf(_currentFocusedNodeId!);
    if (currentIndex > 0) {
      focusNode(orderedNodeIds[currentIndex - 1]);
    }
  }

  /// Clear focus
  void clearFocus() {
    _currentFocusedNodeId = null;
    for (final node in _focusNodes.values) {
      node.unfocus();
    }
  }

  /// Dispose all focus nodes
  void dispose() {
    for (final node in _focusNodes.values) {
      node.dispose();
    }
    _focusNodes.clear();
  }
}

/// Keyboard navigation support for galaxy
class GalaxyKeyboardNavigation {
  GalaxyKeyboardNavigation({
    required this.focusManager,
    required this.onNodeSelected,
    required this.onZoom,
    required this.onPan,
  });

  final GalaxyFocusManager focusManager;
  final void Function(String nodeId) onNodeSelected;
  final void Function(double deltaScale) onZoom;
  final void Function(Offset delta) onPan;

  /// Handle keyboard event
  KeyEventResult handleKeyEvent(KeyEvent event, List<String> orderedNodeIds) {
    if (event is! KeyDownEvent) return KeyEventResult.ignored;

    switch (event.logicalKey) {
      case LogicalKeyboardKey.arrowRight:
      case LogicalKeyboardKey.arrowDown:
        focusManager.focusNext(orderedNodeIds);
        return KeyEventResult.handled;

      case LogicalKeyboardKey.arrowLeft:
      case LogicalKeyboardKey.arrowUp:
        focusManager.focusPrevious(orderedNodeIds);
        return KeyEventResult.handled;

      case LogicalKeyboardKey.enter:
      case LogicalKeyboardKey.space:
        final focusedId = focusManager.currentFocusedNodeId;
        if (focusedId != null) {
          onNodeSelected(focusedId);
        }
        return KeyEventResult.handled;

      case LogicalKeyboardKey.equal:
      case LogicalKeyboardKey.add:
        onZoom(0.1);
        return KeyEventResult.handled;

      case LogicalKeyboardKey.minus:
        onZoom(-0.1);
        return KeyEventResult.handled;

      case LogicalKeyboardKey.keyW:
        onPan(const Offset(0, -50));
        return KeyEventResult.handled;

      case LogicalKeyboardKey.keyS:
        onPan(const Offset(0, 50));
        return KeyEventResult.handled;

      case LogicalKeyboardKey.keyA:
        onPan(const Offset(-50, 0));
        return KeyEventResult.handled;

      case LogicalKeyboardKey.keyD:
        onPan(const Offset(50, 0));
        return KeyEventResult.handled;

      case LogicalKeyboardKey.escape:
        focusManager.clearFocus();
        return KeyEventResult.handled;

      default:
        return KeyEventResult.ignored;
    }
  }
}
