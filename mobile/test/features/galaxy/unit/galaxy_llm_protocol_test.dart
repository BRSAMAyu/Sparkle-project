import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/galaxy/domain/entities/galaxy_llm_protocol.dart';

void main() {
  test('LLMNodeSpec normalizes legacy fractional mastery into 0-100 score', () {
    final node = LLMNodeSpec.fromJson(const <String, dynamic>{
      'id': 'cn.tcp_flow_control',
      'name': 'TCP Flow Control',
      'sector': 'TECH',
      'mastery_score': 0.25,
    });

    expect(node.masteryScore, 25);
  });
}
