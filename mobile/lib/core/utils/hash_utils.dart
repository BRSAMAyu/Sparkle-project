import 'dart:convert';
import 'package:crypto/crypto.dart';

/// Utility class for hashing operations
class HashUtils {
  /// Generate a SHA-256 fingerprint for translation context tracking.
  /// 
  /// Agreement: hash(text + context_before + context_after + page_no)
  static String generateTranslationFingerprint({
    required String text,
    String? contextBefore,
    String? contextAfter,
    int? pageNo,
  }) {
    final buffer = StringBuffer()
      ..write(text.trim())
      ..write('_')
      ..write((contextBefore ?? '').trim())
      ..write('_')
      ..write((contextAfter ?? '').trim())
      ..write('_')
      ..write(pageNo?.toString() ?? '');
    
    final bytes = utf8.encode(buffer.toString());
    return sha256.convert(bytes).toString();
  }
}
