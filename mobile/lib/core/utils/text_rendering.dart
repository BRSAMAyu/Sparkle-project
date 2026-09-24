const sparkleFontFallback = <String>[
  'PingFang SC',
  'Hiragino Sans GB',
  'Heiti SC',
  'Noto Sans SC',
  'Noto Sans CJK SC',
  'Source Han Sans SC',
  'Microsoft YaHei',
  'Arial Unicode MS',
  'Apple Color Emoji',
  'Segoe UI Emoji',
  'Noto Color Emoji',
  'Noto Emoji',
];

/// Removes invisible and replacement characters that commonly surface as
/// question-mark glyphs while preserving valid CJK and emoji content.
String sanitizeDisplayText(String raw) {
  final normalizedNewlines =
      raw.replaceAll('\r\n', '\n').replaceAll('\r', '\n');
  final buf = StringBuffer();

  for (var i = 0; i < normalizedNewlines.length; i++) {
    final c = normalizedNewlines.codeUnitAt(i);

    if (c >= 0x20 && c <= 0x7E) {
      buf.writeCharCode(c);
      continue;
    }
    if (c == 0x0A || c == 0x09) {
      buf.writeCharCode(c);
      continue;
    }
    if (c == 0x200D || c == 0xFE0F) {
      buf.writeCharCode(c);
      continue;
    }
    if (c >= 0x00A0) {
      if (c == 0x00AD) continue;
      if (c >= 0x200B && c <= 0x200C) continue;
      if (c >= 0x200E && c <= 0x200F) continue;
      if (c >= 0x2028 && c <= 0x2029) continue;
      if (c >= 0x2060 && c <= 0x2064) continue;
      if (c == 0x2066 || c == 0x2067 || c == 0x2068 || c == 0x2069) continue;
      if (c == 0xFEFF || c == 0xFFFD || c == 0xFE0E) continue;
      if (c >= 0xFFF0 && c <= 0xFFFC) continue;
      buf.writeCharCode(c);
    }
  }

  return buf.toString();
}

String? sanitizeNullableDisplayText(dynamic value) {
  if (value == null) return null;
  final text = sanitizeDisplayText(value.toString()).trim();
  return text.isEmpty ? null : text;
}

bool _isCjkIdeograph(int c) =>
    (c >= 0x3400 && c <= 0x4DBF) || // Extension A
    (c >= 0x4E00 && c <= 0x9FFF) || // Unified Ideographs
    (c >= 0xF900 && c <= 0xFAFF); // Compatibility Ideographs

bool _isLatinLetterOrDigit(int c) =>
    (c >= 0x30 && c <= 0x39) || // 0-9
    (c >= 0x41 && c <= 0x5A) || // A-Z
    (c >= 0x61 && c <= 0x7A); // a-z

/// Inserts a single space between CJK ideographs and Latin letters/digits so
/// composed display lines (e.g. AI-generated daily context sentences mixing a
/// task title into Chinese prose) never render jammed like
/// `先完成TimedPracticeLoop打破昨日零记录`. Runs that already contain a
/// separating space are left untouched.
String autoSpaceCjkLatin(String raw) {
  if (raw.isEmpty) {
    return raw;
  }
  final buf = StringBuffer();
  var prevWasCjk = false;
  var prevWasLatin = false;
  for (var i = 0; i < raw.length; i++) {
    final c = raw.codeUnitAt(i);
    final isCjk = _isCjkIdeograph(c);
    final isLatin = _isLatinLetterOrDigit(c);
    if ((prevWasCjk && isLatin) || (prevWasLatin && isCjk)) {
      buf.write(' ');
    }
    buf.writeCharCode(c);
    prevWasCjk = isCjk;
    prevWasLatin = isLatin;
  }
  return buf.toString();
}

dynamic sanitizeTextPayload(dynamic value) {
  if (value is String) {
    return sanitizeDisplayText(value);
  }
  if (value is List) {
    return value.map<dynamic>(sanitizeTextPayload).toList(growable: false);
  }
  if (value is Map) {
    return Map<String, dynamic>.fromEntries(
      value.entries.map(
        (entry) => MapEntry(
          entry.key.toString(),
          sanitizeTextPayload(entry.value),
        ),
      ),
    );
  }
  return value;
}

Map<String, dynamic> sanitizeTextMap(Map<String, dynamic> value) =>
    Map<String, dynamic>.from(sanitizeTextPayload(value) as Map);
