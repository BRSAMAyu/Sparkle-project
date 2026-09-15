import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/l10n/app_localizations.dart';

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
    final sections = _isTerms ? _termsSections(AppLocalizations.of(context)!) : _privacySections(AppLocalizations.of(context)!);

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
                      context.l10n.legalCurrentVersion,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: DS.textSecondary,
                          ),
                    ),
                    const SizedBox(height: DS.spacing8),
                    Text(
                      context.l10n.legalLastUpdated,
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

List<_LegalSection> _termsSections(AppLocalizations l10n) {
  return [
    _LegalSection(
      l10n.legalTermsServiceTitle,
      l10n.legalTermsServiceBody,
    ),
    _LegalSection(
      l10n.legalTermsAccountTitle,
      l10n.legalTermsAccountBody,
    ),
    _LegalSection(
      l10n.legalTermsContentTitle,
      l10n.legalTermsContentBody,
    ),
    _LegalSection(
      l10n.legalTermsDeletionTitle,
      l10n.legalTermsDeletionBody,
    ),
  ];
}

List<_LegalSection> _privacySections(AppLocalizations l10n) {
  return [
    _LegalSection(
      l10n.legalPrivacyCollectTitle,
      l10n.legalPrivacyCollectBody,
    ),
    _LegalSection(
      l10n.legalPrivacyPurposeTitle,
      l10n.legalPrivacyPurposeBody,
    ),
    _LegalSection(
      l10n.legalPrivacySecurityTitle,
      l10n.legalPrivacySecurityBody,
    ),
    _LegalSection(
      l10n.legalPrivacyRightsTitle,
      l10n.legalPrivacyRightsBody,
    ),
  ];
}
