// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'cached_list_snapshot.dart';

// **************************************************************************
// IsarCollectionGenerator
// **************************************************************************

// coverage:ignore-file
// ignore_for_file: duplicate_ignore, non_constant_identifier_names, constant_identifier_names, invalid_use_of_protected_member, unnecessary_cast, prefer_const_constructors, lines_longer_than_80_chars, require_trailing_commas, inference_failure_on_function_invocation, unnecessary_parenthesis, unnecessary_raw_strings, unnecessary_null_checks, join_return_with_assignment, prefer_final_locals, avoid_js_rounded_ints, avoid_positional_boolean_parameters, always_specify_types

extension GetCachedListSnapshotCollection on Isar {
  IsarCollection<CachedListSnapshot> get cachedListSnapshots =>
      this.collection();
}

const CachedListSnapshotSchema = CollectionSchema(
  name: r'cls_2528',
  id: -3993110354800439673,
  properties: {
    r'cacheKey': PropertySchema(
      id: 0,
      name: r'cacheKey',
      type: IsarType.string,
    ),
    r'fetchedAt': PropertySchema(
      id: 1,
      name: r'fetchedAt',
      type: IsarType.dateTime,
    ),
    r'jsonData': PropertySchema(
      id: 2,
      name: r'jsonData',
      type: IsarType.longList,
    ),
    r'version': PropertySchema(
      id: 3,
      name: r'version',
      type: IsarType.string,
    )
  },
  estimateSize: _cachedListSnapshotEstimateSize,
  serialize: _cachedListSnapshotSerialize,
  deserialize: _cachedListSnapshotDeserialize,
  deserializeProp: _cachedListSnapshotDeserializeProp,
  idName: r'id',
  indexes: {
    r'i_cls_key_2529': IndexSchema(
      id: -5780496603892815176,
      name: r'i_cls_key_2529',
      unique: true,
      replace: false,
      properties: [
        IndexPropertySchema(
          name: r'cacheKey',
          type: IndexType.hash,
          caseSensitive: true,
        )
      ],
    ),
    r'i_cls_ver_2530': IndexSchema(
      id: 1681328346514525477,
      name: r'i_cls_ver_2530',
      unique: false,
      replace: false,
      properties: [
        IndexPropertySchema(
          name: r'version',
          type: IndexType.hash,
          caseSensitive: true,
        )
      ],
    )
  },
  links: {},
  embeddedSchemas: {},
  getId: _cachedListSnapshotGetId,
  getLinks: _cachedListSnapshotGetLinks,
  attach: _cachedListSnapshotAttach,
  version: '3.1.0+1',
);

int _cachedListSnapshotEstimateSize(
  CachedListSnapshot object,
  List<int> offsets,
  Map<Type, List<int>> allOffsets,
) {
  var bytesCount = offsets.last;
  bytesCount += 3 + object.cacheKey.length * 3;
  bytesCount += 3 + object.jsonData.length * 8;
  bytesCount += 3 + object.version.length * 3;
  return bytesCount;
}

void _cachedListSnapshotSerialize(
  CachedListSnapshot object,
  IsarWriter writer,
  List<int> offsets,
  Map<Type, List<int>> allOffsets,
) {
  writer.writeString(offsets[0], object.cacheKey);
  writer.writeDateTime(offsets[1], object.fetchedAt);
  writer.writeLongList(offsets[2], object.jsonData);
  writer.writeString(offsets[3], object.version);
}

CachedListSnapshot _cachedListSnapshotDeserialize(
  Id id,
  IsarReader reader,
  List<int> offsets,
  Map<Type, List<int>> allOffsets,
) {
  final object = CachedListSnapshot();
  object.cacheKey = reader.readString(offsets[0]);
  object.fetchedAt = reader.readDateTime(offsets[1]);
  object.id = id;
  object.jsonData = reader.readLongList(offsets[2]) ?? [];
  object.version = reader.readString(offsets[3]);
  return object;
}

P _cachedListSnapshotDeserializeProp<P>(
  IsarReader reader,
  int propertyId,
  int offset,
  Map<Type, List<int>> allOffsets,
) {
  switch (propertyId) {
    case 0:
      return (reader.readString(offset)) as P;
    case 1:
      return (reader.readDateTime(offset)) as P;
    case 2:
      return (reader.readLongList(offset) ?? []) as P;
    case 3:
      return (reader.readString(offset)) as P;
    default:
      throw IsarError('Unknown property with id $propertyId');
  }
}

Id _cachedListSnapshotGetId(CachedListSnapshot object) {
  return object.id;
}

List<IsarLinkBase<dynamic>> _cachedListSnapshotGetLinks(
    CachedListSnapshot object) {
  return [];
}

void _cachedListSnapshotAttach(
    IsarCollection<dynamic> col, Id id, CachedListSnapshot object) {
  object.id = id;
}

extension CachedListSnapshotByIndex on IsarCollection<CachedListSnapshot> {
  Future<CachedListSnapshot?> getByCacheKey(String cacheKey) {
    return getByIndex(r'i_cls_key_2529', [cacheKey]);
  }

  CachedListSnapshot? getByCacheKeySync(String cacheKey) {
    return getByIndexSync(r'i_cls_key_2529', [cacheKey]);
  }

  Future<bool> deleteByCacheKey(String cacheKey) {
    return deleteByIndex(r'i_cls_key_2529', [cacheKey]);
  }

  bool deleteByCacheKeySync(String cacheKey) {
    return deleteByIndexSync(r'i_cls_key_2529', [cacheKey]);
  }

  Future<List<CachedListSnapshot?>> getAllByCacheKey(
      List<String> cacheKeyValues) {
    final values = cacheKeyValues.map((e) => [e]).toList();
    return getAllByIndex(r'i_cls_key_2529', values);
  }

  List<CachedListSnapshot?> getAllByCacheKeySync(List<String> cacheKeyValues) {
    final values = cacheKeyValues.map((e) => [e]).toList();
    return getAllByIndexSync(r'i_cls_key_2529', values);
  }

  Future<int> deleteAllByCacheKey(List<String> cacheKeyValues) {
    final values = cacheKeyValues.map((e) => [e]).toList();
    return deleteAllByIndex(r'i_cls_key_2529', values);
  }

  int deleteAllByCacheKeySync(List<String> cacheKeyValues) {
    final values = cacheKeyValues.map((e) => [e]).toList();
    return deleteAllByIndexSync(r'i_cls_key_2529', values);
  }

  Future<Id> putByCacheKey(CachedListSnapshot object) {
    return putByIndex(r'i_cls_key_2529', object);
  }

  Id putByCacheKeySync(CachedListSnapshot object, {bool saveLinks = true}) {
    return putByIndexSync(r'i_cls_key_2529', object, saveLinks: saveLinks);
  }

  Future<List<Id>> putAllByCacheKey(List<CachedListSnapshot> objects) {
    return putAllByIndex(r'i_cls_key_2529', objects);
  }

  List<Id> putAllByCacheKeySync(List<CachedListSnapshot> objects,
      {bool saveLinks = true}) {
    return putAllByIndexSync(r'i_cls_key_2529', objects, saveLinks: saveLinks);
  }
}

extension CachedListSnapshotQueryWhereSort
    on QueryBuilder<CachedListSnapshot, CachedListSnapshot, QWhere> {
  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterWhere> anyId() {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(const IdWhereClause.any());
    });
  }
}

extension CachedListSnapshotQueryWhere
    on QueryBuilder<CachedListSnapshot, CachedListSnapshot, QWhereClause> {
  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterWhereClause>
      idEqualTo(Id id) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IdWhereClause.between(
        lower: id,
        upper: id,
      ));
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterWhereClause>
      idNotEqualTo(Id id) {
    return QueryBuilder.apply(this, (query) {
      if (query.whereSort == Sort.asc) {
        return query
            .addWhereClause(
              IdWhereClause.lessThan(upper: id, includeUpper: false),
            )
            .addWhereClause(
              IdWhereClause.greaterThan(lower: id, includeLower: false),
            );
      } else {
        return query
            .addWhereClause(
              IdWhereClause.greaterThan(lower: id, includeLower: false),
            )
            .addWhereClause(
              IdWhereClause.lessThan(upper: id, includeUpper: false),
            );
      }
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterWhereClause>
      idGreaterThan(Id id, {bool include = false}) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(
        IdWhereClause.greaterThan(lower: id, includeLower: include),
      );
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterWhereClause>
      idLessThan(Id id, {bool include = false}) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(
        IdWhereClause.lessThan(upper: id, includeUpper: include),
      );
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterWhereClause>
      idBetween(
    Id lowerId,
    Id upperId, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IdWhereClause.between(
        lower: lowerId,
        includeLower: includeLower,
        upper: upperId,
        includeUpper: includeUpper,
      ));
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterWhereClause>
      cacheKeyEqualTo(String cacheKey) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IndexWhereClause.equalTo(
        indexName: r'i_cls_key_2529',
        value: [cacheKey],
      ));
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterWhereClause>
      cacheKeyNotEqualTo(String cacheKey) {
    return QueryBuilder.apply(this, (query) {
      if (query.whereSort == Sort.asc) {
        return query
            .addWhereClause(IndexWhereClause.between(
              indexName: r'i_cls_key_2529',
              lower: [],
              upper: [cacheKey],
              includeUpper: false,
            ))
            .addWhereClause(IndexWhereClause.between(
              indexName: r'i_cls_key_2529',
              lower: [cacheKey],
              includeLower: false,
              upper: [],
            ));
      } else {
        return query
            .addWhereClause(IndexWhereClause.between(
              indexName: r'i_cls_key_2529',
              lower: [cacheKey],
              includeLower: false,
              upper: [],
            ))
            .addWhereClause(IndexWhereClause.between(
              indexName: r'i_cls_key_2529',
              lower: [],
              upper: [cacheKey],
              includeUpper: false,
            ));
      }
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterWhereClause>
      versionEqualTo(String version) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IndexWhereClause.equalTo(
        indexName: r'i_cls_ver_2530',
        value: [version],
      ));
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterWhereClause>
      versionNotEqualTo(String version) {
    return QueryBuilder.apply(this, (query) {
      if (query.whereSort == Sort.asc) {
        return query
            .addWhereClause(IndexWhereClause.between(
              indexName: r'i_cls_ver_2530',
              lower: [],
              upper: [version],
              includeUpper: false,
            ))
            .addWhereClause(IndexWhereClause.between(
              indexName: r'i_cls_ver_2530',
              lower: [version],
              includeLower: false,
              upper: [],
            ));
      } else {
        return query
            .addWhereClause(IndexWhereClause.between(
              indexName: r'i_cls_ver_2530',
              lower: [version],
              includeLower: false,
              upper: [],
            ))
            .addWhereClause(IndexWhereClause.between(
              indexName: r'i_cls_ver_2530',
              lower: [],
              upper: [version],
              includeUpper: false,
            ));
      }
    });
  }
}

extension CachedListSnapshotQueryFilter
    on QueryBuilder<CachedListSnapshot, CachedListSnapshot, QFilterCondition> {
  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterFilterCondition>
      cacheKeyEqualTo(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'cacheKey',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterFilterCondition>
      cacheKeyGreaterThan(
    String value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'cacheKey',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterFilterCondition>
      cacheKeyLessThan(
    String value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'cacheKey',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterFilterCondition>
      cacheKeyBetween(
    String lower,
    String upper, {
    bool includeLower = true,
    bool includeUpper = true,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'cacheKey',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterFilterCondition>
      cacheKeyStartsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.startsWith(
        property: r'cacheKey',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterFilterCondition>
      cacheKeyEndsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.endsWith(
        property: r'cacheKey',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterFilterCondition>
      cacheKeyContains(String value, {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.contains(
        property: r'cacheKey',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterFilterCondition>
      cacheKeyMatches(String pattern, {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.matches(
        property: r'cacheKey',
        wildcard: pattern,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterFilterCondition>
      cacheKeyIsEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'cacheKey',
        value: '',
      ));
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterFilterCondition>
      cacheKeyIsNotEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        property: r'cacheKey',
        value: '',
      ));
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterFilterCondition>
      fetchedAtEqualTo(DateTime value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'fetchedAt',
        value: value,
      ));
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterFilterCondition>
      fetchedAtGreaterThan(
    DateTime value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'fetchedAt',
        value: value,
      ));
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterFilterCondition>
      fetchedAtLessThan(
    DateTime value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'fetchedAt',
        value: value,
      ));
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterFilterCondition>
      fetchedAtBetween(
    DateTime lower,
    DateTime upper, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'fetchedAt',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
      ));
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterFilterCondition>
      idEqualTo(Id value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'id',
        value: value,
      ));
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterFilterCondition>
      idGreaterThan(
    Id value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'id',
        value: value,
      ));
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterFilterCondition>
      idLessThan(
    Id value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'id',
        value: value,
      ));
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterFilterCondition>
      idBetween(
    Id lower,
    Id upper, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'id',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
      ));
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterFilterCondition>
      jsonDataElementEqualTo(int value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'jsonData',
        value: value,
      ));
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterFilterCondition>
      jsonDataElementGreaterThan(
    int value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'jsonData',
        value: value,
      ));
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterFilterCondition>
      jsonDataElementLessThan(
    int value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'jsonData',
        value: value,
      ));
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterFilterCondition>
      jsonDataElementBetween(
    int lower,
    int upper, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'jsonData',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
      ));
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterFilterCondition>
      jsonDataLengthEqualTo(int length) {
    return QueryBuilder.apply(this, (query) {
      return query.listLength(
        r'jsonData',
        length,
        true,
        length,
        true,
      );
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterFilterCondition>
      jsonDataIsEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.listLength(
        r'jsonData',
        0,
        true,
        0,
        true,
      );
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterFilterCondition>
      jsonDataIsNotEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.listLength(
        r'jsonData',
        0,
        false,
        999999,
        true,
      );
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterFilterCondition>
      jsonDataLengthLessThan(
    int length, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.listLength(
        r'jsonData',
        0,
        true,
        length,
        include,
      );
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterFilterCondition>
      jsonDataLengthGreaterThan(
    int length, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.listLength(
        r'jsonData',
        length,
        include,
        999999,
        true,
      );
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterFilterCondition>
      jsonDataLengthBetween(
    int lower,
    int upper, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.listLength(
        r'jsonData',
        lower,
        includeLower,
        upper,
        includeUpper,
      );
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterFilterCondition>
      versionEqualTo(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'version',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterFilterCondition>
      versionGreaterThan(
    String value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'version',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterFilterCondition>
      versionLessThan(
    String value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'version',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterFilterCondition>
      versionBetween(
    String lower,
    String upper, {
    bool includeLower = true,
    bool includeUpper = true,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'version',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterFilterCondition>
      versionStartsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.startsWith(
        property: r'version',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterFilterCondition>
      versionEndsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.endsWith(
        property: r'version',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterFilterCondition>
      versionContains(String value, {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.contains(
        property: r'version',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterFilterCondition>
      versionMatches(String pattern, {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.matches(
        property: r'version',
        wildcard: pattern,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterFilterCondition>
      versionIsEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'version',
        value: '',
      ));
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterFilterCondition>
      versionIsNotEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        property: r'version',
        value: '',
      ));
    });
  }
}

extension CachedListSnapshotQueryObject
    on QueryBuilder<CachedListSnapshot, CachedListSnapshot, QFilterCondition> {}

extension CachedListSnapshotQueryLinks
    on QueryBuilder<CachedListSnapshot, CachedListSnapshot, QFilterCondition> {}

extension CachedListSnapshotQuerySortBy
    on QueryBuilder<CachedListSnapshot, CachedListSnapshot, QSortBy> {
  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterSortBy>
      sortByCacheKey() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'cacheKey', Sort.asc);
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterSortBy>
      sortByCacheKeyDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'cacheKey', Sort.desc);
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterSortBy>
      sortByFetchedAt() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'fetchedAt', Sort.asc);
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterSortBy>
      sortByFetchedAtDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'fetchedAt', Sort.desc);
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterSortBy>
      sortByVersion() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'version', Sort.asc);
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterSortBy>
      sortByVersionDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'version', Sort.desc);
    });
  }
}

extension CachedListSnapshotQuerySortThenBy
    on QueryBuilder<CachedListSnapshot, CachedListSnapshot, QSortThenBy> {
  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterSortBy>
      thenByCacheKey() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'cacheKey', Sort.asc);
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterSortBy>
      thenByCacheKeyDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'cacheKey', Sort.desc);
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterSortBy>
      thenByFetchedAt() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'fetchedAt', Sort.asc);
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterSortBy>
      thenByFetchedAtDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'fetchedAt', Sort.desc);
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterSortBy>
      thenById() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'id', Sort.asc);
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterSortBy>
      thenByIdDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'id', Sort.desc);
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterSortBy>
      thenByVersion() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'version', Sort.asc);
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QAfterSortBy>
      thenByVersionDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'version', Sort.desc);
    });
  }
}

extension CachedListSnapshotQueryWhereDistinct
    on QueryBuilder<CachedListSnapshot, CachedListSnapshot, QDistinct> {
  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QDistinct>
      distinctByCacheKey({bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'cacheKey', caseSensitive: caseSensitive);
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QDistinct>
      distinctByFetchedAt() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'fetchedAt');
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QDistinct>
      distinctByJsonData() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'jsonData');
    });
  }

  QueryBuilder<CachedListSnapshot, CachedListSnapshot, QDistinct>
      distinctByVersion({bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'version', caseSensitive: caseSensitive);
    });
  }
}

extension CachedListSnapshotQueryProperty
    on QueryBuilder<CachedListSnapshot, CachedListSnapshot, QQueryProperty> {
  QueryBuilder<CachedListSnapshot, int, QQueryOperations> idProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'id');
    });
  }

  QueryBuilder<CachedListSnapshot, String, QQueryOperations>
      cacheKeyProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'cacheKey');
    });
  }

  QueryBuilder<CachedListSnapshot, DateTime, QQueryOperations>
      fetchedAtProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'fetchedAt');
    });
  }

  QueryBuilder<CachedListSnapshot, List<int>, QQueryOperations>
      jsonDataProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'jsonData');
    });
  }

  QueryBuilder<CachedListSnapshot, String, QQueryOperations> versionProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'version');
    });
  }
}
