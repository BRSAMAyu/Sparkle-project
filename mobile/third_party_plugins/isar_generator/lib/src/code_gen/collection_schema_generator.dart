import 'package:dartx/dartx.dart';
import 'package:isar/isar.dart';
import 'package:isar_generator/src/isar_type.dart';

import 'package:isar_generator/src/object_info.dart';

/// Largest integer exactly representable as a JavaScript double (2^53).
///
/// dart2js/CEF rejects int literals outside this domain
/// ("The integer literal ... can't be represented exactly in JavaScript."),
/// which broke Flutter Web builds for collections whose Isar schema id
/// (64-bit xxh3 of the schema name) exceeds it.
const _maxJsSafeInt = 9007199254740992;

/// Sparkle local patch (FIX-558, based on upstream isar_generator 3.1.0+1):
/// emit schema/index/link ids that don't fit the JS double domain as a
/// runtime `int.parse` of the decimal string instead of an int literal.
/// The Dart VM keeps the exact 64-bit value; on web it deterministically
/// rounds to the nearest double, which is fine because Isar schema ids
/// only need platform-local stability (they are never compared across
/// platforms). Ids inside the JS-safe domain are emitted unchanged so
/// existing generated files don't drift.
String _schemaIdLiteral(int id) =>
    id.abs() > _maxJsSafeInt ? "int.parse(r'$id')" : '$id';

/// Whether any id of this schema needs JS-safe stringification; if so the
/// schema constant can't be `const` (int.parse is not a const expression).
bool _needsJsSafeId(ObjectInfo object) =>
    object.id.abs() > _maxJsSafeInt ||
    object.indexes.any((e) => e.id.abs() > _maxJsSafeInt) ||
    object.links.any((e) => e.id(object.isarName).abs() > _maxJsSafeInt);

String generateSchema(ObjectInfo object) {
  final jsSafeId = _needsJsSafeId(object);
  var code = '${jsSafeId ? 'final' : 'const'} '
      '${object.dartName.capitalize()}Schema = ';
  if (!object.isEmbedded) {
    code += 'CollectionSchema(';
  } else {
    code += 'Schema(';
  }

  final properties = object.objectProperties
      .mapIndexed(
        (i, e) => "r'${e.isarName}': ${_generatePropertySchema(object, i)}",
      )
      .join(',');

  code += '''
    name: r'${object.isarName}',
    id: ${_schemaIdLiteral(object.id)},
    properties: {$properties},

    estimateSize: ${object.estimateSizeName},
    serialize: ${object.serializeName},
    deserialize: ${object.deserializeName},
    deserializeProp: ${object.deserializePropName},''';

  if (!object.isEmbedded) {
    final indexes = object.indexes
        .map((e) => "r'${e.name}': ${_generateIndexSchema(e)}")
        .join(',');
    final links = object.links
        .map((e) => "r'${e.isarName}': ${_generateLinkSchema(object, e)}")
        .join(',');
    final embeddedSchemas = object.embeddedDartNames.entries
        .map((e) => "r'${e.key}': ${e.value.capitalize()}Schema")
        .join(',');

    code += '''
      idName: r'${object.idProperty.isarName}',
      indexes: {$indexes},
      links: {$links},
      embeddedSchemas: {$embeddedSchemas},

      getId: ${object.getIdName},
      getLinks: ${object.getLinksName},
      attach: ${object.attachName},
      version: '${Isar.version}',
    ''';
  }

  return '$code);';
}

String _generatePropertySchema(ObjectInfo object, int index) {
  final property = object.objectProperties[index];
  var enumMap = '';
  if (property.isEnum) {
    enumMap = 'enumMap: ${property.enumValueMapName(object)},';
  }
  var target = '';
  if (property.targetIsarName != null) {
    target = "target: r'${property.targetIsarName}',";
  }
  return '''
  PropertySchema(
    id: $index,
    name: r'${property.isarName}',
    type: IsarType.${property.isarType.name},
    $enumMap
    $target
  )
  ''';
}

String _generateIndexSchema(ObjectIndex index) {
  final properties = index.properties.map((e) {
    return '''
      IndexPropertySchema(
        name: r'${e.property.isarName}',
        type: IndexType.${e.type.name},
        caseSensitive: ${e.caseSensitive},
      )''';
  }).join(',');

  return '''
    IndexSchema(
      id: ${_schemaIdLiteral(index.id)},
      name: r'${index.name}',
      unique: ${index.unique},
      replace: ${index.replace},
      properties: [$properties],
    )''';
}

String _generateLinkSchema(ObjectInfo object, ObjectLink link) {
  var linkName = '';
  if (link.isBacklink) {
    linkName = "linkName: r'${link.targetLinkIsarName}',";
  }
  return '''
    LinkSchema(
      id: ${_schemaIdLiteral(link.id(object.isarName))},
      name: r'${link.isarName}',
      target: r'${link.targetCollectionIsarName}',
      single: ${link.isSingle},
      $linkName
    )''';
}
