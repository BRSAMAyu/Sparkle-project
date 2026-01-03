import 'package:flutter/foundation.dart';
import 'dart:typed_data';

/// Compact Data Representation for Knowledge Node
/// 
/// 优化策略:
/// 1. 使用 int idHash 代替 String UUID (减少 ~50% 内存)
/// 2. 使用 Float32List 存储位置 (减少 ~50% 内存)
/// 3. 使用位运算打包状态 (减少 ~87% 内存)
class CompactKnowledgeNode {
  /// 哈希值代替 UUID 字符串
  final int idHash;

  /// 父节点 ID 哈希 (Optional)
  final int? parentIdHash;

  /// 节点名称 (Reference overhead only)
  final String name;

  /// [x, y] 坐标 (Immutable)
  final Float32List position;

  /// 位运算存储状态
  /// 0-7: mastery (0-100)
  /// 8: isUnlocked (0/1)
  /// 9: isMastered (0/1)
  /// 10-15: sectorIndex (0-63)
  /// 16-19: importance (0-5)
  /// 20-23: studyCount (0-15)
  /// 24-31: reserved
  final int _packedState;

  const CompactKnowledgeNode({
    required this.idHash,
    this.parentIdHash,
    required this.name,
    required this.position,
    required int packedState,
  }) : _packedState = packedState;

  /// Factory to create from individual fields
  factory CompactKnowledgeNode.create({
    required String id,
    String? parentId,
    required String name,
    required double x,
    required double y,
    required int mastery,
    required bool isUnlocked,
    required bool isMastered,
    required int sectorIndex,
    required int importance,
    int studyCount = 0,
  }) {
    // 1. Hash ID
    final idHash = id.hashCode;
    final parentIdHash = parentId?.hashCode;

    // 2. Position
    final rawPos = Float32List(2);
    rawPos[0] = x;
    rawPos[1] = y;
    final position = UnmodifiableFloat32ListView(rawPos);

    // 3. Pack State
    int packed = 0;
    
    // mastery (0-7 bits)
    packed |= (mastery.clamp(0, 100) & 0xFF);
    
    // isUnlocked (8 bit)
    if (isUnlocked) packed |= (1 << 8);
    
    // isMastered (9 bit)
    if (isMastered) packed |= (1 << 9);
    
    // sectorIndex (10-15 bits, max 63)
    packed |= ((sectorIndex & 0x3F) << 10);

    // importance (16-19 bits, max 15)
    packed |= ((importance & 0x0F) << 16);

    // studyCount (20-23 bits, max 15)
    packed |= ((studyCount.clamp(0, 15) & 0x0F) << 20);

    return CompactKnowledgeNode(
      idHash: idHash,
      parentIdHash: parentIdHash,
      name: name,
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
  
  int get sectorIndex => (_packedState >> 10) & 0x3F;
  
  int get subjectId => sectorIndex;

  int get importance => (_packedState >> 16) & 0x0F;

  int get studyCount => (_packedState >> 20) & 0x0F;

  /// Create a copy with modified fields (efficiently)
  CompactKnowledgeNode copyWith({
    String? name,
    int? mastery,
    bool? isUnlocked,
    bool? isMastered,
    int? studyCount,
    Float32List? position,
  }) {
    int newPacked = _packedState;

    if (mastery != null) {
      newPacked &= ~0xFF;
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

    if (studyCount != null) {
      newPacked &= ~(0x0F << 20);
      newPacked |= ((studyCount.clamp(0, 15) & 0x0F) << 20);
    }
    
    Float32List newPosition = this.position;
    if (position != null) {
        // Create new unmodifiable view for safety (Deep Copy)
        newPosition = UnmodifiableFloat32ListView(Float32List.fromList(position));
    }

    return CompactKnowledgeNode(
      idHash: idHash,
      parentIdHash: parentIdHash,
      name: name ?? this.name,
      position: newPosition,
      packedState: newPacked,
    );
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is CompactKnowledgeNode &&
        other.idHash == idHash &&
        other.parentIdHash == parentIdHash &&
        other.name == name &&
        other._packedState == _packedState &&
        (other.position == position || (other.position[0] == position[0] && other.position[1] == position[1]));
  }

  @override
  int get hashCode => Object.hash(idHash, parentIdHash, name, _packedState, position[0], position[1]);
}
