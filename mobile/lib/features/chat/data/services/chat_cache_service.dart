import 'dart:convert';

import 'package:hive_flutter/hive_flutter.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';

class ChatCacheService {
  factory ChatCacheService() => _instance;
  ChatCacheService._internal();
  static const String _groupPrefix = 'group_messages_';
  static const String _privatePrefix = 'private_messages_';
  static const String _pendingGroupPrefix = 'pending_group_';
  static const String _pendingPrivatePrefix = 'pending_private_';

  // Singleton
  static final ChatCacheService _instance = ChatCacheService._internal();

  /// Initialize and register adapters
  /// This should be called in main.dart
  static void registerAdapters() {
    Hive.registerAdapter(UserStatusAdapter());
    Hive.registerAdapter(MessageTypeAdapter());
    Hive.registerAdapter(UserBriefAdapter());
    Hive.registerAdapter(MessageInfoAdapter());
    Hive.registerAdapter(PrivateMessageInfoAdapter());
  }

  Future<void> saveGroupMessages(
      String groupId, List<MessageInfo> messages,) async {
    final box = await Hive.openBox<MessageInfo>('$_groupPrefix$groupId');
    // We only keep the latest 100 messages for now
    await box.clear();
    await box.addAll(messages.take(100));
  }

  Future<List<MessageInfo>> getCachedGroupMessages(String groupId) async {
    final box = await Hive.openBox<MessageInfo>('$_groupPrefix$groupId');
    return box.values.toList();
  }

  Future<void> savePrivateMessages(
      String friendId, List<PrivateMessageInfo> messages,) async {
    final box =
        await Hive.openBox<PrivateMessageInfo>('$_privatePrefix$friendId');
    await box.clear();
    await box.addAll(messages.take(100));
  }

  Future<List<PrivateMessageInfo>> getCachedPrivateMessages(
      String friendId,) async {
    final box =
        await Hive.openBox<PrivateMessageInfo>('$_privatePrefix$friendId');
    return box.values.toList();
  }

  Future<void> clearAllCache() async {
    // This is expensive to implement perfectly with dynamic box names,
    // but we can clear known prefixes if we track them.
    // For now, assume simple cleanup or rely on Hive.deleteFromDisk
  }

  Future<void> enqueuePendingGroupMessage(
      String groupId, Map<String, dynamic> payload,) async {
    final box = await Hive.openBox<String>('$_pendingGroupPrefix$groupId');
    final nonce = payload['nonce']?.toString();
    if (nonce == null || nonce.isEmpty) return;
    await box.put(nonce, jsonEncode(payload));
  }

  Future<List<Map<String, dynamic>>> getPendingGroupMessages(
      String groupId,) async {
    final box = await Hive.openBox<String>('$_pendingGroupPrefix$groupId');
    return box.values
        .map((raw) => jsonDecode(raw) as Map<String, dynamic>)
        .toList();
  }

  Future<void> removePendingGroupMessage(String groupId, String nonce) async {
    final box = await Hive.openBox<String>('$_pendingGroupPrefix$groupId');
    await box.delete(nonce);
  }

  Future<void> enqueuePendingPrivateMessage(
      String friendId, Map<String, dynamic> payload,) async {
    final box = await Hive.openBox<String>('$_pendingPrivatePrefix$friendId');
    final nonce = payload['nonce']?.toString();
    if (nonce == null || nonce.isEmpty) return;
    await box.put(nonce, jsonEncode(payload));
  }

  Future<List<Map<String, dynamic>>> getPendingPrivateMessages(
      String friendId,) async {
    final box = await Hive.openBox<String>('$_pendingPrivatePrefix$friendId');
    return box.values
        .map((raw) => jsonDecode(raw) as Map<String, dynamic>)
        .toList();
  }

  Future<void> removePendingPrivateMessage(
      String friendId, String nonce,) async {
    final box = await Hive.openBox<String>('$_pendingPrivatePrefix$friendId');
    await box.delete(nonce);
  }
}
