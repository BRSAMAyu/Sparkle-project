import 'dart:ffi';
import 'dart:io';

import 'package:isar/isar.dart';

/// Initialize IsarCore using the bundled native library instead of downloading.
///
/// The `download: true` flag in `Isar.initializeIsarCore` fails in test
/// environments because Flutter's test binding intercepts HTTP and returns 400.
/// Use this helper in all test `setUpAll` callbacks that need Isar.
Future<void> initializeIsarCoreForTesting() async {
  await Isar.initializeIsarCore(
    libraries: <Abi, String>{Abi.current(): _isarCoreLibraryPath()},
  );
}

String _isarCoreLibraryPath() {
  final root = Directory.current.path;
  if (Platform.isMacOS) {
    return '$root/third_party_plugins/isar_flutter_libs/macos/libisar.dylib';
  }
  if (Platform.isLinux) {
    return '$root/third_party_plugins/isar_flutter_libs/linux/libisar.so';
  }
  throw UnsupportedError('IsarCore not available on ${Platform.operatingSystem}');
}
