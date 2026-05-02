import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/models/aurora_correction_payload.dart';

void main() {
  group('AuroraCorrectionPayload', () {
    test('dashboard freeform payload uses the standard shape', () {
      final payload = AuroraCorrectionPayload.freeform(
        surface: AuroraCorrectionSurface.dashboard,
        semanticValue: 'freeform_correction',
        label: 'Actually I am not anxious.',
        freeformText: 'Actually I am not anxious.',
        isDisconfirming: true,
        bandStatus: 'needs_confirm',
        conversationId: 'conversation-1',
      ).toJson();

      expect(payload['surface'], 'dashboard');
      expect(payload['source'], 'freeform_input');
      expect(payload['semantic_value'], 'freeform_correction');
      expect(payload['label'], 'Actually I am not anxious.');
      expect(payload['freeform_text'], 'Actually I am not anxious.');
      expect(payload['is_freeform'], isTrue);
      expect(payload['is_disconfirming'], isTrue);
      expect(payload['band_status'], 'needs_confirm');
      expect(payload['conversation_id'], 'conversation-1');
      expect(payload['telemetry_id'], isNotEmpty);
      expect(payload['group_id'], isNotEmpty);
    });

    test('chat chip payload keeps semantic value metadata-only', () {
      final payload = AuroraCorrectionPayload.chip(
        surface: AuroraCorrectionSurface.chat,
        semanticValue: 'strategy_too_aggressive',
        label: 'Go slower',
        isDisconfirming: true,
        bandStatus: 'calibrated',
        telemetryId: 'telemetry-1',
        groupId: 'group-1',
        conversationId: 'conversation-2',
        messageId: 'message-9',
      ).toJson();

      expect(payload['surface'], 'chat');
      expect(payload['source'], 'predicted_chip');
      expect(payload['label'], 'Go slower');
      expect(payload['semantic_value'], 'strategy_too_aggressive');
      expect(payload['label'], isNot(contains('strategy_too_aggressive')));
      expect(payload['is_freeform'], isFalse);
      expect(payload['is_disconfirming'], isTrue);
      expect(payload['telemetry_id'], 'telemetry-1');
      expect(payload['group_id'], 'group-1');
      expect(payload['conversation_id'], 'conversation-2');
      expect(payload['message_id'], 'message-9');
    });

    test('status band correction uses status_band surface', () {
      final payload = AuroraCorrectionPayload.chip(
        surface: AuroraCorrectionSurface.statusBand,
        semanticValue: 'low_energy',
        label: 'Low energy',
        isDisconfirming: false,
        bandStatus: 'sensing',
      ).toJson();

      expect(payload['surface'], 'status_band');
      expect(payload['source'], 'predicted_chip');
      expect(payload['semantic_value'], 'low_energy');
      expect(payload['label'], 'Low energy');
      expect(payload['freeform_text'], isEmpty);
    });

    test('calibration override uses explicit override source', () {
      final payload = AuroraCorrectionPayload.calibrationOverride(
        surface: AuroraCorrectionSurface.dashboard,
        semanticValue: 'quick_calibration',
        label: 'Quick calibration',
        bandStatus: 'cooling_down',
      ).toJson();

      expect(payload['surface'], 'dashboard');
      expect(payload['source'], 'calibration_override');
      expect(payload['semantic_value'], 'quick_calibration');
      expect(payload['is_freeform'], isFalse);
      expect(payload['is_disconfirming'], isFalse);
    });
  });
}
