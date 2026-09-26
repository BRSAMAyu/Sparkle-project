import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/models/intervention.dart';

/// V3-FIX-301 回归契约：backend InterventionLevel SCREAMING 值集
/// {SILENT_MARKER/TOAST/CARD/FULL_SCREEN_MODAL}（schemas/intervention.py，
/// intervention_service 下发）在 mobile parse 面逐值显式接受。
///
/// 缺陷史：`parseInterventionLevel('SILENT_MARKER')` 此前无显式 case，落
/// `default` 有损降级——恰好与目标值同值（silent），值断言无法区分「显式接受」
/// 与「兜底吞没」；故红面由源码契约断言钉死（parse 函数内必须存在
/// `case 'silent_marker':`，即 ENUM-PARITY guard wire_map 依赖的已接受字面量），
/// 大小写归一与别名合并行为由值断言钉死。
void main() {
  group('parseInterventionLevel（V3-FIX-301）', () {
    test('backend 四值大写 wire 字面量逐值归一', () {
      expect(parseInterventionLevel('SILENT_MARKER'), InterventionLevel.silent);
      expect(parseInterventionLevel('TOAST'), InterventionLevel.toast);
      expect(parseInterventionLevel('CARD'), InterventionLevel.card);
      expect(
        parseInterventionLevel('FULL_SCREEN_MODAL'),
        InterventionLevel.modal,
      );
    });

    test('full_screen_modal→modal 别名合并与小写形态保持', () {
      expect(parseInterventionLevel('full_screen_modal'), InterventionLevel.modal);
      expect(parseInterventionLevel('modal'), InterventionLevel.modal);
      expect(parseInterventionLevel('toast'), InterventionLevel.toast);
      expect(parseInterventionLevel('Card'), InterventionLevel.card);
    });

    test('unknown 哨兵外值与 null 落 silent 兜底', () {
      expect(parseInterventionLevel('banner'), InterventionLevel.silent);
      expect(parseInterventionLevel(''), InterventionLevel.silent);
      expect(parseInterventionLevel(null), InterventionLevel.silent);
    });

    test('SILENT_MARKER 有显式 case 而非 default 有损降级（源码契约）', () {
      // 守卫面：parse 函数体内必须显式声明 'silent_marker' case——这是
      // backend SILENT_MARKER 下发的已接受面（guard wire_map 同源证据）；
      // 删除该 case 即单边断链，立即红。
      final source = File(
        'test/unit/../../lib/core/models/intervention.dart',
      );
      expect(source.existsSync(), isTrue, reason: '源文件缺失: ${source.path}');
      final body = source.readAsStringSync();
      final parseStart = body.indexOf('InterventionLevel parseInterventionLevel');
      expect(parseStart, greaterThanOrEqualTo(0), reason: 'parse 函数缺失');
      final parseBody = body.substring(
        parseStart,
        body.indexOf('}', body.indexOf('default', parseStart)) + 1,
      );
      expect(
        parseBody.contains("case 'silent_marker':"),
        isTrue,
        reason:
            'parseInterventionLevel 缺少 case \'silent_marker\' 显式接受面'
            '（SILENT_MARKER 将落 default 有损降级，V3-FIX-301 回归）',
      );
    });
  });
}
