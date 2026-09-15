const String sparkleFileReferenceScheme = 'sparkle-file://';

bool isSparkleFileReference(String? value) =>
    value != null && value.startsWith(sparkleFileReferenceScheme);

String buildSparkleFileReference(String fileId) =>
    '$sparkleFileReferenceScheme$fileId';

String? parseSparkleFileId(String? value) {
  if (!isSparkleFileReference(value)) {
    return null;
  }
  final fileId = value!.substring(sparkleFileReferenceScheme.length).trim();
  return fileId.isEmpty ? null : fileId;
}
