import 'package:flutter/foundation.dart';

/// Compact Data Representation for Knowledge Node
/// 
/// 优化策略:
/// 1. 使用 int idHash 代替 String UUID (减少 ~50% 内存)
/// 2. 使用 Float32List 存储位置 (减少 ~50% 内存)
/// 3. 使用位运算打包状态 (减少 ~87% 内存)
class CompactKnowledgeNode {
  /// 哈希值代替 UUID 字符串
  final int idHash;

  /// [x, y] 坐标
  final Float32List position;

  /// 位运算存储状态
  /// 0-7: mastery (0-100)
  /// 8: isUnlocked (0/1)
  /// 9: isMastered (0/1)
  /// 10-15: subjectId (0-63)
  /// 16-19: importance (0-5)
  /// 20-31: reserved
  final int _packedState;

  const CompactKnowledgeNode({
    required this.idHash,
    required this.position,
    required int packedState,
  }) : _packedState = packedState;

  /// Factory to create from individual fields
  factory CompactKnowledgeNode.create({
    required String id,
    required double x,
    required double y,
    required int mastery,
    required bool isUnlocked,
    required bool isMastered,
    required int subjectId,
    required int importance,
  }) {
    // 1. Hash ID
    final idHash = id.hashCode;

    // 2. Position
    final position = Float32List(2);
    position[0] = x;
    position[1] = y;

    // 3. Pack State
    int packed = 0;
    
    // mastery (0-7 bits)
    packed |= (mastery.clamp(0, 100) & 0xFF);
    
    // isUnlocked (8 bit)
    if (isUnlocked) packed |= (1 << 8);
    
    // isMastered (9 bit)
    if (isMastered) packed |= (1 << 9);
    
    // subjectId (10-15 bits, max 63)
    packed |= ((subjectId & 0x3F) << 10);

    // importance (16-19 bits, max 15)
    packed |= ((importance & 0x0F) << 16);

    return CompactKnowledgeNode(
      idHash: idHash,
      position: position,
      packedState: packed,
    );
  }

  // Getters using bitwise operations
  
  double get x => position[0];
  double get y => position[1];
  
  int get mastery => _packedState & 0xFF;
  
  bool get isUnlocked => ((_packedState >> 8) & 1) == 1;
  
  bool get isMastered => ((_packedState >> 9) & 1) == 1;
  
  int get subjectId => (_packedState >> 10) & 0x3F;

  int get importance => (_packedState >> 16) & 0x0F;

  /// Create a copy with modified fields (efficiently)
  CompactKnowledgeNode copyWith({
    int? mastery,
    bool? isUnlocked,
    bool? isMastered,
  }) {
    int newPacked = _packedState;

    if (mastery != null) {
      // Clear first 8 bits
      newPacked &= ~0xFF;
      // Set new mastery
      newPacked |= (mastery.clamp(0, 100) & 0xFF);
    }

    if (isUnlocked != null) {
      if (isUnlocked) {
        newPacked |= (1 << 8);
      } else {
        newPacked &= ~(1 << 8);
      }
    }

    if (isMastered != null) {
      if (isMastered) {
        newPacked |= (1 << 9);
      } else {
        newPacked &= ~(1 << 9);
      }
    }

    return CompactKnowledgeNode(
      idHash: idHash,
      position: position, // Shared reference (immutable content effectively)
      packedState: newPacked,
    );
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is CompactKnowledgeNode &&
        other.idHash == idHash &&
        other._packedState == _packedState &&
        // Optimize: assume position doesn't change if reference is same or check values
        (other.position == position || (other.position[0] == position[0] && other.position[1] == position[1]));
  }

  @override
  int get hashCode => Object.hash(idHash, _packedState, position[0], position[1]);
}
