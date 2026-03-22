import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:sparkle/core/experience/experience_profile.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/widgets/scene_audio_scope.dart';
import 'package:sparkle/features/onboarding/presentation/widgets/architecture_animation.dart';

/// 交互式引导流程 - Week 7
///
/// 新用户首次使用时的引导体验
/// 包含：
/// 1. 欢迎页
/// 2. 架构可视化动画
/// 3. 核心功能介绍（Galaxy、Chat、Tasks）
/// 4. 权限请求
/// 5. 个性化设置
class InteractiveOnboardingScreen extends ConsumerStatefulWidget {
  const InteractiveOnboardingScreen({
    required this.onComplete,
    super.key,
  });
  final VoidCallback onComplete;

  @override
  ConsumerState<InteractiveOnboardingScreen> createState() =>
      _InteractiveOnboardingScreenState();
}

class _InteractiveOnboardingScreenState
    extends ConsumerState<InteractiveOnboardingScreen> {
  final PageController _pageController = PageController();
  int _currentPage = 0;
  final int _totalPages = 6;
  bool _notificationsEnabled = false;
  bool _microphoneEnabled = false;
  bool _requestingNotification = false;
  bool _requestingMicrophone = false;

  @override
  void initState() {
    super.initState();
    unawaited(_loadPermissionStatuses());
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  Future<void> _loadPermissionStatuses() async {
    final notificationStatus =
        await ref.read(notificationServiceProvider).checkPermissionStatus();
    final microphoneStatus = await Permission.microphone.status;
    if (!mounted) {
      return;
    }
    setState(() {
      _notificationsEnabled = notificationStatus.hasPermission;
      _microphoneEnabled = microphoneStatus.isGranted;
    });
  }

  Future<void> _requestNotificationPermission() async {
    if (_requestingNotification) {
      return;
    }
    setState(() => _requestingNotification = true);
    final granted = await ref
        .read(notificationPermissionStatusProvider.notifier)
        .requestPermission();
    if (!mounted) {
      return;
    }
    setState(() {
      _notificationsEnabled = granted;
      _requestingNotification = false;
    });
  }

  Future<void> _requestMicrophonePermission() async {
    if (_requestingMicrophone) {
      return;
    }
    setState(() => _requestingMicrophone = true);
    final status = await Permission.microphone.request();
    if (!mounted) {
      return;
    }
    setState(() {
      _microphoneEnabled = status.isGranted;
      _requestingMicrophone = false;
    });
  }

  void _nextPage() {
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm));
    if (_currentPage < _totalPages - 1) {
      unawaited(
        _pageController.nextPage(
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeInOut,
        ),
      );
    } else {
      widget.onComplete();
    }
  }

  void _skipAll() {
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
    widget.onComplete();
  }

  @override
  Widget build(BuildContext context) => SceneAudioScope(
        policy: ExperienceProfiles.dashboardProductive.audioPolicy(
          trackOverride: BgmTrack.dashboard,
        ),
        child: Scaffold(
        backgroundColor: DS.deepSpaceStart,
        body: SafeArea(
          child: Column(
            children: [
              // Skip button
              if (_currentPage < _totalPages - 1)
                Align(
                  alignment: Alignment.topRight,
                  child: SparkleButton.ghost(
                    label: context.l10n.onboardingSkip,
                    onPressed: _skipAll,
                  ),
                ),

              // PageView
              Expanded(
                child: PageView(
                  controller: _pageController,
                  onPageChanged: (index) {
                    setState(() => _currentPage = index);
                    unawaited(
                      SensoryFeedbackService.emit(
                        SensoryFeedbackEvent.navigation,
                      ),
                    );
                  },
                  children: [
                    _buildWelcomePage(),
                    _buildArchitecturePage(),
                    _buildGalaxyFeaturePage(),
                    _buildChatFeaturePage(),
                    _buildTaskFeaturePage(),
                    _buildPersonalizationPage(),
                  ],
                ),
              ),

              // Page indicator
              Padding(
                padding: const EdgeInsets.all(DS.lg),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    // Page dots
                    Row(
                      children: List.generate(
                        _totalPages,
                        (index) => Container(
                          width: index == _currentPage ? 24 : 8,
                          height: 8,
                          margin: const EdgeInsets.symmetric(horizontal: 4),
                          decoration: BoxDecoration(
                            color: index == _currentPage
                                ? DS.brandPrimary
                                : DS.brandPrimary.withValues(alpha: 0.3),
                            borderRadius: BorderRadius.circular(4),
                          ),
                        ),
                      ),
                    ),

                    // Next/Done button
                    SparkleButton.primary(
                      label: _currentPage == _totalPages - 1
                          ? context.l10n.onboardingGetStarted
                          : context.l10n.onboardingNext,
                      onPressed: _nextPage,
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
      );

  // Page 1: Welcome
  Widget _buildWelcomePage() => ContentConstraint(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(DS.xxl),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
            // Logo animation
            TweenAnimationBuilder<double>(
              tween: Tween(begin: 0, end: 1),
              duration: const Duration(seconds: 1),
              curve: Curves.elasticOut,
              builder: (context, value, child) => Transform.scale(
                scale: value,
                child: Container(
                  width: 120,
                  height: 120,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: LinearGradient(
                      colors: [
                        DS.brandPrimary.shade400,
                        DS.prismPurple,
                      ],
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: DS.brandPrimary.withValues(alpha: 0.5),
                        blurRadius: 40,
                        spreadRadius: 10,
                      ),
                    ],
                  ),
                  child: Icon(
                    Icons.auto_awesome,
                    size: 60,
                    color: DS.brandPrimaryConst,
                  ),
                ),
              ),
            ),
            const SizedBox(height: DS.xxxl),

            // Title
            Text(
              context.l10n.onboardingWelcomeTitle,
              style: TextStyle(
                color: DS.brandPrimaryConst,
                fontSize: 32,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: DS.lg),

            // Subtitle
            Text(
              context.l10n.onboardingWelcomeSubtitle,
              textAlign: TextAlign.center,
              style: TextStyle(
                color: DS.brandPrimary.withValues(alpha: 0.8),
                fontSize: 18,
              ),
            ),
            const SizedBox(height: DS.xxxl),

            // Features preview
            SparkleStaggerItem(
              index: 0,
              child: _buildFeaturePreview(
                Icons.auto_graph,
                context.l10n.onboardingFeatureGalaxy,
                context.l10n.onboardingFeatureGalaxyDesc,
              ),
            ),
            const SizedBox(height: DS.lg),
            SparkleStaggerItem(
              index: 1,
              child: _buildFeaturePreview(
                Icons.psychology,
                context.l10n.onboardingFeatureChat,
                context.l10n.onboardingFeatureChatDesc,
              ),
            ),
            const SizedBox(height: DS.lg),
              SparkleStaggerItem(
                index: 2,
                child: _buildFeaturePreview(
                Icons.task_alt,
                context.l10n.onboardingFeatureTasks,
                context.l10n.onboardingFeatureTasksDesc,
              ),
              ),
            ],
          ),
        ),
      );

  Widget _buildFeaturePreview(
    IconData icon,
    String title,
    String description,
  ) =>
      Container(
        padding: const EdgeInsets.all(DS.lg),
        decoration: BoxDecoration(
          color: DS.brandPrimary.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: DS.brandPrimary.withValues(alpha: 0.2)),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(DS.md),
              decoration: BoxDecoration(
                color: DS.brandPrimary.withValues(alpha: 0.3),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(icon, color: DS.brandPrimaryConst, size: 24),
            ),
            const SizedBox(width: DS.lg),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: TextStyle(
                      color: DS.brandPrimaryConst,
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  Text(
                    description,
                    style: TextStyle(
                      color: DS.brandPrimary.withValues(alpha: 0.7),
                      fontSize: 14,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      );

  // Page 2: Architecture Animation
  Widget _buildArchitecturePage() => ContentConstraint(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(DS.xxl),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
            Text(
              context.l10n.onboardingArchitectureTitle,
              style: TextStyle(
                color: DS.brandPrimaryConst,
                fontSize: 28,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: DS.lg),
            Text(
              context.l10n.onboardingArchitectureSubtitle,
              style: TextStyle(
                color: DS.brandPrimary.withValues(alpha: 0.8),
                fontSize: 16,
              ),
            ),
            const SizedBox(height: DS.xxl),

            // Architecture Animation
              const ArchitectureAnimation(),
            ],
          ),
        ),
      );

  // Page 3: Galaxy Feature
  Widget _buildGalaxyFeaturePage() => _buildFeaturePage(
        icon: Icons.auto_graph,
        iconGradient: [DS.brandPrimary.shade400, DS.info],
        title: context.l10n.onboardingGalaxyTitle,
        description: context.l10n.onboardingGalaxyDescription,
        features: [
          context.l10n.onboardingGalaxyFeature1,
          context.l10n.onboardingGalaxyFeature2,
          context.l10n.onboardingGalaxyFeature3,
          context.l10n.onboardingGalaxyFeature4,
        ],
        demoWidget: _buildGalaxyDemo(),
      );

  // Page 4: Chat Feature
  Widget _buildChatFeaturePage() => _buildFeaturePage(
        icon: Icons.psychology,
        iconGradient: [DS.prismPurple, DS.error],
        title: context.l10n.onboardingChatTitle,
        description: context.l10n.onboardingChatDescription,
        features: [
          context.l10n.onboardingChatFeature1,
          context.l10n.onboardingChatFeature2,
          context.l10n.onboardingChatFeature3,
          context.l10n.onboardingChatFeature4,
        ],
        demoWidget: _buildChatDemo(),
      );

  // Page 5: Task Feature
  Widget _buildTaskFeaturePage() => _buildFeaturePage(
        icon: Icons.task_alt,
        iconGradient: [DS.success.shade400, Colors.teal.shade400],
        title: context.l10n.onboardingTasksTitle,
        description: context.l10n.onboardingTasksDescription,
        features: [
          context.l10n.onboardingTasksFeature1,
          context.l10n.onboardingTasksFeature2,
          context.l10n.onboardingTasksFeature3,
          context.l10n.onboardingTasksFeature4,
        ],
        demoWidget: _buildTaskDemo(),
      );

  // Page 6: Personalization
  Widget _buildPersonalizationPage() => ContentConstraint(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(DS.xxl),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
            Icon(
              Icons.settings_suggest,
              size: 80,
              color: DS.brandPrimaryConst,
            ),
            const SizedBox(height: DS.xxl),
            Text(
              context.l10n.onboardingPersonalizationTitle,
              style: TextStyle(
                color: DS.brandPrimaryConst,
                fontSize: 28,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: DS.lg),
            Text(
              context.l10n.onboardingPersonalizationSubtitle,
              style: TextStyle(
                color: DS.brandPrimary.withValues(alpha: 0.8),
                fontSize: 16,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: DS.xxxl),
            _buildPermissionOption(
              icon: Icons.notifications_active,
              title: context.l10n.onboardingSettingReminders,
              description: context.l10n.onboardingSettingRemindersDesc,
              enabled: _notificationsEnabled,
              isLoading: _requestingNotification,
              onTap:
                  _notificationsEnabled ? null : _requestNotificationPermission,
            ),
            const SizedBox(height: DS.lg),
            _buildPermissionOption(
              icon: Icons.mic_none_rounded,
              title: _isChinese ? '语音输入' : 'Voice Input',
              description: _isChinese
                  ? '启用麦克风后，你可以直接说出目标和问题。'
                  : 'Enable the microphone so you can speak goals and questions naturally.',
              enabled: _microphoneEnabled,
              isLoading: _requestingMicrophone,
              onTap: _microphoneEnabled ? null : _requestMicrophonePermission,
            ),
            const SizedBox(height: DS.lg),
              _buildSettingOption(
                icon: Icons.auto_awesome,
                title: context.l10n.onboardingSettingAssistant,
                description: context.l10n.onboardingSettingAssistantDesc,
                value: true,
              ),
            ],
          ),
        ),
      );

  Widget _buildFeaturePage({
    required IconData icon,
    required List<Color> iconGradient,
    required String title,
    required String description,
    required List<String> features,
    required Widget demoWidget,
  }) =>
      ContentConstraint(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(DS.xxl),
          child: Column(
            children: [
              // Icon
              SparkleStaggerItem(
                index: 0,
                child: Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  gradient: LinearGradient(colors: iconGradient),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Icon(icon, size: 48, color: DS.brandPrimary),
                ),
              ),
              const SizedBox(height: DS.xl),

              // Title
              SparkleStaggerItem(
                index: 1,
                child: Text(
                title,
                style: TextStyle(
                  color: DS.brandPrimaryConst,
                  fontSize: 28,
                  fontWeight: FontWeight.bold,
                ),
                ),
              ),
              const SizedBox(height: DS.md),

              // Description
              SparkleStaggerItem(
                index: 2,
                child: Text(
                description,
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: DS.brandPrimary.withValues(alpha: 0.8),
                  fontSize: 16,
                ),
                ),
              ),
              const SizedBox(height: DS.xxl),

              // Demo widget
              SparkleStaggerItem(index: 3, child: demoWidget),
              const SizedBox(height: DS.xxl),

              // Features list
              ...features.map(
                (feature) => SparkleStaggerItem(
                  index: features.indexOf(feature) + 4,
                  child: Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Icon(
                        Icons.check_circle,
                        color: iconGradient[0],
                        size: 24,
                      ),
                      const SizedBox(width: DS.md),
                      Expanded(
                        child: Text(
                          feature,
                          style: TextStyle(
                            color: DS.brandPrimaryConst,
                            fontSize: 14,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                ),
              ),
            ],
          ),
        ),
      );

  bool get _isChinese => Localizations.localeOf(context).languageCode == 'zh';

  String get _permissionEnableLabel => _isChinese ? '开启' : 'Enable';

  String get _permissionEnabledLabel => _isChinese ? '已开启' : 'Enabled';

  String get _permissionReadyLabel => _isChinese
      ? '已准备好，之后也可以在设置里调整'
      : 'Ready to go, and you can change this later in Settings';

  String get _permissionPendingLabel =>
      _isChinese ? '稍后也可以在设置里开启' : 'You can turn this on later in Settings';

  Widget _buildPermissionOption({
    required IconData icon,
    required String title,
    required String description,
    required bool enabled,
    required bool isLoading,
    required Future<void> Function()? onTap,
  }) =>
      SparkleStaggerItem(
        index: title.hashCode & 1,
        child: Container(
        padding: const EdgeInsets.all(DS.lg),
        decoration: BoxDecoration(
          color: DS.brandPrimary.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: DS.brandPrimary.withValues(alpha: 0.2)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, color: DS.brandPrimary.shade400, size: 32),
                const SizedBox(width: DS.lg),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style: TextStyle(
                          color: DS.brandPrimaryConst,
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      Text(
                        description,
                        style: TextStyle(
                          color: DS.brandPrimary.withValues(alpha: 0.7),
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ),
                AnimatedContainer(
                  duration: const Duration(milliseconds: 180),
                  padding: const EdgeInsets.symmetric(
                    horizontal: DS.md,
                    vertical: DS.xs,
                  ),
                  decoration: BoxDecoration(
                    color: enabled
                        ? DS.success.withValues(alpha: 0.18)
                        : DS.brandPrimary.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Text(
                    enabled ? _permissionEnabledLabel : _permissionEnableLabel,
                    style: TextStyle(
                      color: enabled ? DS.success : DS.brandPrimaryConst,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: DS.md),
            Row(
              children: [
                Expanded(
                  child: Text(
                    enabled ? _permissionReadyLabel : _permissionPendingLabel,
                    style: TextStyle(
                      color: DS.brandPrimary.withValues(alpha: 0.7),
                      fontSize: 12,
                    ),
                  ),
                ),
                if (onTap case final action?)
                  SparkleButton.ghost(
                    label: isLoading
                        ? (_isChinese ? '处理中...' : 'Working...')
                        : _permissionEnableLabel,
                    onPressed: isLoading
                        ? () {}
                        : () {
                            unawaited(
                              SensoryFeedbackService.emit(
                                SensoryFeedbackEvent.confirm,
                              ),
                            );
                            unawaited(action());
                          },
                  ),
              ],
            ),
          ],
        ),
        ),
      );

  Widget _buildSettingOption({
    required IconData icon,
    required String title,
    required String description,
    required bool value,
  }) =>
      Container(
        padding: const EdgeInsets.all(DS.lg),
        decoration: BoxDecoration(
          color: DS.brandPrimary.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: DS.brandPrimary.withValues(alpha: 0.2)),
        ),
        child: Row(
          children: [
            Icon(icon, color: DS.brandPrimary.shade400, size: 32),
            const SizedBox(width: DS.lg),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: TextStyle(
                      color: DS.brandPrimaryConst,
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  Text(
                    description,
                    style: TextStyle(
                      color: DS.brandPrimary.withValues(alpha: 0.7),
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ),
            Switch(
              value: value,
              onChanged: (v) {
                unawaited(
                  SensoryFeedbackService.emit(SensoryFeedbackEvent.selection),
                );
              },
              activeThumbColor: DS.brandPrimary.shade400,
            ),
          ],
        ),
      );

  // Demo widgets
  Widget _buildGalaxyDemo() => Container(
        height: 200,
        decoration: BoxDecoration(
          gradient: RadialGradient(
            colors: [
              DS.brandPrimary.withValues(alpha: 0.3),
              DS.surfacePrimary.withValues(alpha: 0),
            ],
          ),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Center(
          child: Icon(
            Icons.auto_graph,
            size: 80,
            color: DS.brandPrimary.shade400,
          ),
        ),
      );

  Widget _buildChatDemo() => Container(
        constraints: const BoxConstraints(minHeight: 200),
        padding: const EdgeInsets.all(DS.lg),
        decoration: BoxDecoration(
          color: DS.brandPrimary.withValues(alpha: 0.05),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildChatMessage(context.l10n.onboardingChatDemo1, true),
            const SizedBox(height: DS.sm),
            _buildChatMessage(context.l10n.onboardingChatDemo2, false),
            const SizedBox(height: DS.sm),
            _buildChatMessage(context.l10n.onboardingChatDemo3, true),
          ],
        ),
      );

  Widget _buildChatMessage(String text, bool isAI) => Align(
        alignment: isAI ? Alignment.centerLeft : Alignment.centerRight,
        child: Container(
          padding: const EdgeInsets.all(DS.md),
          decoration: BoxDecoration(
            color: isAI
                ? DS.prismPurple.withValues(alpha: 0.2)
                : DS.brandPrimary.withValues(alpha: 0.2),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Text(
            text,
            style: TextStyle(color: DS.brandPrimaryConst, fontSize: 12),
          ),
        ),
      );

  Widget _buildTaskDemo() => Container(
        constraints: const BoxConstraints(minHeight: 200),
        padding: const EdgeInsets.all(DS.lg),
        decoration: BoxDecoration(
          color: DS.brandPrimary.withValues(alpha: 0.05),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            _buildTaskItem(
              context.l10n.onboardingTaskTypeLearning,
              context.l10n.onboardingTaskDemo1,
              DS.brandPrimary,
            ),
            const SizedBox(height: DS.sm),
            _buildTaskItem(
              context.l10n.onboardingTaskTypePractice,
              context.l10n.onboardingTaskDemo2,
              DS.success,
            ),
            const SizedBox(height: DS.sm),
            _buildTaskItem(
              context.l10n.onboardingTaskTypeReflection,
              context.l10n.onboardingTaskDemo3,
              DS.prismPurple,
            ),
          ],
        ),
      );

  Widget _buildTaskItem(String type, String title, Color color) => Container(
        padding: const EdgeInsets.all(DS.md),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.2),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Row(
          children: [
            Icon(Icons.circle, size: 12, color: color),
            const SizedBox(width: DS.sm),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    type,
                    style: TextStyle(
                      color: color,
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  Text(
                    title,
                    style: TextStyle(color: DS.brandPrimaryConst, fontSize: 12),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
}
