import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/data/models/compact_knowledge_node.dart';

void main() {
  group('CompactKnowledgeNode', () {
    test('should correctly pack and unpack values', () {
      final node = CompactKnowledgeNode.create(
        id: '123',
        x: 10.5,
        y: 20.0,
        mastery: 85,
        isUnlocked: true,
        isMastered: false,
        subjectId: 5,
        importance: 3,
      );

      expect(node.idHash, '123'.hashCode);
      expect(node.x, 10.5);
      expect(node.y, 20.0);
      expect(node.mastery, 85);
      expect(node.isUnlocked, true);
      expect(node.isMastered, false);
      expect(node.subjectId, 5);
      expect(node.importance, 3);
    });

    test('should clamp mastery value between 0 and 100', () {
      final node = CompactKnowledgeNode.create(
        id: '123',
        x: 0,
        y: 0,
        mastery: 150,
        isUnlocked: true,
        isMastered: false,
        subjectId: 0,
        importance: 0,
      );

      expect(node.mastery, 100);
      
      final nodeNegative = CompactKnowledgeNode.create(
        id: '123',
        x: 0,
        y: 0,
        mastery: -50,
        isUnlocked: true,
        isMastered: false,
        subjectId: 0,
        importance: 0,
      );

      expect(nodeNegative.mastery, 0);
    });

    test('should handle bitwise operations correctly for flags', () {
      final node = CompactKnowledgeNode.create(
        id: '123',
        x: 0,
        y: 0,
        mastery: 50,
        isUnlocked: true,
        isMastered: true,
        subjectId: 63, // Max 6 bits
        importance: 15, // Max 4 bits
      );

      expect(node.isUnlocked, true);
      expect(node.isMastered, true);
      expect(node.subjectId, 63);
      expect(node.importance, 15);
    });

    test('copyWith should only update specified fields', () {
      final node = CompactKnowledgeNode.create(
        id: '123',
        x: 10,
        y: 10,
        mastery: 50,
        isUnlocked: false,
        isMastered: false,
        subjectId: 1,
        importance: 1,
      );

      final updated = node.copyWith(
        mastery: 100,
        isUnlocked: true,
      );

      expect(updated.mastery, 100);
      expect(updated.isUnlocked, true);
      // Others remain unchanged
      expect(updated.isMastered, false);
      expect(updated.subjectId, 1);
      expect(updated.importance, 1);
      expect(updated.x, 10);
    });
  });
}
