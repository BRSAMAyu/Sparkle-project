import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:hive_flutter/hive_flutter.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:sparkle/app/app.dart';
import 'package:sparkle/core/services/chat_cache_service.dart';
import 'package:sparkle/core/services/demo_data_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize Hive for local storage
  await Hive.initFlutter();
  
  // Register Chat Adapters
  ChatCacheService.registerAdapters();

  // Initialize SharedPrefs
  await SharedPreferences.getInstance();

  // Enable Demo Mode
  DemoDataService.isDemoMode = true;

  // TODO: Open Hive boxes
  await Hive.openBox('settings');
  await Hive.openBox('user');

  runApp(
    const ProviderScope(
      child: SparkleApp(),
    ),
  );
}
