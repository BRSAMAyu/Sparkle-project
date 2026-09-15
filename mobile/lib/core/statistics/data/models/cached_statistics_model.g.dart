// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'cached_statistics_model.dart';

// **************************************************************************
// IsarCollectionGenerator
// **************************************************************************

// coverage:ignore-file
// ignore_for_file: duplicate_ignore, non_constant_identifier_names, constant_identifier_names, invalid_use_of_protected_member, unnecessary_cast, prefer_const_constructors, lines_longer_than_80_chars, require_trailing_commas, inference_failure_on_function_invocation, unnecessary_parenthesis, unnecessary_raw_strings, unnecessary_null_checks, join_return_with_assignment, prefer_final_locals, avoid_js_rounded_ints, avoid_positional_boolean_parameters, always_specify_types

extension GetCachedStatisticsModelCollection on Isar {
  IsarCollection<CachedStatisticsModel> get cachedStatisticsModels =>
      this.collection();
}

const CachedStatisticsModelSchema = CollectionSchema(
  name: r'CachedStatisticsModel',
  id: 1385342800440360539,
  properties: {
    r'ageSeconds': PropertySchema(
      id: 0,
      name: r'ageSeconds',
      type: IsarType.long,
    ),
    r'cacheKey': PropertySchema(
      id: 1,
      name: r'cacheKey',
      type: IsarType.string,
    ),
    r'createdAt': PropertySchema(
      id: 2,
      name: r'createdAt',
      type: IsarType.dateTime,
    ),
    r'dataSize': PropertySchema(
      id: 3,
      name: r'dataSize',
      type: IsarType.long,
    ),
    r'isFullySynced': PropertySchema(
      id: 4,
      name: r'isFullySynced',
      type: IsarType.bool,
    ),
    r'jsonData': PropertySchema(
      id: 5,
      name: r'jsonData',
      type: IsarType.longList,
    ),
    r'lastAccessedAt': PropertySchema(
      id: 6,
      name: r'lastAccessedAt',
      type: IsarType.dateTime,
    ),
    r'metadata': PropertySchema(
      id: 7,
      name: r'metadata',
      type: IsarType.string,
    ),
    r'period': PropertySchema(
      id: 8,
      name: r'period',
      type: IsarType.string,
      enumMap: _CachedStatisticsModelperiodEnumValueMap,
    ),
    r'periodEnd': PropertySchema(
      id: 9,
      name: r'periodEnd',
      type: IsarType.dateTime,
    ),
    r'periodStart': PropertySchema(
      id: 10,
      name: r'periodStart',
      type: IsarType.dateTime,
    ),
    r'priority': PropertySchema(
      id: 11,
      name: r'priority',
      type: IsarType.long,
    ),
    r'ttlSeconds': PropertySchema(
      id: 12,
      name: r'ttlSeconds',
      type: IsarType.long,
    ),
    r'type': PropertySchema(
      id: 13,
      name: r'type',
      type: IsarType.string,
      enumMap: _CachedStatisticsModeltypeEnumValueMap,
    )
  },
  estimateSize: _cachedStatisticsModelEstimateSize,
  serialize: _cachedStatisticsModelSerialize,
  deserialize: _cachedStatisticsModelDeserialize,
  deserializeProp: _cachedStatisticsModelDeserializeProp,
  idName: r'id',
  indexes: {
    r'cacheKey': IndexSchema(
      id: 5885332021012296610,
      name: r'cacheKey',
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
    r'createdAt': IndexSchema(
      id: -3433535483987302584,
      name: r'createdAt',
      unique: false,
      replace: false,
      properties: [
        IndexPropertySchema(
          name: r'createdAt',
          type: IndexType.value,
          caseSensitive: false,
        )
      ],
    ),
    r'lastAccessedAt': IndexSchema(
      id: 7637973981624628205,
      name: r'lastAccessedAt',
      unique: false,
      replace: false,
      properties: [
        IndexPropertySchema(
          name: r'lastAccessedAt',
          type: IndexType.value,
          caseSensitive: false,
        )
      ],
    )
  },
  links: {},
  embeddedSchemas: {},
  getId: _cachedStatisticsModelGetId,
  getLinks: _cachedStatisticsModelGetLinks,
  attach: _cachedStatisticsModelAttach,
  version: '3.1.0+1',
);

int _cachedStatisticsModelEstimateSize(
  CachedStatisticsModel object,
  List<int> offsets,
  Map<Type, List<int>> allOffsets,
) {
  var bytesCount = offsets.last;
  bytesCount += 3 + object.cacheKey.length * 3;
  bytesCount += 3 + object.jsonData.length * 8;
  {
    final value = object.metadata;
    if (value != null) {
      bytesCount += 3 + value.length * 3;
    }
  }
  bytesCount += 3 + object.period.name.length * 3;
  bytesCount += 3 + object.type.name.length * 3;
  return bytesCount;
}

void _cachedStatisticsModelSerialize(
  CachedStatisticsModel object,
  IsarWriter writer,
  List<int> offsets,
  Map<Type, List<int>> allOffsets,
) {
  writer.writeLong(offsets[0], object.ageSeconds);
  writer.writeString(offsets[1], object.cacheKey);
  writer.writeDateTime(offsets[2], object.createdAt);
  writer.writeLong(offsets[3], object.dataSize);
  writer.writeBool(offsets[4], object.isFullySynced);
  writer.writeLongList(offsets[5], object.jsonData);
  writer.writeDateTime(offsets[6], object.lastAccessedAt);
  writer.writeString(offsets[7], object.metadata);
  writer.writeString(offsets[8], object.period.name);
  writer.writeDateTime(offsets[9], object.periodEnd);
  writer.writeDateTime(offsets[10], object.periodStart);
  writer.writeLong(offsets[11], object.priority);
  writer.writeLong(offsets[12], object.ttlSeconds);
  writer.writeString(offsets[13], object.type.name);
}

CachedStatisticsModel _cachedStatisticsModelDeserialize(
  Id id,
  IsarReader reader,
  List<int> offsets,
  Map<Type, List<int>> allOffsets,
) {
  final object = CachedStatisticsModel();
  object.cacheKey = reader.readString(offsets[1]);
  object.createdAt = reader.readDateTime(offsets[2]);
  object.id = id;
  object.isFullySynced = reader.readBool(offsets[4]);
  object.jsonData = reader.readLongList(offsets[5]) ?? [];
  object.lastAccessedAt = reader.readDateTime(offsets[6]);
  object.metadata = reader.readStringOrNull(offsets[7]);
  object.period = _CachedStatisticsModelperiodValueEnumMap[
          reader.readStringOrNull(offsets[8])] ??
      StatisticsPeriod.today;
  object.periodEnd = reader.readDateTime(offsets[9]);
  object.periodStart = reader.readDateTime(offsets[10]);
  object.priority = reader.readLong(offsets[11]);
  object.ttlSeconds = reader.readLongOrNull(offsets[12]);
  object.type = _CachedStatisticsModeltypeValueEnumMap[
          reader.readStringOrNull(offsets[13])] ??
      StatisticsType.focus;
  return object;
}

P _cachedStatisticsModelDeserializeProp<P>(
  IsarReader reader,
  int propertyId,
  int offset,
  Map<Type, List<int>> allOffsets,
) {
  switch (propertyId) {
    case 0:
      return (reader.readLong(offset)) as P;
    case 1:
      return (reader.readString(offset)) as P;
    case 2:
      return (reader.readDateTime(offset)) as P;
    case 3:
      return (reader.readLong(offset)) as P;
    case 4:
      return (reader.readBool(offset)) as P;
    case 5:
      return (reader.readLongList(offset) ?? []) as P;
    case 6:
      return (reader.readDateTime(offset)) as P;
    case 7:
      return (reader.readStringOrNull(offset)) as P;
    case 8:
      return (_CachedStatisticsModelperiodValueEnumMap[
              reader.readStringOrNull(offset)] ??
          StatisticsPeriod.today) as P;
    case 9:
      return (reader.readDateTime(offset)) as P;
    case 10:
      return (reader.readDateTime(offset)) as P;
    case 11:
      return (reader.readLong(offset)) as P;
    case 12:
      return (reader.readLongOrNull(offset)) as P;
    case 13:
      return (_CachedStatisticsModeltypeValueEnumMap[
              reader.readStringOrNull(offset)] ??
          StatisticsType.focus) as P;
    default:
      throw IsarError('Unknown property with id $propertyId');
  }
}

const _CachedStatisticsModelperiodEnumValueMap = {
  r'today': r'today',
  r'week': r'week',
  r'month': r'month',
  r'year': r'year',
  r'custom': r'custom',
};
const _CachedStatisticsModelperiodValueEnumMap = {
  r'today': StatisticsPeriod.today,
  r'week': StatisticsPeriod.week,
  r'month': StatisticsPeriod.month,
  r'year': StatisticsPeriod.year,
  r'custom': StatisticsPeriod.custom,
};
const _CachedStatisticsModeltypeEnumValueMap = {
  r'focus': r'focus',
  r'agent': r'agent',
  r'capsule': r'capsule',
  r'learning': r'learning',
};
const _CachedStatisticsModeltypeValueEnumMap = {
  r'focus': StatisticsType.focus,
  r'agent': StatisticsType.agent,
  r'capsule': StatisticsType.capsule,
  r'learning': StatisticsType.learning,
};

Id _cachedStatisticsModelGetId(CachedStatisticsModel object) {
  return object.id;
}

List<IsarLinkBase<dynamic>> _cachedStatisticsModelGetLinks(
    CachedStatisticsModel object) {
  return [];
}

void _cachedStatisticsModelAttach(
    IsarCollection<dynamic> col, Id id, CachedStatisticsModel object) {
  object.id = id;
}

extension CachedStatisticsModelByIndex
    on IsarCollection<CachedStatisticsModel> {
  Future<CachedStatisticsModel?> getByCacheKey(String cacheKey) {
    return getByIndex(r'cacheKey', [cacheKey]);
  }

  CachedStatisticsModel? getByCacheKeySync(String cacheKey) {
    return getByIndexSync(r'cacheKey', [cacheKey]);
  }

  Future<bool> deleteByCacheKey(String cacheKey) {
    return deleteByIndex(r'cacheKey', [cacheKey]);
  }

  bool deleteByCacheKeySync(String cacheKey) {
    return deleteByIndexSync(r'cacheKey', [cacheKey]);
  }

  Future<List<CachedStatisticsModel?>> getAllByCacheKey(
      List<String> cacheKeyValues) {
    final values = cacheKeyValues.map((e) => [e]).toList();
    return getAllByIndex(r'cacheKey', values);
  }

  List<CachedStatisticsModel?> getAllByCacheKeySync(
      List<String> cacheKeyValues) {
    final values = cacheKeyValues.map((e) => [e]).toList();
    return getAllByIndexSync(r'cacheKey', values);
  }

  Future<int> deleteAllByCacheKey(List<String> cacheKeyValues) {
    final values = cacheKeyValues.map((e) => [e]).toList();
    return deleteAllByIndex(r'cacheKey', values);
  }

  int deleteAllByCacheKeySync(List<String> cacheKeyValues) {
    final values = cacheKeyValues.map((e) => [e]).toList();
    return deleteAllByIndexSync(r'cacheKey', values);
  }

  Future<Id> putByCacheKey(CachedStatisticsModel object) {
    return putByIndex(r'cacheKey', object);
  }

  Id putByCacheKeySync(CachedStatisticsModel object, {bool saveLinks = true}) {
    return putByIndexSync(r'cacheKey', object, saveLinks: saveLinks);
  }

  Future<List<Id>> putAllByCacheKey(List<CachedStatisticsModel> objects) {
    return putAllByIndex(r'cacheKey', objects);
  }

  List<Id> putAllByCacheKeySync(List<CachedStatisticsModel> objects,
      {bool saveLinks = true}) {
    return putAllByIndexSync(r'cacheKey', objects, saveLinks: saveLinks);
  }
}

extension CachedStatisticsModelQueryWhereSort
    on QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QWhere> {
  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterWhere>
      anyId() {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(const IdWhereClause.any());
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterWhere>
      anyCreatedAt() {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(
        const IndexWhereClause.any(indexName: r'createdAt'),
      );
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterWhere>
      anyLastAccessedAt() {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(
        const IndexWhereClause.any(indexName: r'lastAccessedAt'),
      );
    });
  }
}

extension CachedStatisticsModelQueryWhere on QueryBuilder<CachedStatisticsModel,
    CachedStatisticsModel, QWhereClause> {
  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterWhereClause>
      idEqualTo(Id id) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IdWhereClause.between(
        lower: id,
        upper: id,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterWhereClause>
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

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterWhereClause>
      idGreaterThan(Id id, {bool include = false}) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(
        IdWhereClause.greaterThan(lower: id, includeLower: include),
      );
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterWhereClause>
      idLessThan(Id id, {bool include = false}) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(
        IdWhereClause.lessThan(upper: id, includeUpper: include),
      );
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterWhereClause>
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

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterWhereClause>
      cacheKeyEqualTo(String cacheKey) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IndexWhereClause.equalTo(
        indexName: r'cacheKey',
        value: [cacheKey],
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterWhereClause>
      cacheKeyNotEqualTo(String cacheKey) {
    return QueryBuilder.apply(this, (query) {
      if (query.whereSort == Sort.asc) {
        return query
            .addWhereClause(IndexWhereClause.between(
              indexName: r'cacheKey',
              lower: [],
              upper: [cacheKey],
              includeUpper: false,
            ))
            .addWhereClause(IndexWhereClause.between(
              indexName: r'cacheKey',
              lower: [cacheKey],
              includeLower: false,
              upper: [],
            ));
      } else {
        return query
            .addWhereClause(IndexWhereClause.between(
              indexName: r'cacheKey',
              lower: [cacheKey],
              includeLower: false,
              upper: [],
            ))
            .addWhereClause(IndexWhereClause.between(
              indexName: r'cacheKey',
              lower: [],
              upper: [cacheKey],
              includeUpper: false,
            ));
      }
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterWhereClause>
      createdAtEqualTo(DateTime createdAt) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IndexWhereClause.equalTo(
        indexName: r'createdAt',
        value: [createdAt],
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterWhereClause>
      createdAtNotEqualTo(DateTime createdAt) {
    return QueryBuilder.apply(this, (query) {
      if (query.whereSort == Sort.asc) {
        return query
            .addWhereClause(IndexWhereClause.between(
              indexName: r'createdAt',
              lower: [],
              upper: [createdAt],
              includeUpper: false,
            ))
            .addWhereClause(IndexWhereClause.between(
              indexName: r'createdAt',
              lower: [createdAt],
              includeLower: false,
              upper: [],
            ));
      } else {
        return query
            .addWhereClause(IndexWhereClause.between(
              indexName: r'createdAt',
              lower: [createdAt],
              includeLower: false,
              upper: [],
            ))
            .addWhereClause(IndexWhereClause.between(
              indexName: r'createdAt',
              lower: [],
              upper: [createdAt],
              includeUpper: false,
            ));
      }
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterWhereClause>
      createdAtGreaterThan(
    DateTime createdAt, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IndexWhereClause.between(
        indexName: r'createdAt',
        lower: [createdAt],
        includeLower: include,
        upper: [],
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterWhereClause>
      createdAtLessThan(
    DateTime createdAt, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IndexWhereClause.between(
        indexName: r'createdAt',
        lower: [],
        upper: [createdAt],
        includeUpper: include,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterWhereClause>
      createdAtBetween(
    DateTime lowerCreatedAt,
    DateTime upperCreatedAt, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IndexWhereClause.between(
        indexName: r'createdAt',
        lower: [lowerCreatedAt],
        includeLower: includeLower,
        upper: [upperCreatedAt],
        includeUpper: includeUpper,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterWhereClause>
      lastAccessedAtEqualTo(DateTime lastAccessedAt) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IndexWhereClause.equalTo(
        indexName: r'lastAccessedAt',
        value: [lastAccessedAt],
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterWhereClause>
      lastAccessedAtNotEqualTo(DateTime lastAccessedAt) {
    return QueryBuilder.apply(this, (query) {
      if (query.whereSort == Sort.asc) {
        return query
            .addWhereClause(IndexWhereClause.between(
              indexName: r'lastAccessedAt',
              lower: [],
              upper: [lastAccessedAt],
              includeUpper: false,
            ))
            .addWhereClause(IndexWhereClause.between(
              indexName: r'lastAccessedAt',
              lower: [lastAccessedAt],
              includeLower: false,
              upper: [],
            ));
      } else {
        return query
            .addWhereClause(IndexWhereClause.between(
              indexName: r'lastAccessedAt',
              lower: [lastAccessedAt],
              includeLower: false,
              upper: [],
            ))
            .addWhereClause(IndexWhereClause.between(
              indexName: r'lastAccessedAt',
              lower: [],
              upper: [lastAccessedAt],
              includeUpper: false,
            ));
      }
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterWhereClause>
      lastAccessedAtGreaterThan(
    DateTime lastAccessedAt, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IndexWhereClause.between(
        indexName: r'lastAccessedAt',
        lower: [lastAccessedAt],
        includeLower: include,
        upper: [],
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterWhereClause>
      lastAccessedAtLessThan(
    DateTime lastAccessedAt, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IndexWhereClause.between(
        indexName: r'lastAccessedAt',
        lower: [],
        upper: [lastAccessedAt],
        includeUpper: include,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterWhereClause>
      lastAccessedAtBetween(
    DateTime lowerLastAccessedAt,
    DateTime upperLastAccessedAt, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IndexWhereClause.between(
        indexName: r'lastAccessedAt',
        lower: [lowerLastAccessedAt],
        includeLower: includeLower,
        upper: [upperLastAccessedAt],
        includeUpper: includeUpper,
      ));
    });
  }
}

extension CachedStatisticsModelQueryFilter on QueryBuilder<
    CachedStatisticsModel, CachedStatisticsModel, QFilterCondition> {
  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> ageSecondsEqualTo(int value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'ageSeconds',
        value: value,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> ageSecondsGreaterThan(
    int value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'ageSeconds',
        value: value,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> ageSecondsLessThan(
    int value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'ageSeconds',
        value: value,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> ageSecondsBetween(
    int lower,
    int upper, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'ageSeconds',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> cacheKeyEqualTo(
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

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> cacheKeyGreaterThan(
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

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> cacheKeyLessThan(
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

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> cacheKeyBetween(
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

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> cacheKeyStartsWith(
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

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> cacheKeyEndsWith(
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

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
          QAfterFilterCondition>
      cacheKeyContains(String value, {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.contains(
        property: r'cacheKey',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
          QAfterFilterCondition>
      cacheKeyMatches(String pattern, {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.matches(
        property: r'cacheKey',
        wildcard: pattern,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> cacheKeyIsEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'cacheKey',
        value: '',
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> cacheKeyIsNotEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        property: r'cacheKey',
        value: '',
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> createdAtEqualTo(DateTime value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'createdAt',
        value: value,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> createdAtGreaterThan(
    DateTime value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'createdAt',
        value: value,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> createdAtLessThan(
    DateTime value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'createdAt',
        value: value,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> createdAtBetween(
    DateTime lower,
    DateTime upper, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'createdAt',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> dataSizeEqualTo(int value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'dataSize',
        value: value,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> dataSizeGreaterThan(
    int value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'dataSize',
        value: value,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> dataSizeLessThan(
    int value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'dataSize',
        value: value,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> dataSizeBetween(
    int lower,
    int upper, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'dataSize',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> idEqualTo(Id value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'id',
        value: value,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> idGreaterThan(
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

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> idLessThan(
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

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> idBetween(
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

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> isFullySyncedEqualTo(bool value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'isFullySynced',
        value: value,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> jsonDataElementEqualTo(int value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'jsonData',
        value: value,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> jsonDataElementGreaterThan(
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

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> jsonDataElementLessThan(
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

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> jsonDataElementBetween(
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

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> jsonDataLengthEqualTo(int length) {
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

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> jsonDataIsEmpty() {
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

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> jsonDataIsNotEmpty() {
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

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> jsonDataLengthLessThan(
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

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> jsonDataLengthGreaterThan(
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

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> jsonDataLengthBetween(
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

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> lastAccessedAtEqualTo(DateTime value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'lastAccessedAt',
        value: value,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> lastAccessedAtGreaterThan(
    DateTime value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'lastAccessedAt',
        value: value,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> lastAccessedAtLessThan(
    DateTime value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'lastAccessedAt',
        value: value,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> lastAccessedAtBetween(
    DateTime lower,
    DateTime upper, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'lastAccessedAt',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> metadataIsNull() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(const FilterCondition.isNull(
        property: r'metadata',
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> metadataIsNotNull() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(const FilterCondition.isNotNull(
        property: r'metadata',
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> metadataEqualTo(
    String? value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'metadata',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> metadataGreaterThan(
    String? value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'metadata',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> metadataLessThan(
    String? value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'metadata',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> metadataBetween(
    String? lower,
    String? upper, {
    bool includeLower = true,
    bool includeUpper = true,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'metadata',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> metadataStartsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.startsWith(
        property: r'metadata',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> metadataEndsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.endsWith(
        property: r'metadata',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
          QAfterFilterCondition>
      metadataContains(String value, {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.contains(
        property: r'metadata',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
          QAfterFilterCondition>
      metadataMatches(String pattern, {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.matches(
        property: r'metadata',
        wildcard: pattern,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> metadataIsEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'metadata',
        value: '',
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> metadataIsNotEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        property: r'metadata',
        value: '',
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> periodEqualTo(
    StatisticsPeriod value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'period',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> periodGreaterThan(
    StatisticsPeriod value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'period',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> periodLessThan(
    StatisticsPeriod value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'period',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> periodBetween(
    StatisticsPeriod lower,
    StatisticsPeriod upper, {
    bool includeLower = true,
    bool includeUpper = true,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'period',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> periodStartsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.startsWith(
        property: r'period',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> periodEndsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.endsWith(
        property: r'period',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
          QAfterFilterCondition>
      periodContains(String value, {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.contains(
        property: r'period',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
          QAfterFilterCondition>
      periodMatches(String pattern, {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.matches(
        property: r'period',
        wildcard: pattern,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> periodIsEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'period',
        value: '',
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> periodIsNotEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        property: r'period',
        value: '',
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> periodEndEqualTo(DateTime value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'periodEnd',
        value: value,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> periodEndGreaterThan(
    DateTime value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'periodEnd',
        value: value,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> periodEndLessThan(
    DateTime value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'periodEnd',
        value: value,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> periodEndBetween(
    DateTime lower,
    DateTime upper, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'periodEnd',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> periodStartEqualTo(DateTime value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'periodStart',
        value: value,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> periodStartGreaterThan(
    DateTime value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'periodStart',
        value: value,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> periodStartLessThan(
    DateTime value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'periodStart',
        value: value,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> periodStartBetween(
    DateTime lower,
    DateTime upper, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'periodStart',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> priorityEqualTo(int value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'priority',
        value: value,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> priorityGreaterThan(
    int value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'priority',
        value: value,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> priorityLessThan(
    int value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'priority',
        value: value,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> priorityBetween(
    int lower,
    int upper, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'priority',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> ttlSecondsIsNull() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(const FilterCondition.isNull(
        property: r'ttlSeconds',
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> ttlSecondsIsNotNull() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(const FilterCondition.isNotNull(
        property: r'ttlSeconds',
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> ttlSecondsEqualTo(int? value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'ttlSeconds',
        value: value,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> ttlSecondsGreaterThan(
    int? value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'ttlSeconds',
        value: value,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> ttlSecondsLessThan(
    int? value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'ttlSeconds',
        value: value,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> ttlSecondsBetween(
    int? lower,
    int? upper, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'ttlSeconds',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> typeEqualTo(
    StatisticsType value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'type',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> typeGreaterThan(
    StatisticsType value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'type',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> typeLessThan(
    StatisticsType value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'type',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> typeBetween(
    StatisticsType lower,
    StatisticsType upper, {
    bool includeLower = true,
    bool includeUpper = true,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'type',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> typeStartsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.startsWith(
        property: r'type',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> typeEndsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.endsWith(
        property: r'type',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
          QAfterFilterCondition>
      typeContains(String value, {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.contains(
        property: r'type',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
          QAfterFilterCondition>
      typeMatches(String pattern, {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.matches(
        property: r'type',
        wildcard: pattern,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> typeIsEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'type',
        value: '',
      ));
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel,
      QAfterFilterCondition> typeIsNotEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        property: r'type',
        value: '',
      ));
    });
  }
}

extension CachedStatisticsModelQueryObject on QueryBuilder<
    CachedStatisticsModel, CachedStatisticsModel, QFilterCondition> {}

extension CachedStatisticsModelQueryLinks on QueryBuilder<CachedStatisticsModel,
    CachedStatisticsModel, QFilterCondition> {}

extension CachedStatisticsModelQuerySortBy
    on QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QSortBy> {
  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      sortByAgeSeconds() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'ageSeconds', Sort.asc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      sortByAgeSecondsDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'ageSeconds', Sort.desc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      sortByCacheKey() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'cacheKey', Sort.asc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      sortByCacheKeyDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'cacheKey', Sort.desc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      sortByCreatedAt() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'createdAt', Sort.asc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      sortByCreatedAtDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'createdAt', Sort.desc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      sortByDataSize() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'dataSize', Sort.asc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      sortByDataSizeDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'dataSize', Sort.desc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      sortByIsFullySynced() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'isFullySynced', Sort.asc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      sortByIsFullySyncedDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'isFullySynced', Sort.desc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      sortByLastAccessedAt() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'lastAccessedAt', Sort.asc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      sortByLastAccessedAtDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'lastAccessedAt', Sort.desc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      sortByMetadata() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'metadata', Sort.asc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      sortByMetadataDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'metadata', Sort.desc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      sortByPeriod() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'period', Sort.asc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      sortByPeriodDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'period', Sort.desc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      sortByPeriodEnd() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'periodEnd', Sort.asc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      sortByPeriodEndDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'periodEnd', Sort.desc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      sortByPeriodStart() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'periodStart', Sort.asc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      sortByPeriodStartDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'periodStart', Sort.desc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      sortByPriority() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'priority', Sort.asc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      sortByPriorityDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'priority', Sort.desc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      sortByTtlSeconds() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'ttlSeconds', Sort.asc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      sortByTtlSecondsDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'ttlSeconds', Sort.desc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      sortByType() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'type', Sort.asc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      sortByTypeDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'type', Sort.desc);
    });
  }
}

extension CachedStatisticsModelQuerySortThenBy
    on QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QSortThenBy> {
  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      thenByAgeSeconds() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'ageSeconds', Sort.asc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      thenByAgeSecondsDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'ageSeconds', Sort.desc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      thenByCacheKey() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'cacheKey', Sort.asc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      thenByCacheKeyDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'cacheKey', Sort.desc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      thenByCreatedAt() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'createdAt', Sort.asc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      thenByCreatedAtDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'createdAt', Sort.desc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      thenByDataSize() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'dataSize', Sort.asc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      thenByDataSizeDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'dataSize', Sort.desc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      thenById() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'id', Sort.asc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      thenByIdDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'id', Sort.desc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      thenByIsFullySynced() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'isFullySynced', Sort.asc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      thenByIsFullySyncedDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'isFullySynced', Sort.desc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      thenByLastAccessedAt() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'lastAccessedAt', Sort.asc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      thenByLastAccessedAtDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'lastAccessedAt', Sort.desc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      thenByMetadata() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'metadata', Sort.asc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      thenByMetadataDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'metadata', Sort.desc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      thenByPeriod() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'period', Sort.asc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      thenByPeriodDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'period', Sort.desc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      thenByPeriodEnd() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'periodEnd', Sort.asc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      thenByPeriodEndDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'periodEnd', Sort.desc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      thenByPeriodStart() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'periodStart', Sort.asc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      thenByPeriodStartDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'periodStart', Sort.desc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      thenByPriority() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'priority', Sort.asc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      thenByPriorityDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'priority', Sort.desc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      thenByTtlSeconds() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'ttlSeconds', Sort.asc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      thenByTtlSecondsDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'ttlSeconds', Sort.desc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      thenByType() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'type', Sort.asc);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QAfterSortBy>
      thenByTypeDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'type', Sort.desc);
    });
  }
}

extension CachedStatisticsModelQueryWhereDistinct
    on QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QDistinct> {
  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QDistinct>
      distinctByAgeSeconds() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'ageSeconds');
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QDistinct>
      distinctByCacheKey({bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'cacheKey', caseSensitive: caseSensitive);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QDistinct>
      distinctByCreatedAt() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'createdAt');
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QDistinct>
      distinctByDataSize() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'dataSize');
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QDistinct>
      distinctByIsFullySynced() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'isFullySynced');
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QDistinct>
      distinctByJsonData() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'jsonData');
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QDistinct>
      distinctByLastAccessedAt() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'lastAccessedAt');
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QDistinct>
      distinctByMetadata({bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'metadata', caseSensitive: caseSensitive);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QDistinct>
      distinctByPeriod({bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'period', caseSensitive: caseSensitive);
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QDistinct>
      distinctByPeriodEnd() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'periodEnd');
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QDistinct>
      distinctByPeriodStart() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'periodStart');
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QDistinct>
      distinctByPriority() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'priority');
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QDistinct>
      distinctByTtlSeconds() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'ttlSeconds');
    });
  }

  QueryBuilder<CachedStatisticsModel, CachedStatisticsModel, QDistinct>
      distinctByType({bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'type', caseSensitive: caseSensitive);
    });
  }
}

extension CachedStatisticsModelQueryProperty on QueryBuilder<
    CachedStatisticsModel, CachedStatisticsModel, QQueryProperty> {
  QueryBuilder<CachedStatisticsModel, int, QQueryOperations> idProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'id');
    });
  }

  QueryBuilder<CachedStatisticsModel, int, QQueryOperations>
      ageSecondsProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'ageSeconds');
    });
  }

  QueryBuilder<CachedStatisticsModel, String, QQueryOperations>
      cacheKeyProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'cacheKey');
    });
  }

  QueryBuilder<CachedStatisticsModel, DateTime, QQueryOperations>
      createdAtProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'createdAt');
    });
  }

  QueryBuilder<CachedStatisticsModel, int, QQueryOperations>
      dataSizeProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'dataSize');
    });
  }

  QueryBuilder<CachedStatisticsModel, bool, QQueryOperations>
      isFullySyncedProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'isFullySynced');
    });
  }

  QueryBuilder<CachedStatisticsModel, List<int>, QQueryOperations>
      jsonDataProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'jsonData');
    });
  }

  QueryBuilder<CachedStatisticsModel, DateTime, QQueryOperations>
      lastAccessedAtProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'lastAccessedAt');
    });
  }

  QueryBuilder<CachedStatisticsModel, String?, QQueryOperations>
      metadataProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'metadata');
    });
  }

  QueryBuilder<CachedStatisticsModel, StatisticsPeriod, QQueryOperations>
      periodProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'period');
    });
  }

  QueryBuilder<CachedStatisticsModel, DateTime, QQueryOperations>
      periodEndProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'periodEnd');
    });
  }

  QueryBuilder<CachedStatisticsModel, DateTime, QQueryOperations>
      periodStartProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'periodStart');
    });
  }

  QueryBuilder<CachedStatisticsModel, int, QQueryOperations>
      priorityProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'priority');
    });
  }

  QueryBuilder<CachedStatisticsModel, int?, QQueryOperations>
      ttlSecondsProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'ttlSeconds');
    });
  }

  QueryBuilder<CachedStatisticsModel, StatisticsType, QQueryOperations>
      typeProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'type');
    });
  }
}
