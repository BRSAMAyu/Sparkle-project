import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/star_map_painter.dart';

void main() {
  group('clampSectorLabelLeft（V13 D-11 扇区标签被右侧控件栏截断）', () {
    test('锚点在画布中部时标签位置不受影响', () {
      // 412dp 画布、标签宽 90：可用右界 412-96-90=226，180 在区间内。
      expect(
        clampSectorLabelLeft(
          canvasWidth: 412,
          labelLeft: 180,
          labelWidth: 90,
        ),
        180,
      );
    });

    test('右缘标签被收敛进控件栏以内（Inspiration → 不再截断）', () {
      // 锚点使标签矩形右缘伸进右侧控件栏（96px 预留）。
      final clamped = clampSectorLabelLeft(
        canvasWidth: 412,
        labelLeft: 412 - 45 - 20, // 中心靠近右缘，右缘越界
        labelWidth: 90,
      );
      expect(clamped, lessThanOrEqualTo(412 - 96 - 90));
      expect(clamped, greaterThanOrEqualTo(8));
    });

    test('标签左缘不会越出画布左界', () {
      expect(
        clampSectorLabelLeft(
          canvasWidth: 412,
          labelLeft: -30,
          labelWidth: 90,
        ),
        8,
      );
    });

    test('极窄画布（区间倒挂）安全退回左缘 8px，不抛异常', () {
      // 标签比可用宽度还宽：maxLeft < 8 → 退回 8。
      expect(
        clampSectorLabelLeft(
          canvasWidth: 60,
          labelLeft: 10,
          labelWidth: 200,
        ),
        8,
      );
    });
  });
}
