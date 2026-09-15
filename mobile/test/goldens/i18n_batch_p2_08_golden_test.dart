import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:golden_toolkit/golden_toolkit.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/memory/presentation/widgets/memory_evidence_badge.dart';
import 'package:sparkle/l10n/app_localizations_en.dart';
import 'package:sparkle/l10n/app_localizations_zh.dart';

const bool _enableP208Goldens = bool.fromEnvironment('ENABLE_P2_08_GOLDEN');

void main() {
  tearDown(I18nService.instance.reset);

  testGoldens(
    'memory evidence badge switches zh and en copy',
    (tester) async {
      await loadAppFonts();

      I18nService.instance
          .updateLocale(const Locale('zh'), AppLocalizationsZh());
      await tester.pumpWidgetBuilder(
        const _BadgeHarness(),
        surfaceSize: const Size(260, 96),
      );
      expect(find.text('已隐藏'), findsOneWidget);

      I18nService.instance
          .updateLocale(const Locale('en'), AppLocalizationsEn());
      await tester.pumpWidgetBuilder(
        _BadgeHarness(key: UniqueKey()),
        surfaceSize: const Size(260, 96),
      );
      await tester.pump();
      expect(find.text('Redacted'), findsOneWidget);

      await screenMatchesGolden(tester, 'i18n_batch_p2_08_badge_en');
    },
    skip: !_enableP208Goldens,
  );
}

class _BadgeHarness extends StatelessWidget {
  const _BadgeHarness({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
        home: Scaffold(
          body: Center(
            child: Wrap(
              spacing: 12,
              children: const [
                MemoryEvidenceBadge(status: MemoryEvidenceStatus.ok),
                MemoryEvidenceBadge(status: MemoryEvidenceStatus.redacted),
                MemoryEvidenceBadge(status: MemoryEvidenceStatus.missing),
              ],
            ),
          ),
        ),
      );
}
