import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/experience/experience_profile.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/widgets/scene_audio_scope.dart';
import 'package:sparkle/features/home/presentation/widgets/understanding_panel.dart';
import 'package:sparkle/features/onboarding/presentation/widgets/architecture_animation.dart';

const _kOnboardingPageKey = 'onboarding_current_page';

/// 交互式引导流程 - Week 7
///
/// 新用户首次使用时的引导体验
/// 包含：
/// 1. 欢迎页
/// 2. 架构可视化动画
/// 3. 核心功能介绍（Galaxy）
/// 4. AI 怎么帮你（Chat + Tasks 合并单页，A-SPEC2 top10 #6）
/// 5. 权限请求与个性化设置
class InteractiveOnboardingScreen extends ConsumerStatefulWidget {
  const InteractiveOnboardingScreen({
    required this.onComplete,
    super.key,
  });
  final VoidCallback onComplete;

  /// A-SPEC2 top10 #6：引导收敛 ≤5 步（SPEC §8.9 必达②）。
  /// 原 6 页中的 chat/task 两特性页合并为「AI 怎么帮你」单页。
  static const int totalPages = 5;

  @override
  ConsumerState<InteractiveOnboardingScreen> createState() =>
      _InteractiveOnboardingScreenState();
}

class _InteractiveOnboardingScreenState
    extends ConsumerState<InteractiveOnboardingScreen> {
  final PageController _pageController = PageController();
  int _currentPage = 0;
  final int _totalPages = InteractiveOnboardingScreen.totalPages;
  bool _notificationsEnabled = false;
  bool _microphoneEnabled = false;
  bool _requestingNotification = false;
  bool _requestingMicrophone = false;

  @override
  void initState() {
    super.initState();
    unawaited(_loadPermissionStatuses());
    unawaited(_restorePage());
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  Future<void> _restorePage() async {
    final prefs = await SharedPreferences.getInstance();
    final saved = prefs.getInt(_kOnboardingPageKey);
    if (saved != null && saved > 0 && saved < _totalPages && mounted) {
      _currentPage = saved;
      _pageController.jumpToPage(saved);
    }
  }

  Future<void> _persistPage() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(_kOnboardingPageKey, _currentPage);
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
      unawaited(_clearSavedPage());
      widget.onComplete();
    }
  }

  void _skipAll() {
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
    unawaited(_clearSavedPage());
    widget.onComplete();
  }

  Future<void> _clearSavedPage() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_kOnboardingPageKey);
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
                      unawaited(_persistPage());
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
                      _buildAiHelpPage(),
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
                  fontWeight: DS.fontWeightBold,
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
                      fontWeight: DS.fontWeightBold,
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
                  fontWeight: DS.fontWeightBold,
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

  // Page 4: AI 怎么帮你（Chat + Tasks 合并单页，一屏两特性各一句）
  Widget _buildAiHelpPage() => ContentConstraint(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(DS.xxl),
          child: Column(
            children: [
              // 复用 _buildFeaturePage 的图标容器（gradientLiteral 收敛：
              // 渐变字面量单源于 _buildFeatureIcon，A5.3 ratchet 只降不升）。
              _buildFeatureIcon(
                icon: Icons.psychology,
                iconGradient: [DS.prismPurple, DS.success.shade400],
              ),
              const SizedBox(height: DS.xl),
              SparkleStaggerItem(
                index: 1,
                child: Text(
                  context.l10n.onboardingAiHelpTitle,
                  style: TextStyle(
                    color: DS.brandPrimaryConst,
                    fontSize: 28,
                    fontWeight: DS.fontWeightBold,
                  ),
                ),
              ),
              const SizedBox(height: DS.xxl),
              SparkleStaggerItem(
                index: 2,
                child: _buildFeaturePreview(
                  Icons.psychology,
                  context.l10n.onboardingFeatureChat,
                  context.l10n.onboardingFeatureChatDesc,
                ),
              ),
              const SizedBox(height: DS.lg),
              SparkleStaggerItem(
                index: 3,
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

  // Page 5: Personalization
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
                  fontWeight: DS.fontWeightBold,
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
                onTap: _notificationsEnabled
                    ? null
                    : _requestNotificationPermission,
              ),
              const SizedBox(height: DS.lg),
              _buildPermissionOption(
                icon: Icons.mic_none_rounded,
                title: context.l10n.onboardingVoiceInput,
                description: context.l10n.onboardingVoiceInputDesc,
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
              const SizedBox(height: DS.lg),
              const UnderstandingPanel(
                compact: true,
                initiallyExpanded: true,
                surface: 'onboarding',
              ),
            ],
          ),
        ),
      );

  // 特性页头部图标容器（gradient 字面量唯一 owner，A5.3）。
  Widget _buildFeatureIcon({
    required IconData icon,
    required List<Color> iconGradient,
  }) =>
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
              _buildFeatureIcon(icon: icon, iconGradient: iconGradient),
              const SizedBox(height: DS.xl),

              // Title
              SparkleStaggerItem(
                index: 1,
                child: Text(
                  title,
                  style: TextStyle(
                    color: DS.brandPrimaryConst,
                    fontSize: 28,
                    fontWeight: DS.fontWeightBold,
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

  String get _permissionEnableLabel => context.l10n.onboardingPermissionEnable;

  String get _permissionEnabledLabel =>
      context.l10n.onboardingPermissionEnabled;

  String get _permissionReadyLabel => context.l10n.onboardingPermissionReady;

  String get _permissionPendingLabel =>
      context.l10n.onboardingPermissionPending;

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
                            fontWeight: DS.fontWeightBold,
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
                      enabled
                          ? _permissionEnabledLabel
                          : _permissionEnableLabel,
                      style: TextStyle(
                        color: enabled ? DS.success : DS.brandPrimaryConst,
                        fontSize: 12,
                        fontWeight: DS.fontWeightSemibold,
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
                          ? context.l10n.onboardingPermissionWorking
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
                      fontWeight: DS.fontWeightBold,
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
}
