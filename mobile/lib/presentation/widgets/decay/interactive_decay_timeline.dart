import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'dart:math' as math;

/// 必杀技 B: 交互式知识衰减时间线
///
/// 功能：
/// - 滑块拖动查看未来 0-90 天的知识衰减状态
/// - 实时显示 Galaxy 节点颜色/透明度变化
/// - "What If" 按钮模拟复习干预效果
/// - 触觉反馈增强交互体验
class InteractiveDecayTimeline extends StatefulWidget {
  /// 衰减预测数据更新回调
  final Function(int daysAhead) onDaysChanged;

  /// 干预模拟回调
  final Function(List<String> nodeIds, int daysAhead) onSimulateIntervention;

  /// 当前选中的节点IDs（用于干预）
  final List<String> selectedNodeIds;

  /// 初始天数
  final int initialDays;

  const InteractiveDecayTimeline({
    Key? key,
    required this.onDaysChanged,
    required this.onSimulateIntervention,
    this.selectedNodeIds = const [],
    this.initialDays = 30,
  }) : super(key: key);

  @override
  State<InteractiveDecayTimeline> createState() =>
      _InteractiveDecayTimelineState();
}

class _InteractiveDecayTimelineState extends State<InteractiveDecayTimeline>
    with SingleTickerProviderStateMixin {
  late double _currentDays;
  late AnimationController _interventionController;
  bool _isSimulating = false;

  @override
  void initState() {
    super.initState();
    _currentDays = widget.initialDays.toDouble();

    _interventionController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 300),
    );
  }

  @override
  void dispose() {
    _interventionController.dispose();
    super.dispose();
  }

  void _onSliderChanged(double value) {
    setState(() {
      _currentDays = value;
    });

    // 触觉反馈（每10天）
    if (value % 10 == 0) {
      HapticFeedback.selectionClick();
    }

    // 通知父组件更新预测数据
    widget.onDaysChanged(value.round());
  }

  void _onSimulateReview() {
    if (widget.selectedNodeIds.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('请先在 Galaxy 中选择要复习的节点'),
          duration: Duration(seconds: 2),
        ),
      );
      return;
    }

    setState(() {
      _isSimulating = true;
    });

    // 动画效果
    _interventionController.forward().then((_) {
      _interventionController.reverse();
    });

    // 触觉反馈
    HapticFeedback.mediumImpact();

    // 调用干预模拟
    widget.onSimulateIntervention(
      widget.selectedNodeIds,
      _currentDays.round(),
    );

    // 1秒后重置状态
    Future.delayed(const Duration(seconds: 1), () {
      if (mounted) {
        setState(() {
          _isSimulating = false;
        });
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            theme.colorScheme.surface,
            theme.colorScheme.surface.withOpacity(0.8),
          ],
        ),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.1),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          // 标题
          Row(
            children: [
              Icon(
                Icons.access_time,
                color: theme.colorScheme.primary,
                size: 24,
              ),
              const SizedBox(width: 8),
              Text(
                '知识时光机',
                style: theme.textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
              const Spacer(),
              _buildTimeChip(context),
            ],
          ),

          const SizedBox(height: 20),

          // 时间轴滑块
          _buildTimelineSlider(theme),

          const SizedBox(height: 16),

          // 状态指示器
          _buildStatusIndicators(theme),

          const SizedBox(height: 20),

          // 干预按钮
          _buildInterventionButton(theme),
        ],
      ),
    );
  }

  Widget _buildTimeChip(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.primaryContainer,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        '未来 ${_currentDays.round()} 天',
        style: TextStyle(
          color: Theme.of(context).colorScheme.onPrimaryContainer,
          fontWeight: FontWeight.w600,
          fontSize: 14,
        ),
      ),
    );
  }

  Widget _buildTimelineSlider(ThemeData theme) {
    return Column(
      children: [
        // 自定义滑块
        SliderTheme(
          data: SliderThemeData(
            activeTrackColor: _getTrackColor(_currentDays),
            inactiveTrackColor: theme.colorScheme.surfaceVariant,
            thumbColor: _getTrackColor(_currentDays),
            overlayColor: _getTrackColor(_currentDays).withOpacity(0.2),
            thumbShape: const RoundSliderThumbShape(
              enabledThumbRadius: 12,
            ),
            overlayShape: const RoundSliderOverlayShape(
              overlayRadius: 24,
            ),
            trackHeight: 6,
          ),
          child: Slider(
            value: _currentDays,
            min: 0,
            max: 90,
            divisions: 18, // 每5天一个刻度
            label: '${_currentDays.round()} 天后',
            onChanged: _onSliderChanged,
          ),
        ),

        // 刻度标签
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 8),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _buildTickLabel('今天', theme),
              _buildTickLabel('30天', theme),
              _buildTickLabel('60天', theme),
              _buildTickLabel('90天', theme),
            ],
          ),
        ),
      ],
    );
  }

  Color _getTrackColor(double days) {
    if (days <= 15) {
      return Colors.green;
    } else if (days <= 45) {
      return Colors.orange;
    } else {
      return Colors.red;
    }
  }

  Widget _buildTickLabel(String label, ThemeData theme) {
    return Text(
      label,
      style: theme.textTheme.bodySmall?.copyWith(
        color: theme.colorScheme.onSurfaceVariant,
      ),
    );
  }

  Widget _buildStatusIndicators(ThemeData theme) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceAround,
      children: [
        _buildStatusItem(
          icon: Icons.wb_sunny,
          label: '健康',
          color: Colors.green,
          description: '>60%',
          theme: theme,
        ),
        _buildStatusItem(
          icon: Icons.wb_cloudy,
          label: '衰减中',
          color: Colors.orange,
          description: '20-60%',
          theme: theme,
        ),
        _buildStatusItem(
          icon: Icons.warning_amber,
          label: '危险',
          color: Colors.red,
          description: '<20%',
          theme: theme,
        ),
      ],
    );
  }

  Widget _buildStatusItem({
    required IconData icon,
    required String label,
    required Color color,
    required String description,
    required ThemeData theme,
  }) {
    return Column(
      children: [
        Icon(icon, color: color, size: 28),
        const SizedBox(height: 4),
        Text(
          label,
          style: theme.textTheme.bodySmall?.copyWith(
            fontWeight: FontWeight.w600,
          ),
        ),
        Text(
          description,
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
            fontSize: 10,
          ),
        ),
      ],
    );
  }

  Widget _buildInterventionButton(ThemeData theme) {
    return SizedBox(
      width: double.infinity,
      child: AnimatedBuilder(
        animation: _interventionController,
        builder: (context, child) {
          final scale = 1.0 + _interventionController.value * 0.1;

          return Transform.scale(
            scale: scale,
            child: ElevatedButton.icon(
              onPressed: _isSimulating ? null : _onSimulateReview,
              icon: _isSimulating
                  ? SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: theme.colorScheme.onPrimary,
                      ),
                    )
                  : const Icon(Icons.auto_fix_high),
              label: Text(
                _isSimulating
                    ? '模拟中...'
                    : '如果现在复习？ (${widget.selectedNodeIds.length} 个节点)',
                style: const TextStyle(
                  fontWeight: FontWeight.w600,
                ),
              ),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
                backgroundColor: theme.colorScheme.primary,
                foregroundColor: theme.colorScheme.onPrimary,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
                elevation: _isSimulating ? 0 : 2,
              ),
            ),
          );
        },
      ),
    );
  }
}

/// 时间线可视化 Painter（可选，用于更复杂的可视化）
class DecayTimelinePainter extends CustomPainter {
  final double currentDays;
  final Map<int, double> decayCurve; // day -> average_mastery

  DecayTimelinePainter({
    required this.currentDays,
    required this.decayCurve,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (decayCurve.isEmpty) return;

    final paint = Paint()
      ..color = Colors.blue.withOpacity(0.5)
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke;

    final path = Path();
    final maxDay = decayCurve.keys.reduce(math.max);

    // 绘制衰减曲线
    bool firstPoint = true;
    decayCurve.forEach((day, mastery) {
      final x = (day / maxDay) * size.width;
      final y = size.height - (mastery / 100.0) * size.height;

      if (firstPoint) {
        path.moveTo(x, y);
        firstPoint = false;
      } else {
        path.lineTo(x, y);
      }
    });

    canvas.drawPath(path, paint);

    // 绘制当前时间点标记
    final currentX = (currentDays / maxDay) * size.width;
    final circlePaint = Paint()
      ..color = Colors.red
      ..style = PaintingStyle.fill;

    canvas.drawCircle(
      Offset(currentX, size.height / 2),
      6,
      circlePaint,
    );
  }

  @override
  bool shouldRepaint(DecayTimelinePainter oldDelegate) {
    return oldDelegate.currentDays != currentDays ||
        oldDelegate.decayCurve != decayCurve;
  }
}
