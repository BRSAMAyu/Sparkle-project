import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/home/domain/services/emotion_visual_blending_service.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/layers/weather_layer.dart';
import 'package:sparkle/features/home/presentation/widgets/weather_presentation.dart';

class WeatherGuideScreen extends ConsumerStatefulWidget {
  const WeatherGuideScreen({super.key});

  @override
  ConsumerState<WeatherGuideScreen> createState() => _WeatherGuideScreenState();
}

class _WeatherGuideScreenState extends ConsumerState<WeatherGuideScreen>
    with TickerProviderStateMixin {
  late final AnimationController _mainAnimationController;
  late final AnimationController _particleController;

  static const List<_WeatherGuideSpec> _specs = [
    _WeatherGuideSpec(
      type: 'sunny',
      title: '晴空',
      previewLabel: '稳定推进',
      detail: '默认天气。通常代表近期节奏平稳，没有明显风险，适合按计划持续推进。',
      trigger: '当冲刺没有进入高压或落后状态时，系统会保持晴空。',
    ),
    _WeatherGuideSpec(
      type: 'cloudy',
      title: '薄雾',
      previewLabel: '整理与回稳',
      detail: '代表节奏开始变慢，系统会提醒你回到主线、补上最近的推进。',
      trigger: '冲刺 7 天内且进度低于 20%，或连续 2 天没有完成任务时更容易出现。',
    ),
    _WeatherGuideSpec(
      type: 'rainy',
      title: '风雨',
      previewLabel: '收束与聚焦',
      detail: '代表压力上升，需要减少噪声、尽快聚焦关键动作。',
      trigger: '冲刺剩余少于 3 天且进度低于 50%，或近期焦虑指标高于 50% 时更容易出现。',
    ),
    _WeatherGuideSpec(
      type: 'meteor',
      title: '流星',
      previewLabel: '高光冲刺',
      detail: '代表你正处于很强的推进势能里，系统会给到更亮、更轻快的反馈。',
      trigger: '当前冲刺进度高于 80% 时更容易出现。',
    ),
  ];

  @override
  void initState() {
    super.initState();
    _mainAnimationController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2200),
    );
    _particleController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 3200),
    );
    unawaited(_mainAnimationController.repeat(reverse: true));
    unawaited(_particleController.repeat());
  }

  @override
  void dispose() {
    _mainAnimationController.dispose();
    _particleController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final dashboardState = ref.watch(dashboardProvider);
    final currentPresentation = resolveWeatherPresentation(
      context,
      dashboardState.weather.type,
    );

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
          variant: ButtonVariant.ghost,
        ),
        title: const Text('天气图鉴'),
      ),
      child: ContentConstraint(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(
            DS.spacing16,
            DS.spacing12,
            DS.spacing16,
            DS.spacing24,
          ),
          children: [
            _CurrentWeatherPanel(
              presentation: currentPresentation,
              condition: dashboardState.weather.condition,
            ),
            const SizedBox(height: DS.spacing16),
            const _SectionHeader(
              title: '天气预览',
              subtitle: '这里可以预览系统里的全部天气表现。预览不会改动真实天气，只用于帮助你理解视觉效果与设定。',
            ),
            const SizedBox(height: DS.spacing10),
            LayoutBuilder(
              builder: (context, constraints) {
                final compact = constraints.maxWidth < 720;
                final cardWidth = compact
                    ? constraints.maxWidth
                    : (constraints.maxWidth - DS.spacing12) / 2;
                return Wrap(
                  spacing: DS.spacing12,
                  runSpacing: DS.spacing12,
                  children: _specs
                      .map(
                        (spec) => SizedBox(
                          width: cardWidth,
                          child: _WeatherPreviewCard(
                            spec: spec,
                            isCurrent: dashboardState.weather.type == spec.type,
                            mainAnimation: _mainAnimationController,
                            particleAnimation: _particleController,
                          ),
                        ),
                      )
                      .toList(),
                );
              },
            ),
            const SizedBox(height: DS.spacing20),
            const _SectionHeader(
              title: '判定标准',
              subtitle: '真实天气依然由你的近期数据决定，下面是当前系统的主要参考规则。',
            ),
            const SizedBox(height: DS.spacing10),
            const _WeatherRuleTile(
              title: '晴空是默认状态',
              body: '当系统没有检测到明显的高压、拖延或强势冲刺信号时，会保持晴空。',
            ),
            const _WeatherRuleTile(
              title: '薄雾代表节奏变慢',
              body: '冲刺剩余 7 天内且进度低于 20%，或连续 2 天没有完成任务时，天气更容易转为薄雾。',
            ),
            const _WeatherRuleTile(
              title: '风雨代表压力偏高',
              body: '冲刺剩余少于 3 天且进度低于 50% 时，系统会倾向给出风雨状态，提醒你尽快收束焦点。',
            ),
            const _WeatherRuleTile(
              title: '焦虑会覆盖基础判断',
              body: '如果近期焦虑指标高于 50%，系统会优先给出风雨天气，用来提示当前负荷偏高。',
            ),
            const _WeatherRuleTile(
              title: '流星代表高势能',
              body: '当当前冲刺进度高于 80% 时，系统更容易进入流星天气，强调你的推进势头。',
            ),
            const SizedBox(height: DS.spacing20),
            const _SectionHeader(
              title: '说明',
              subtitle:
                  '这个页面用于理解天气系统的视觉效果与判定逻辑。真正显示给你的天气，仍然会跟随你的真实任务、冲刺和状态数据动态更新。',
            ),
          ],
        ),
      ),
    );
  }
}

class _CurrentWeatherPanel extends StatelessWidget {
  const _CurrentWeatherPanel({
    required this.presentation,
    required this.condition,
  });

  final WeatherPresentationData presentation;
  final String condition;

  @override
  Widget build(BuildContext context) => GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    '当前天气',
                    style: context.sparkleTypography.titleLarge.copyWith(
                      fontWeight: DS.fontWeightBold,
                      color: DS.textPrimary,
                    ),
                  ),
                ),
                WeatherStatusBadge(
                  presentation: presentation,
                  condition: condition,
                  density: WeatherStatusDensity.compact,
                ),
              ],
            ),
            const SizedBox(height: DS.spacing12),
            Text(
              presentation.subtitle,
              style: context.sparkleTypography.bodyMedium.copyWith(
                color: DS.textSecondary,
                height: 1.45,
              ),
            ),
            const SizedBox(height: DS.spacing10),
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: DS.spacing12,
                vertical: DS.spacing10,
              ),
              decoration: BoxDecoration(
                color: Color.alphaBlend(
                  presentation.softAccent.withValues(alpha: 0.08),
                  DS.surfacePanel,
                ),
                borderRadius: DS.borderRadius16,
                border: Border.all(
                  color: presentation.borderTint.withValues(alpha: 0.75),
                ),
              ),
              child: Text(
                condition.trim().isEmpty
                    ? '当前天气会根据你的真实数据自动更新。'
                    : '当前判定：$condition',
                style: context.sparkleTypography.labelSmall.copyWith(
                  color: DS.textSecondary,
                  height: 1.4,
                ),
              ),
            ),
          ],
        ),
      );
}

class _WeatherPreviewCard extends StatelessWidget {
  const _WeatherPreviewCard({
    required this.spec,
    required this.isCurrent,
    required this.mainAnimation,
    required this.particleAnimation,
  });

  final _WeatherGuideSpec spec;
  final bool isCurrent;
  final Animation<double> mainAnimation;
  final Animation<double> particleAnimation;

  @override
  Widget build(BuildContext context) {
    final presentation = resolveWeatherPresentation(context, spec.type);

    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      padding: EdgeInsets.zero,
      child: ClipRRect(
        borderRadius: DS.borderRadius20,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              height: 188,
              child: Stack(
                fit: StackFit.expand,
                children: [
                  DecoratedBox(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: presentation.headerGradient,
                      ),
                    ),
                  ),
                  IgnorePointer(
                    child: WeatherLayer(
                      weatherType: spec.type,
                      blendParams: _previewBlendParams(spec.type),
                      mainAnimation: mainAnimation,
                      particleAnimation: particleAnimation,
                    ),
                  ),
                  Positioned(
                    left: DS.spacing12,
                    right: DS.spacing12,
                    bottom: DS.spacing12,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: WeatherStatusBadge(
                                presentation: presentation,
                                condition: spec.previewLabel,
                                density: WeatherStatusDensity.compact,
                              ),
                            ),
                            if (isCurrent) ...[
                              const SizedBox(width: DS.spacing8),
                              Container(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: DS.spacing8,
                                  vertical: DS.spacing4,
                                ),
                                decoration: BoxDecoration(
                                  color: DS.surfaceOverlay.withValues(
                                    alpha: 0.76,
                                  ),
                                  borderRadius: DS.borderRadiusFull,
                                  border: Border.all(color: DS.borderSubtle),
                                ),
                                child: Text(
                                  '当前',
                                  style: context.sparkleTypography.labelSmall
                                      .copyWith(
                                    color: DS.textPrimary,
                                    fontWeight: DS.fontWeightBold,
                                  ),
                                ),
                              ),
                            ],
                          ],
                        ),
                        const SizedBox(height: DS.spacing8),
                        Text(
                          spec.title,
                          style: context.sparkleTypography.titleLarge.copyWith(
                            color: DS.textPrimary,
                            fontWeight: DS.fontWeightBold,
                          ),
                        ),
                        const SizedBox(height: DS.spacing4),
                        Text(
                          presentation.ambientHint,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: context.sparkleTypography.labelSmall.copyWith(
                            color: DS.textSecondary,
                            height: 1.35,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    spec.detail,
                    style: context.sparkleTypography.bodyMedium.copyWith(
                      color: DS.textSecondary,
                      height: 1.45,
                    ),
                  ),
                  const SizedBox(height: DS.spacing10),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: DS.spacing10,
                      vertical: DS.spacing8,
                    ),
                    decoration: BoxDecoration(
                      color: DS.surfacePanel,
                      borderRadius: DS.borderRadius16,
                      border: Border.all(color: DS.borderSubtle),
                    ),
                    child: Text(
                      '真实触发参考：${spec.trigger}',
                      style: context.sparkleTypography.labelSmall.copyWith(
                        color: DS.textSecondary,
                        height: 1.4,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  VisualBlendParams _previewBlendParams(String type) {
    switch (type) {
      case 'cloudy':
        return VisualBlendParams(
          primaryTint: DS.neutral400,
          particleDensity: 0.56,
          animationSpeed: 0.55,
          backgroundOpacity: 0.28,
        );
      case 'rainy':
        return VisualBlendParams(
          primaryTint: DS.info,
          particleDensity: 0.72,
          animationSpeed: 0.78,
          backgroundOpacity: 0.32,
        );
      case 'meteor':
        return VisualBlendParams(
          primaryTint: DS.brandSecondary,
          particleDensity: 0.62,
          animationSpeed: 0.88,
          backgroundOpacity: 0.28,
        );
      case 'sunny':
      default:
        return VisualBlendParams(
          primaryTint: DS.brandPrimary,
          particleDensity: 0.48,
          animationSpeed: 0.62,
          backgroundOpacity: 0.24,
        );
    }
  }
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({
    required this.title,
    required this.subtitle,
  });

  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: context.sparkleTypography.titleLarge.copyWith(
              color: DS.textPrimary,
              fontWeight: DS.fontWeightBold,
            ),
          ),
          const SizedBox(height: DS.spacing6),
          Text(
            subtitle,
            style: context.sparkleTypography.labelSmall.copyWith(
              color: DS.textSecondary,
              height: 1.45,
            ),
          ),
        ],
      );
}

class _WeatherRuleTile extends StatelessWidget {
  const _WeatherRuleTile({
    required this.title,
    required this.body,
  });

  final String title;
  final String body;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: DS.spacing10),
        child: GraphiteCardSurface(
          surfaceRole: SparkleSurfaceRole.card,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: context.sparkleTypography.labelLarge.copyWith(
                  color: DS.textPrimary,
                  fontWeight: DS.fontWeightBold,
                ),
              ),
              const SizedBox(height: DS.spacing6),
              Text(
                body,
                style: context.sparkleTypography.bodyMedium.copyWith(
                  color: DS.textSecondary,
                  height: 1.45,
                ),
              ),
            ],
          ),
        ),
      );
}

class _WeatherGuideSpec {
  const _WeatherGuideSpec({
    required this.type,
    required this.title,
    required this.previewLabel,
    required this.detail,
    required this.trigger,
  });

  final String type;
  final String title;
  final String previewLabel;
  final String detail;
  final String trigger;
}
