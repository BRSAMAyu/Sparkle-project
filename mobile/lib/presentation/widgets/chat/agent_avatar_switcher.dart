import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/data/models/reasoning_step_model.dart';

/// 从protobuf的int值映射到前端AgentType枚举
/// 与 proto/agent_service.proto 中的 AgentType 枚举保持一致
AgentType agentTypeFromProto(int protoValue) {
  switch (protoValue) {
    case 1:
      return AgentType.orchestrator;
    case 2:
      return AgentType.knowledge;
    case 3:
      return AgentType.math;
    case 4:
      return AgentType.code;
    case 5:
      return AgentType.dataAnalysis;
    case 6:
      return AgentType.translation;
    case 7:
      return AgentType.image;
    case 8:
      return AgentType.audio;
    case 9:
      return AgentType.writing;
    case 10:
      return AgentType.reasoning;
    default:
      return AgentType.orchestrator; // 默认为orchestrator
  }
}

/// Agent视觉配置
class AgentConfig {
  final IconData icon;
  final Color color;
  final String displayName;
  final String animation; // 动画隐喻描述

  const AgentConfig({
    required this.icon,
    required this.color,
    required this.displayName,
    required this.animation,
  });

  /// 获取指定AgentType的配置
  static AgentConfig forType(AgentType type) {
    switch (type) {
      case AgentType.orchestrator:
        return const AgentConfig(
          icon: Icons.psychology, // 大脑图标
          color: Color(0xFF9C27B0), // 紫色 (Sparkle Purple)
          displayName: 'Orchestrator',
          animation: '呼吸脉冲', // 思考中
        );

      case AgentType.knowledge:
        return const AgentConfig(
          icon: Icons.auto_awesome, // 星光图标
          color: DS.info, // 蓝色 (Science Blue)
          displayName: 'KnowledgeAgent',
          animation: '旋转扫描', // 检索中
        );

      case AgentType.math:
        return const AgentConfig(
          icon: Icons.calculate, // 计算器图标
          color: Color(0xFFFFC107), // 琥珀色 (Amber)
          displayName: 'MathAgent',
          animation: '数字跳动', // 计算中
        );

      case AgentType.code:
        return const AgentConfig(
          icon: Icons.terminal, // 终端图标
          color: DS.success, // 绿色 (Matrix Green)
          displayName: 'CodeAgent',
          animation: '光标闪烁', // 编码中
        );

      case AgentType.writing:
        return const AgentConfig(
          icon: Icons.edit, // 笔图标
          color: Color(0xFFF59E0B), // 琥珀色
          displayName: 'WritingAgent',
          animation: '文字流动',
        );

      case AgentType.science:
        return const AgentConfig(
          icon: Icons.science, // 科学图标
          color: Color(0xFF10B981), // 绿色
          displayName: 'ScienceAgent',
          animation: '实验分析',
        );

      case AgentType.search:
        return const AgentConfig(
          icon: Icons.search, // 搜索图标
          color: Color(0xFF3B82F6), // 蓝色
          displayName: 'SearchAgent',
          animation: '扫描搜索',
        );

      case AgentType.dataAnalysis:
        return const AgentConfig(
          icon: Icons.analytics, // 数据分析图标
          color: Color(0xFF8B5CF6), // 紫罗兰色
          displayName: 'DataAnalyst',
          animation: '数据流动',
        );

      case AgentType.translation:
        return const AgentConfig(
          icon: Icons.translate, // 翻译图标
          color: Color(0xFF06B6D4), // 青色
          displayName: 'Translator',
          animation: '语言转换',
        );

      case AgentType.image:
        return const AgentConfig(
          icon: Icons.image, // 图像图标
          color: Color(0xFFEC4899), // 粉色
          displayName: 'ImageAgent',
          animation: '像素渲染',
        );

      case AgentType.audio:
        return const AgentConfig(
          icon: Icons.audiotrack, // 音频图标
          color: Color(0xFFF59E0B), // 橙色
          displayName: 'AudioAgent',
          animation: '音波震动',
        );

      case AgentType.reasoning:
        return const AgentConfig(
          icon: Icons.lightbulb, // 灯泡图标
          color: Color(0xFFEAB308), // 黄色
          displayName: 'ReasoningAgent',
          animation: '逻辑推演',
        );
    }
  }
}

/// Agent头像切换器 - 支持平滑的角色切换动画
///
/// 使用AnimatedSwitcher实现图标的无缝溶解切换，
/// 包含旋转、缩放和淡入淡出的组合动画
class AgentAvatarSwitcher extends StatelessWidget {
  final AgentType agentType;
  final double size;
  final bool showPulseAnimation;

  const AgentAvatarSwitcher({
    required this.agentType,
    super.key,
    this.size = 32,
    this.showPulseAnimation = false,
  });

  @override
  Widget build(BuildContext context) {
    final config = AgentConfig.forType(agentType);

    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 500),
      transitionBuilder: (child, animation) {
        // 组合动画：旋转 + 缩放 + 淡入
        final rotationTween = Tween<double>(
          begin: 0.8,
          end: 1.0,
        );

        return RotationTransition(
          turns: rotationTween.animate(animation),
          child: ScaleTransition(
            scale: animation,
            child: FadeTransition(
              opacity: animation,
              child: child,
            ),
          ),
        );
      },
      child: _buildAgentIcon(config),
    );
  }

  Widget _buildAgentIcon(AgentConfig config) {
    // 必须给唯一Key，否则AnimatedSwitcher认为没有变化
    return Container(
      key: ValueKey(agentType),
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: config.color.withValues(alpha: 0.2), // 背景色
        border: Border.all(
          color: config.color,
          width: 2,
        ),
        // 添加微妙的阴影效果
        boxShadow: [
          BoxShadow(
            color: config.color.withValues(alpha: 0.3),
            blurRadius: 8,
            spreadRadius: 0,
          ),
        ],
      ),
      child: showPulseAnimation
          ? _PulsingIcon(
              icon: config.icon,
              color: config.color,
            )
          : Icon(
              config.icon,
              color: config.color,
              size: size * 0.5,
            ),
    );
  }
}

/// 脉冲动画图标 - 用于Orchestrator思考时的呼吸效果
class _PulsingIcon extends StatefulWidget {
  final IconData icon;
  final Color color;

  const _PulsingIcon({
    required this.icon,
    required this.color,
  });

  @override
  State<_PulsingIcon> createState() => _PulsingIconState();
}

class _PulsingIconState extends State<_PulsingIcon>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _scaleAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat(reverse: true);

    _scaleAnimation = Tween<double>(
      begin: 0.9,
      end: 1.1,
    ).animate(
      CurvedAnimation(
        parent: _controller,
        curve: Curves.easeInOut,
      ),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ScaleTransition(
      scale: _scaleAnimation,
      child: Icon(
        widget.icon,
        color: widget.color,
        size: 16,
      ),
    );
  }
}

/// Agent状态指示器 - 带动画的完整状态显示
///
/// 包含Agent头像、名称和当前状态描述
class AgentStatusIndicator extends StatelessWidget {
  final AgentType agentType;
  final String statusText;
  final bool isThinking;

  const AgentStatusIndicator({
    required this.agentType,
    required this.statusText,
    super.key,
    this.isThinking = false,
  });

  @override
  Widget build(BuildContext context) {
    final config = AgentConfig.forType(agentType);
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: config.color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: config.color.withValues(alpha: 0.3),
          width: 1,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          AgentAvatarSwitcher(
            agentType: agentType,
            size: 24,
            showPulseAnimation: isThinking && agentType == AgentType.orchestrator,
          ),
          const SizedBox(width: DS.sm),
          Flexible(
            child: Text(
              statusText,
              style: theme.textTheme.bodySmall?.copyWith(
                color: config.color,
                fontWeight: FontWeight.w600,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          if (isThinking) ...[
            const SizedBox(width: DS.sm),
            SizedBox(
              width: 12,
              height: 12,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                valueColor: AlwaysStoppedAnimation<Color>(config.color),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
