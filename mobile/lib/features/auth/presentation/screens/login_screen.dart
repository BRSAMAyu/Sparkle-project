import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/display/lexicon/error_lexicon.dart';
import 'package:sparkle/core/errors/user_facing_error.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/services/social_auth_service.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  // Brand colors — single source: the SparkleColors palette (batch2
  // convergence, read via the unified context.colors entry from batch3).
  SparkleColors get _brandColors => context.colors;
  Color get _brandPrimary => _brandColors.brandPrimary;
  Color get _brandPrimaryDeep => _brandColors.brandPrimaryDeep;
  Color get _brandSecondary => _brandColors.brandSecondary;
  Color get _brandSecondaryDeep => _brandColors.brandSecondaryDeep;

  final _formKey = GlobalKey<FormState>();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isPasswordVisible = false;

  /// N25（A-SPEC5 v1.5）校验三段制：未提交前不提前报错（disabled），
  /// 首次提交失败后转即时校验（onUserInteraction），提交时全量兜底。
  AutovalidateMode _autovalidateMode = AutovalidateMode.disabled;

  /// W-4 防重入窗口：同帧/短连击内的重复提交只放行第一次。
  ///
  /// Web 上 flt-text-editing-host 内含真实 <form>+隐藏 submit input，
  /// 原生 form submit 与 Flutter 侧提交构成双通道，一次 Enter 可同时
  /// 触发 login 与 guest 两个 POST（web-round1 W-4 实测 19:44:10/11）。
  ///
  /// W-4（web-round2 误伤定性）：防重入必须**分域**。旧实现把按钮点击与
  /// 键盘提交放在同一个 800ms 窗口里，按钮通道消费的票据会把 800ms 内的
  /// 键盘 Enter 一并吞掉（实测 Enter ×8 零请求）。现拆成两个互不影响的
  /// 通道窗口：
  /// - 按钮域 800ms：防双击与 login/guest 双 POST（round-1 语义保持）；
  /// - 键盘域 100ms：只吸收同帧内的原生 form submit + performAction
  ///   双触发，保证紧随按钮点击的键盘提交永远能发出请求。
  static const _buttonSubmitDedupWindow = Duration(milliseconds: 800);
  static const _keySubmitDedupWindow = Duration(milliseconds: 100);
  DateTime? _lastButtonSubmitAt;
  DateTime? _lastKeySubmitAt;

  bool _consumeButtonSubmitTicket() {
    final now = DateTime.now();
    final last = _lastButtonSubmitAt;
    if (last != null && now.difference(last) < _buttonSubmitDedupWindow) {
      return false;
    }
    _lastButtonSubmitAt = now;
    return true;
  }

  bool _consumeKeySubmitTicket() {
    final now = DateTime.now();
    final last = _lastKeySubmitAt;
    if (last != null && now.difference(last) < _keySubmitDedupWindow) {
      return false;
    }
    _lastKeySubmitAt = now;
    return true;
  }

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  void _submit({bool fromKeyboard = false}) {
    final allowed =
        fromKeyboard ? _consumeKeySubmitTicket() : _consumeButtonSubmitTicket();
    if (!allowed) return;
    if (_formKey.currentState!.validate()) {
      unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm));
      unawaited(
        ref.read(authProvider.notifier).login(
              _usernameController.text.trim(),
              _passwordController.text.trim(),
            ),
      );
    } else if (_autovalidateMode != AutovalidateMode.onUserInteraction) {
      // N25 三段制：首次提交失败后，输入/失焦即校验，改错即时消错。
      setState(() => _autovalidateMode = AutovalidateMode.onUserInteraction);
    }
  }

  void _submitAsGuest() {
    if (!_consumeButtonSubmitTicket()) return;
    unawaited(ref.read(authProvider.notifier).loginAsGuest());
  }

  /// O5：「体验一个示例」入口——与访客链路同源（loginAsGuest，后端预置
  /// 种子数据 + GJ02 upgrade-guest 真转正路径），仅补用户可见的分叉声明。
  void _submitTryExample() {
    if (!_consumeButtonSubmitTicket()) return;
    unawaited(ref.read(authProvider.notifier).loginAsGuest());
  }

  Future<void> _handleSocialLogin(
    Future<SocialAuthResult?> Function() loginMethod,
  ) async {
    try {
      final result = await loginMethod();
      if (result != null) {
        if (!mounted) return;
        unawaited(
          ref.read(authProvider.notifier).socialLogin(
                provider: result.provider,
                token: result.token,
                openid: result.openid,
                email: result.email,
                nickname: result.nickname,
                avatarUrl: result.avatarUrl,
              ),
        );
      }
    } catch (e) {
      if (!mounted) return;
      AppFeedback.error(context, UserFacingError.from(e));
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    final l10n = AppLocalizations.of(context);

    if (l10n == null) {
      return const Scaffold(
        body: Center(child: LoadingIndicator()),
      );
    }

    // Listen for errors and show a SnackBar
    ref.listen<AuthState>(authProvider, (previous, next) {
      if (next.error != null && (previous?.error != next.error)) {
        final failure = next.failure;
        // N15/N16（A-SPEC3）：error 字段已类型化——优先读 failure 自带的
        // 服务端人话；无 failure 时经 error_lexicon owner 按类别出 arb 词条，
        // 不再经 ErrorMessages 对原始异常串做文本嗅探。
        AppFeedback.error(
          context,
          failure?.userMessage ?? uiErrorMessage(l10n, next.error!),
        );
      }
      // Successful login is handled by router redirect
    });

    return SparklePageScaffold(
      role: SparklePageRole.auth,
      safeArea: false,
      child: SafeArea(
        child: ContentConstraint(
          child: SingleChildScrollView(
            keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
            padding: const EdgeInsets.all(DS.xl),
            // Form-factor constraint (batch3 W-7): keep the login form a
            // centered column on desktop/web instead of a 1200px stretch.
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(
                  maxWidth: DS.contentMaxWidthForm,
                ),
                child: Form(
                  key: _formKey,
                  autovalidateMode: _autovalidateMode,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      const SizedBox(height: DS.spacing24),
                      _BrandMark(
                        primary: _brandPrimary,
                        primaryDeep: _brandPrimaryDeep,
                      ),
                      const SizedBox(height: DS.lg),
                      _BrandWordmark(
                        title: l10n.appTitle,
                        secondary: _brandSecondary,
                        secondaryDeep: _brandSecondaryDeep,
                      ),
                      const SizedBox(height: DS.sm),
                      Text(
                        l10n.welcomeSubtitle,
                        textAlign: TextAlign.center,
                        style: Theme.of(context).textTheme.bodyLarge,
                      ),
                      const SizedBox(height: DS.xxxl),
                      TextFormField(
                        controller: _usernameController,
                        autofillHints: const [AutofillHints.username],
                        // W-4：显式声明 IME 语义，避免 web 端原生 form submit
                        // 以默认「done」通道触发隐式提交。
                        textInputAction: TextInputAction.next,
                        onFieldSubmitted: (_) =>
                            FocusScope.of(context).nextFocus(),
                        decoration: InputDecoration(
                          labelText: l10n.username,
                          border: const OutlineInputBorder(),
                          prefixIcon: const Icon(Icons.person_outline),
                        ),
                        validator: (value) =>
                            value!.isEmpty ? l10n.pleaseEnterUsername : null,
                      ),
                      const SizedBox(height: DS.lg),
                      TextFormField(
                        controller: _passwordController,
                        autofillHints: const [AutofillHints.password],
                        obscureText: !_isPasswordVisible,
                        obscuringCharacter: '●',
                        style: const TextStyle(letterSpacing: 0),
                        // W-4：done + 显式 onFieldSubmitted，Enter 只走这一条
                        // Flutter 通道（再由键盘域防重入窗口吸收同帧重复触发）。
                        textInputAction: TextInputAction.done,
                        onFieldSubmitted: (_) => _submit(fromKeyboard: true),
                        decoration: InputDecoration(
                          labelText: l10n.password,
                          border: const OutlineInputBorder(),
                          prefixIcon: const Icon(Icons.lock_outline),
                          // W-5（round1 web 走查）：图标按钮无可见文字，tooltip
                          // 同时提供可访问名称与桌面端悬停提示。
                          suffixIcon: IconButton(
                            tooltip: _isPasswordVisible
                                ? l10n.authHidePassword
                                : l10n.authShowPassword,
                            icon: Icon(
                              _isPasswordVisible
                                  ? Icons.visibility
                                  : Icons.visibility_off,
                            ),
                            onPressed: () {
                              unawaited(
                                SensoryFeedbackService.emit(
                                  SensoryFeedbackEvent.selection,
                                ),
                              );
                              setState(
                                () => _isPasswordVisible = !_isPasswordVisible,
                              );
                            },
                          ),
                        ),
                        validator: (value) =>
                            value!.isEmpty ? l10n.pleaseEnterPassword : null,
                      ),
                      const SizedBox(height: DS.sm),
                      Align(
                        alignment: Alignment.centerRight,
                        child: TextButton(
                          onPressed: authState.isLoading
                              ? null
                              : () => context.push('/forgot-password'),
                          child: Text(l10n.authForgotPassword),
                        ),
                      ),
                      const SizedBox(height: DS.xl),
                      SparkleButton(
                        label: l10n.login,
                        onPressed: authState.isLoading ? null : _submit,
                        expand: true,
                        loading: authState.isLoading,
                        disabled: authState.isLoading,
                      ),
                      const SizedBox(height: DS.sm),
                      SparkleButton(
                        label: l10n.continueAsGuest,
                        onPressed: authState.isLoading ? null : _submitAsGuest,
                        loading: authState.isLoading,
                        disabled: authState.isLoading,
                        variant: ButtonVariant.ghost,
                        expand: true,
                      ),
                      // O5（J-01 机会图）：FIRST_3_MINUTES Screen 1 分叉点——
                      // 「体验一个示例」次级入口（可见但不喧宾夺主），走既有
                      // guest/example 链路（GJ02 已验证的 upgrade-guest 同源
                      // 路径），不造新链路。
                      const SizedBox(height: DS.xs),
                      TextButton(
                        onPressed:
                            authState.isLoading ? null : _submitTryExample,
                        child: Text(l10n.authTryExample),
                      ),
                      const SizedBox(height: DS.xxxl),
                      Row(
                        children: [
                          const Expanded(child: Divider()),
                          Padding(
                            padding: const EdgeInsets.symmetric(
                              horizontal: DS.spacing16,
                            ),
                            child: Text(
                              l10n.orText,
                              style: TextStyle(color: DS.brandPrimary),
                            ),
                          ),
                          const Expanded(child: Divider()),
                        ],
                      ),
                      const SizedBox(height: DS.xl),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                        children: [
                          _SocialLoginButton(
                            icon: Icons.g_mobiledata_rounded,
                            label: l10n.google,
                            onTap: () => _handleSocialLogin(
                              SocialAuthService().signInWithGoogle,
                            ),
                          ),
                          _SocialLoginButton(
                            icon: Icons.apple_rounded,
                            label: l10n.apple,
                            onTap: () => _handleSocialLogin(
                              SocialAuthService().signInWithApple,
                            ),
                          ),
                          _SocialLoginButton(
                            icon: Icons.wechat_rounded,
                            label: l10n.wechat,
                            onTap: () => _handleSocialLogin(
                              SocialAuthService().signInWithWeChat,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: DS.lg),
                      Center(
                        child: SparkleButton.ghost(
                          label: l10n.noAccount,
                          onPressed: () => context.push('/register'),
                        ),
                      ),
                      const SizedBox(height: DS.sm),
                      Wrap(
                        alignment: WrapAlignment.center,
                        crossAxisAlignment: WrapCrossAlignment.center,
                        spacing: DS.spacing4,
                        children: [
                          Text(
                            l10n.authLoginAgreement,
                            style: context.typo.bodySmall,
                          ),
                          TextButton(
                            onPressed: () => context.push('/legal/terms'),
                            child: Text(l10n.authUserAgreement),
                          ),
                          Text(
                            l10n.authAnd,
                            style: context.typo.bodySmall,
                          ),
                          TextButton(
                            onPressed: () => context.push('/legal/privacy'),
                            child: Text(l10n.authPrivacyPolicy),
                          ),
                        ],
                      ),
                      const SizedBox(height: DS.spacing12),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _BrandMark extends StatelessWidget {
  const _BrandMark({
    required this.primary,
    required this.primaryDeep,
  });

  final Color primary;
  final Color primaryDeep;

  @override
  Widget build(BuildContext context) => SizedBox(
        height: 96,
        child: Stack(
          alignment: Alignment.center,
          children: [
            Container(
              width: 92,
              height: 92,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    primary.withValues(alpha: 0.22),
                    primary.withValues(alpha: 0.08),
                    Colors.transparent,
                  ],
                  stops: const [0.0, 0.58, 1.0],
                ),
              ),
            ),
            Container(
              width: 74,
              height: 74,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [primary, primaryDeep],
                ),
                boxShadow: [
                  BoxShadow(
                    color: primary.withValues(alpha: 0.28),
                    blurRadius: 20,
                    offset: const Offset(0, 10),
                  ),
                ],
              ),
            ),
            const Icon(
              Icons.whatshot_rounded,
              size: 34,
              color: Colors.white,
            ),
          ],
        ),
      );
}

class _BrandWordmark extends StatelessWidget {
  const _BrandWordmark({
    required this.title,
    required this.secondary,
    required this.secondaryDeep,
  });

  final String title;
  final Color secondary;
  final Color secondaryDeep;

  @override
  Widget build(BuildContext context) {
    // SparkleTypography role (batch3 W-7): Material headlineSmall is not
    // mapped by _buildTextTheme, so the wordmark previously fell back to
    // the M3 default scale instead of the design system's.
    final baseStyle = context.typo.headingMedium.copyWith(
      fontWeight: FontWeight.w700,
      letterSpacing: 0.2,
      height: 1.05,
      color: secondaryDeep,
    );

    return ShaderMask(
      shaderCallback: (bounds) => LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [secondary, secondaryDeep],
      ).createShader(bounds),
      blendMode: BlendMode.srcIn,
      child: Text(
        title,
        textAlign: TextAlign.center,
        style: baseStyle.copyWith(
          shadows: [
            Shadow(
              color: secondary.withValues(alpha: 0.16),
              blurRadius: 12,
              offset: const Offset(0, 4),
            ),
          ],
        ),
      ),
    );
  }
}

class _SocialLoginButton extends StatelessWidget {
  const _SocialLoginButton({
    required this.icon,
    required this.label,
    required this.onTap,
  });
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    // W-5（round1 web 走查）：纯图标按钮原本在语义树中是无名节点——
    // 读屏与语义自动化都无法辨识。显式补 button 语义 + 名称 + 点击动作，
    // 并 excludeSemantics 避免内部无语义图标产生匿名子节点。
    return Semantics(
      button: true,
      label: label,
      onTap: onTap,
      excludeSemantics: true,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.all(DS.md),
          decoration: BoxDecoration(
            color: colorScheme.surface,
            border: Border.all(
              color: colorScheme.outline.withValues(alpha: 0.2),
            ),
            borderRadius: BorderRadius.circular(12),
            boxShadow: [
              BoxShadow(
                color: DS.brandPrimary.withValues(alpha: 0.05),
                blurRadius: 4,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: Icon(
            icon,
            size: 32,
            color: colorScheme.onSurface,
          ),
        ),
      ),
    );
  }
}
