import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/services/guest_conversion_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('GuestConversionService（N40 价值信号常量 + 一次性标记持久层）', () {
    test('recordValueSignal 累计计数并记录信号稳定标识', () async {
      SharedPreferences.setMockInitialValues({});
      final prefs = await SharedPreferences.getInstance();
      final service = GuestConversionService(prefs);

      await service.recordValueSignal(GuestValueSignal.firstTaskCompleted);

      expect(service.signalCount, 1);
      expect(service.lastSignalKey, GuestValueSignal.firstTaskCompleted.key);
      expect(prefs.getInt('guest_conversion_signal_count'), 1);
      expect(
        prefs.getString('guest_conversion_last_signal'),
        'first_task_completed',
      );
      expect(service.isDismissedUntilNextSignal, isFalse);
    });

    test('点掉后持久挂起；下个价值信号到达即重新武装（不再弹直到下个信号）',
        () async {
      SharedPreferences.setMockInitialValues({});
      final prefs = await SharedPreferences.getInstance();
      final service = GuestConversionService(prefs);

      await service.recordValueSignal(GuestValueSignal.firstTaskCompleted);
      await service.dismissUntilNextSignal();

      expect(service.isDismissedUntilNextSignal, isTrue);
      expect(
        prefs.getBool('guest_conversion_dismissed_until_next_signal'),
        isTrue,
      );

      await service.recordValueSignal(GuestValueSignal.firstDiagnosisOutput);

      expect(service.isDismissedUntilNextSignal, isFalse);
      expect(
        prefs.containsKey('guest_conversion_dismissed_until_next_signal'),
        isFalse,
      );
      expect(service.signalCount, 2);
      expect(service.lastSignalKey, 'first_diagnosis_output');
    });

    test('新建实例恢复持久事实（跨会话语义）', () async {
      SharedPreferences.setMockInitialValues({
        'guest_conversion_signal_count': 3,
        'guest_conversion_last_signal': 'first_memory_referenced',
        'guest_conversion_dismissed_until_next_signal': true,
      });
      final prefs = await SharedPreferences.getInstance();
      final service = GuestConversionService(prefs);

      expect(service.signalCount, 3);
      expect(service.lastSignalKey, 'first_memory_referenced');
      expect(service.isDismissedUntilNextSignal, isTrue);
    });
  });
}
