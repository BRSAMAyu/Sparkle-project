// A-4 regression tests: visual element config color extraction must tolerate
// the polymorphic shapes shipped by the catalogue.
//
// Field evidence (android-round1.md A-4, field-test logcat 19:24:48):
//   ProfileScreen._colorFromElement (profile_screen.dart:437) crashed the
//   whole Profile tab with:
//   type '_Map<String, dynamic>' is not a subtype of type 'List<dynamic>?'
//   Registered users equip elements whose `config['gradient']` is a Map
//   envelope ({'colors': [...]}) — the canonical shape parsed by
//   visual_element_card.dart — while the screen hard-cast it to List.
//
// The tolerant parse now lives in the model (VisualElementModel
// .prestigeAccentHex); these tests lock the shape matrix.
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/shared/entities/visual_element_model.dart';

VisualElementModel elementWithConfig(Map<String, dynamic> config) => VisualElementModel.fromJson(<String, dynamic>{
    'id': 've_test',
    'name': 'Test Element',
    'element_type': 'background',
    'rarity': 'rare',
    'unlock_source': 'system',
    'is_default': false,
    'sort_order': 1,
    'config': config,
  });

void main() {
  test('hex-string List for colors yields the first parsable hex', () {
    final element = elementWithConfig(<String, dynamic>{
      'colors': ['#7A93B4', '#94AFD2'],
    });
    expect(element.prestigeAccentHex, '7A93B4');
  });

  test(
      'Map-envelope gradient (canonical catalogue shape) does not throw and '
      'yields the first nested hex — the exact shape that crashed the tab',
      () {
    final element = elementWithConfig(<String, dynamic>{
      'gradient': <String, dynamic>{
        'colors': ['#AB47BC', '#FFA726'],
        'begin': 'top',
        'end': 'bottom',
      },
    });
    expect(element.prestigeAccentHex, 'AB47BC');
  });

  test('gradient as hex-string List still works (legacy shape)', () {
    final element = elementWithConfig(<String, dynamic>{
      'gradient': ['#42A5F5'],
    });
    expect(element.prestigeAccentHex, '42A5F5');
  });

  test('colors taking precedence over gradient is preserved', () {
    final element = elementWithConfig(<String, dynamic>{
      'colors': ['#111111'],
      'gradient': <String, dynamic>{
        'colors': ['#222222'],
      },
    });
    expect(element.prestigeAccentHex, '111111');
  });

  test('8-digit ARGB hex is accepted', () {
    final element = elementWithConfig(<String, dynamic>{
      'colors': ['FF335577'],
    });
    expect(element.prestigeAccentHex, 'FF335577');
  });

  test('malformed / empty / non-color payloads return null instead of throwing',
      () {
    expect(
      elementWithConfig(const <String, dynamic>{}).prestigeAccentHex,
      isNull,
    );
    expect(
      elementWithConfig(<String, dynamic>{
        'colors': <String>['nothex', '12345'],
      }).prestigeAccentHex,
      isNull,
    );
    expect(
      elementWithConfig(<String, dynamic>{
        'gradient': <String, dynamic>{'stops': [0.0, 1.0]},
      }).prestigeAccentHex,
      isNull,
    );
    // The exact pre-fix crash payload: a Map where a List was hard-cast.
    expect(
      elementWithConfig(<String, dynamic>{
        'colors': <String, dynamic>{'primary': '#7A93B4'},
      }).prestigeAccentHex,
      isNull,
      reason:
          'A Map colors envelope without a nested colors list must degrade to '
          'null (fallback color) rather than crash',
    );
  });
}
