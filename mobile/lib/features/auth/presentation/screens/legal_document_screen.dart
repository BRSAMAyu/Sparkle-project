import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';

class LegalDocumentScreen extends StatelessWidget {
  const LegalDocumentScreen({
    required this.documentType,
    super.key,
  });

  final String documentType;

  bool get _isTerms => documentType == 'terms';

  @override
  Widget build(BuildContext context) {
    final title = _isTerms ? '用户协议' : '隐私政策';
    final sections = _isTerms ? _termsSections : _privacySections;

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
                      '当前版本：v1',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: DS.textSecondary,
                          ),
                    ),
                    const SizedBox(height: DS.spacing8),
                    Text(
                      '这是当前移动端内置的合规说明占位稿，后续可以平滑替换为线上正式版本。',
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
                          fontWeight: FontWeight.w700,
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

const List<_LegalSection> _termsSections = [
  _LegalSection(
    '1. 服务说明',
    'Sparkle 为你提供学习陪伴、知识管理与账号安全相关服务。你在使用服务时，应保证提供的信息真实、合法且不侵犯他人权益。',
  ),
  _LegalSection(
    '2. 账号责任',
    '你需要妥善保管登录凭证，不得将账号出借、出租或转让给他人使用。如发现异常登录，请尽快修改密码或联系我们。',
  ),
  _LegalSection(
    '3. 内容与行为规范',
    '你上传、发布或同步的内容应遵守适用法律法规。对于违法违规、侵权或危害平台安全的行为，我们有权采取限制措施。',
  ),
  _LegalSection(
    '4. 账号注销与数据处理',
    '你可以在设置中申请注销账号。注销后我们会立即使当前会话失效，并按照平台规则进入保留期后完成后续清理。',
  ),
];

const List<_LegalSection> _privacySections = [
  _LegalSection(
    '1. 我们收集的信息',
    '为完成注册登录、安全校验和多设备管理，我们会处理邮箱、设备标识、登录日志及你主动提供的资料。',
  ),
  _LegalSection(
    '2. 使用目的',
    '这些信息主要用于身份验证、账号保护、异常排查、功能交付及服务质量优化，不会超出说明范围任意使用。',
  ),
  _LegalSection(
    '3. 数据安全',
    '我们会结合令牌吊销、会话管理和安全日志等机制保护账号安全，并尽量减少不必要的数据保留。',
  ),
  _LegalSection(
    '4. 你的权利',
    '你可以申请修改资料、重置密码、验证邮箱、管理登录设备或注销账号。后续正式版本可接入线上协议页与客服入口。',
  ),
];
