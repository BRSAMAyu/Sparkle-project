import 'dart:convert';
import 'package:hive_flutter/hive_flutter.dart';
import 'package:sparkle/features/cognitive/data/models/cognitive_fragment_model.dart';

class LocalCognitiveRepository {
  static const String _boxName = 'cognitive_offline_queue';

  Future<void> _ensureBoxOpen() async {
    if (!Hive.isBoxOpen(_boxName)) {
      await Hive.openBox<String>(_boxName);
    }
  }

  Future<void> queueFragment(CognitiveFragmentCreate data) async {
    await _ensureBoxOpen();
    final box = Hive.box<String>(_boxName);
    final jsonString = jsonEncode(data.toJson());
    await box.add(jsonString);
  }

  Future<List<Map<String, dynamic>>> getQueueRaw() async {
    await _ensureBoxOpen();
    final box = Hive.box<String>(_boxName);
    return box.values
        .map((e) => jsonDecode(e) as Map<String, dynamic>)
        .toList();
  }

  Future<void> removeFromQueue(int index) async {
    await _ensureBoxOpen();
    final box = Hive.box<String>(_boxName);
    await box.deleteAt(index);
  }

  Future<void> clearQueue() async {
    await _ensureBoxOpen();
    final box = Hive.box<String>(_boxName);
    await box.clear();
  }
}
