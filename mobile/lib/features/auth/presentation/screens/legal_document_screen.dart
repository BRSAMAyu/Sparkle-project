import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';

class LegalDocumentScreen extends StatelessWidget {
  const LegalDocumentScreen({
    required this.documentType,
    super.key,
  });

  final String documentType;

  bool get _isTerms => documentType == 'terms';

  @override
  Widget build(BuildContext context) {
    final title = _isTerms ? context.l10n.authTermsOfService : context.l10n.authPrivacyPolicy;
    final sections = _isTerms ? _termsSections() : _privacySections();

    return SparklePageScaffold(
      role: SparklePageRole.settings,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () {
            if (context.canPop()) {
              context.pop();
            } else {
              context.go('/login');
            }
          },
        ),
        title: Text(title),
        centerTitle: true,
      ),
      child: ContentConstraint(
        child: ListView.separated(
          padding: const EdgeInsets.all(DS.spacing24),
          itemCount: sections.length + 1,
          separatorBuilder: (_, __) => const SizedBox(height: DS.spacing16),
          itemBuilder: (context, index) {
            if (index == 0) {
              return SparkleStaggerItem(
                index: 0,
                child: GraphiteCardSurface(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    const SizedBox(height: DS.spacing8),
                    Text(
                      I18nService.instance.isChinese ? '当前版本：v1' : 'Current version: v1',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: DS.textSecondary,
                          ),
                    ),
                    const SizedBox(height: DS.spacing8),
                    Text(
                      I18nService.instance.isChinese
                          ? '最后更新：2026年5月1日。本隐私政策说明了 Sparkle 如何收集、使用和保护你的个人信息。请仔细阅读。'
                          : 'Last updated: May 1, 2026. This privacy policy explains how Sparkle collects, uses, and protects your personal information. Please read carefully.',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
                ),
              );
            }

            final section = sections[index - 1];
            return SparkleStaggerItem(
              index: index,
              child: GraphiteCardSurface(
                surfaceRole: SparkleSurfaceRole.card,
                child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    section.title,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: DS.fontWeightBold,
                        ),
                  ),
                  const SizedBox(height: DS.spacing8),
                  Text(
                    section.body,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          height: 1.65,
                        ),
                  ),
                ],
              ),
              ),
            );
          },
        ),
      ),
    );
  }
}

class _LegalSection {
  const _LegalSection(this.title, this.body);

  final String title;
  final String body;
}

List<_LegalSection> _termsSections() {
  final zh = I18nService.instance.isChinese;
  return [
    _LegalSection(
      zh ? '1. 服务说明' : '1. Service Description',
      zh ? 'Sparkle 为你提供学习陪伴、知识管理与账号安全相关服务。你在使用服务时，应保证提供的信息真实、合法且不侵犯他人权益。' : 'Sparkle provides learning companionship, knowledge management, and account security services. You must ensure information provided is truthful, lawful, and does not infringe on others\' rights.',
    ),
    _LegalSection(
      zh ? '2. 账号责任' : '2. Account Responsibility',
      zh ? '你需要妥善保管登录凭证，不得将账号出借、出租或转让给他人使用。如发现异常登录，请尽快修改密码或联系我们。' : 'You must keep your login credentials secure and must not lend, rent, or transfer your account. If you notice unusual login activity, change your password or contact us promptly.',
    ),
    _LegalSection(
      zh ? '3. 内容与行为规范' : '3. Content & Conduct',
      zh ? '你上传、发布或同步的内容应遵守适用法律法规。对于违法违规、侵权或危害平台安全的行为，我们有权采取限制措施。' : 'Content you upload, publish, or sync must comply with applicable laws. We reserve the right to restrict violations, infringement, or behavior that threatens platform security.',
    ),
    _LegalSection(
      zh ? '4. 账号注销与数据处理' : '4. Account Deletion & Data',
      zh ? '你可以在设置中申请注销账号。注销后我们会立即使当前会话失效，并按照平台规则进入保留期后完成后续清理。' : 'You can request account deletion in Settings. After deletion, your session is immediately invalidated and data is cleaned up after the retention period per platform policy.',
    ),
  ];
}

List<_LegalSection> _privacySections() {
  final zh = I18nService.instance.isChinese;
  return [
    _LegalSection(
      zh ? '1. 我们收集的信息' : '1. Information We Collect',
      zh ? '为完成注册登录、安全校验和多设备管理，我们会处理邮箱、设备标识、登录日志及你主动提供的资料。' : 'To enable registration, security verification, and multi-device management, we process your email, device identifiers, login logs, and information you voluntarily provide.',
    ),
    _LegalSection(
      zh ? '2. 使用目的' : '2. Purpose of Use',
      zh ? '这些信息主要用于身份验证、账号保护、异常排查、功能交付及服务质量优化，不会超出说明范围任意使用。' : 'This information is used for identity verification, account protection, troubleshooting, feature delivery, and service quality optimization — never beyond the stated scope.',
    ),
    _LegalSection(
      zh ? '3. 数据安全' : '3. Data Security',
      zh ? '我们会结合令牌吊销、会话管理和安全日志等机制保护账号安全，并尽量减少不必要的数据保留。' : 'We use token revocation, session management, and security logs to protect your account, minimizing unnecessary data retention.',
    ),
    _LegalSection(
      zh ? '4. 你的权利' : '4. Your Rights',
      zh ? '你可以申请修改资料、重置密码、验证邮箱、管理登录设备或注销账号。后续正式版本可接入线上协议页与客服入口。' : 'You can request to modify your profile, reset your password, verify your email, manage login devices, or delete your account. Future versions will link to online policy pages and support.',
    ),
  ];
}
