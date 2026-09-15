// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'vocab_word.dart';

// **************************************************************************
// IsarCollectionGenerator
// **************************************************************************

// coverage:ignore-file
// ignore_for_file: duplicate_ignore, non_constant_identifier_names, constant_identifier_names, invalid_use_of_protected_member, unnecessary_cast, prefer_const_constructors, lines_longer_than_80_chars, require_trailing_commas, inference_failure_on_function_invocation, unnecessary_parenthesis, unnecessary_raw_strings, unnecessary_null_checks, join_return_with_assignment, prefer_final_locals, avoid_js_rounded_ints, avoid_positional_boolean_parameters, always_specify_types

extension GetVocabWordCollection on Isar {
  IsarCollection<VocabWord> get vocabWords => this.collection();
}

const VocabWordSchema = CollectionSchema(
  name: r'VocabWord',
  id: 5401094777627121794,
  properties: {
    r'accuracyRate': PropertySchema(
      id: 0,
      name: r'accuracyRate',
      type: IsarType.double,
    ),
    r'consecutiveCorrect': PropertySchema(
      id: 1,
      name: r'consecutiveCorrect',
      type: IsarType.long,
    ),
    r'correctReviewCount': PropertySchema(
      id: 2,
      name: r'correctReviewCount',
      type: IsarType.long,
    ),
    r'createdAt': PropertySchema(
      id: 3,
      name: r'createdAt',
      type: IsarType.dateTime,
    ),
    r'daysUntilReview': PropertySchema(
      id: 4,
      name: r'daysUntilReview',
      type: IsarType.long,
    ),
    r'definition': PropertySchema(
      id: 5,
      name: r'definition',
      type: IsarType.string,
    ),
    r'exampleSentence': PropertySchema(
      id: 6,
      name: r'exampleSentence',
      type: IsarType.string,
    ),
    r'importance': PropertySchema(
      id: 7,
      name: r'importance',
      type: IsarType.long,
    ),
    r'isDueForReview': PropertySchema(
      id: 8,
      name: r'isDueForReview',
      type: IsarType.bool,
    ),
    r'lastReviewAt': PropertySchema(
      id: 9,
      name: r'lastReviewAt',
      type: IsarType.dateTime,
    ),
    r'nextReviewAt': PropertySchema(
      id: 10,
      name: r'nextReviewAt',
      type: IsarType.dateTime,
    ),
    r'partOfSpeech': PropertySchema(
      id: 11,
      name: r'partOfSpeech',
      type: IsarType.string,
    ),
    r'phonetic': PropertySchema(
      id: 12,
      name: r'phonetic',
      type: IsarType.string,
    ),
    r'reviewCount': PropertySchema(
      id: 13,
      name: r'reviewCount',
      type: IsarType.long,
    ),
    r'sourceTranslationId': PropertySchema(
      id: 14,
      name: r'sourceTranslationId',
      type: IsarType.string,
    ),
    r'tags': PropertySchema(
      id: 15,
      name: r'tags',
      type: IsarType.stringList,
    ),
    r'taskId': PropertySchema(
      id: 16,
      name: r'taskId',
      type: IsarType.string,
    ),
    r'updatedAt': PropertySchema(
      id: 17,
      name: r'updatedAt',
      type: IsarType.dateTime,
    ),
    r'word': PropertySchema(
      id: 18,
      name: r'word',
      type: IsarType.string,
    )
  },
  estimateSize: _vocabWordEstimateSize,
  serialize: _vocabWordSerialize,
  deserialize: _vocabWordDeserialize,
  deserializeProp: _vocabWordDeserializeProp,
  idName: r'id',
  indexes: {
    r'word': IndexSchema(
      id: -2031626334120420267,
      name: r'word',
      unique: true,
      replace: false,
      properties: [
        IndexPropertySchema(
          name: r'word',
          type: IndexType.hash,
          caseSensitive: true,
        )
      ],
    ),
    r'nextReviewAt': IndexSchema(
      id: -3214419740154650383,
      name: r'nextReviewAt',
      unique: false,
      replace: false,
      properties: [
        IndexPropertySchema(
          name: r'nextReviewAt',
          type: IndexType.value,
          caseSensitive: false,
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
    )
  },
  links: {},
  embeddedSchemas: {},
  getId: _vocabWordGetId,
  getLinks: _vocabWordGetLinks,
  attach: _vocabWordAttach,
  version: '3.1.0+1',
);

int _vocabWordEstimateSize(
  VocabWord object,
  List<int> offsets,
  Map<Type, List<int>> allOffsets,
) {
  var bytesCount = offsets.last;
  {
    final value = object.definition;
    if (value != null) {
      bytesCount += 3 + value.length * 3;
    }
  }
  {
    final value = object.exampleSentence;
    if (value != null) {
      bytesCount += 3 + value.length * 3;
    }
  }
  {
    final value = object.partOfSpeech;
    if (value != null) {
      bytesCount += 3 + value.length * 3;
    }
  }
  {
    final value = object.phonetic;
    if (value != null) {
      bytesCount += 3 + value.length * 3;
    }
  }
  {
    final value = object.sourceTranslationId;
    if (value != null) {
      bytesCount += 3 + value.length * 3;
    }
  }
  bytesCount += 3 + object.tags.length * 3;
  {
    for (var i = 0; i < object.tags.length; i++) {
      final value = object.tags[i];
      bytesCount += value.length * 3;
    }
  }
  {
    final value = object.taskId;
    if (value != null) {
      bytesCount += 3 + value.length * 3;
    }
  }
  bytesCount += 3 + object.word.length * 3;
  return bytesCount;
}

void _vocabWordSerialize(
  VocabWord object,
  IsarWriter writer,
  List<int> offsets,
  Map<Type, List<int>> allOffsets,
) {
  writer.writeDouble(offsets[0], object.accuracyRate);
  writer.writeLong(offsets[1], object.consecutiveCorrect);
  writer.writeLong(offsets[2], object.correctReviewCount);
  writer.writeDateTime(offsets[3], object.createdAt);
  writer.writeLong(offsets[4], object.daysUntilReview);
  writer.writeString(offsets[5], object.definition);
  writer.writeString(offsets[6], object.exampleSentence);
  writer.writeLong(offsets[7], object.importance);
  writer.writeBool(offsets[8], object.isDueForReview);
  writer.writeDateTime(offsets[9], object.lastReviewAt);
  writer.writeDateTime(offsets[10], object.nextReviewAt);
  writer.writeString(offsets[11], object.partOfSpeech);
  writer.writeString(offsets[12], object.phonetic);
  writer.writeLong(offsets[13], object.reviewCount);
  writer.writeString(offsets[14], object.sourceTranslationId);
  writer.writeStringList(offsets[15], object.tags);
  writer.writeString(offsets[16], object.taskId);
  writer.writeDateTime(offsets[17], object.updatedAt);
  writer.writeString(offsets[18], object.word);
}

VocabWord _vocabWordDeserialize(
  Id id,
  IsarReader reader,
  List<int> offsets,
  Map<Type, List<int>> allOffsets,
) {
  final object = VocabWord();
  object.consecutiveCorrect = reader.readLong(offsets[1]);
  object.correctReviewCount = reader.readLong(offsets[2]);
  object.createdAt = reader.readDateTime(offsets[3]);
  object.definition = reader.readStringOrNull(offsets[5]);
  object.exampleSentence = reader.readStringOrNull(offsets[6]);
  object.id = id;
  object.importance = reader.readLong(offsets[7]);
  object.lastReviewAt = reader.readDateTimeOrNull(offsets[9]);
  object.nextReviewAt = reader.readDateTimeOrNull(offsets[10]);
  object.partOfSpeech = reader.readStringOrNull(offsets[11]);
  object.phonetic = reader.readStringOrNull(offsets[12]);
  object.reviewCount = reader.readLong(offsets[13]);
  object.sourceTranslationId = reader.readStringOrNull(offsets[14]);
  object.tags = reader.readStringList(offsets[15]) ?? [];
  object.taskId = reader.readStringOrNull(offsets[16]);
  object.updatedAt = reader.readDateTime(offsets[17]);
  object.word = reader.readString(offsets[18]);
  return object;
}

P _vocabWordDeserializeProp<P>(
  IsarReader reader,
  int propertyId,
  int offset,
  Map<Type, List<int>> allOffsets,
) {
  switch (propertyId) {
    case 0:
      return (reader.readDouble(offset)) as P;
    case 1:
      return (reader.readLong(offset)) as P;
    case 2:
      return (reader.readLong(offset)) as P;
    case 3:
      return (reader.readDateTime(offset)) as P;
    case 4:
      return (reader.readLongOrNull(offset)) as P;
    case 5:
      return (reader.readStringOrNull(offset)) as P;
    case 6:
      return (reader.readStringOrNull(offset)) as P;
    case 7:
      return (reader.readLong(offset)) as P;
    case 8:
      return (reader.readBool(offset)) as P;
    case 9:
      return (reader.readDateTimeOrNull(offset)) as P;
    case 10:
      return (reader.readDateTimeOrNull(offset)) as P;
    case 11:
      return (reader.readStringOrNull(offset)) as P;
    case 12:
      return (reader.readStringOrNull(offset)) as P;
    case 13:
      return (reader.readLong(offset)) as P;
    case 14:
      return (reader.readStringOrNull(offset)) as P;
    case 15:
      return (reader.readStringList(offset) ?? []) as P;
    case 16:
      return (reader.readStringOrNull(offset)) as P;
    case 17:
      return (reader.readDateTime(offset)) as P;
    case 18:
      return (reader.readString(offset)) as P;
    default:
      throw IsarError('Unknown property with id $propertyId');
  }
}

Id _vocabWordGetId(VocabWord object) {
  return object.id;
}

List<IsarLinkBase<dynamic>> _vocabWordGetLinks(VocabWord object) {
  return [];
}

void _vocabWordAttach(IsarCollection<dynamic> col, Id id, VocabWord object) {
  object.id = id;
}

extension VocabWordByIndex on IsarCollection<VocabWord> {
  Future<VocabWord?> getByWord(String word) {
    return getByIndex(r'word', [word]);
  }

  VocabWord? getByWordSync(String word) {
    return getByIndexSync(r'word', [word]);
  }

  Future<bool> deleteByWord(String word) {
    return deleteByIndex(r'word', [word]);
  }

  bool deleteByWordSync(String word) {
    return deleteByIndexSync(r'word', [word]);
  }

  Future<List<VocabWord?>> getAllByWord(List<String> wordValues) {
    final values = wordValues.map((e) => [e]).toList();
    return getAllByIndex(r'word', values);
  }

  List<VocabWord?> getAllByWordSync(List<String> wordValues) {
    final values = wordValues.map((e) => [e]).toList();
    return getAllByIndexSync(r'word', values);
  }

  Future<int> deleteAllByWord(List<String> wordValues) {
    final values = wordValues.map((e) => [e]).toList();
    return deleteAllByIndex(r'word', values);
  }

  int deleteAllByWordSync(List<String> wordValues) {
    final values = wordValues.map((e) => [e]).toList();
    return deleteAllByIndexSync(r'word', values);
  }

  Future<Id> putByWord(VocabWord object) {
    return putByIndex(r'word', object);
  }

  Id putByWordSync(VocabWord object, {bool saveLinks = true}) {
    return putByIndexSync(r'word', object, saveLinks: saveLinks);
  }

  Future<List<Id>> putAllByWord(List<VocabWord> objects) {
    return putAllByIndex(r'word', objects);
  }

  List<Id> putAllByWordSync(List<VocabWord> objects, {bool saveLinks = true}) {
    return putAllByIndexSync(r'word', objects, saveLinks: saveLinks);
  }
}

extension VocabWordQueryWhereSort
    on QueryBuilder<VocabWord, VocabWord, QWhere> {
  QueryBuilder<VocabWord, VocabWord, QAfterWhere> anyId() {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(const IdWhereClause.any());
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterWhere> anyNextReviewAt() {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(
        const IndexWhereClause.any(indexName: r'nextReviewAt'),
      );
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterWhere> anyCreatedAt() {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(
        const IndexWhereClause.any(indexName: r'createdAt'),
      );
    });
  }
}

extension VocabWordQueryWhere
    on QueryBuilder<VocabWord, VocabWord, QWhereClause> {
  QueryBuilder<VocabWord, VocabWord, QAfterWhereClause> idEqualTo(Id id) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IdWhereClause.between(
        lower: id,
        upper: id,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterWhereClause> idNotEqualTo(Id id) {
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

  QueryBuilder<VocabWord, VocabWord, QAfterWhereClause> idGreaterThan(Id id,
      {bool include = false}) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(
        IdWhereClause.greaterThan(lower: id, includeLower: include),
      );
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterWhereClause> idLessThan(Id id,
      {bool include = false}) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(
        IdWhereClause.lessThan(upper: id, includeUpper: include),
      );
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterWhereClause> idBetween(
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

  QueryBuilder<VocabWord, VocabWord, QAfterWhereClause> wordEqualTo(
      String word) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IndexWhereClause.equalTo(
        indexName: r'word',
        value: [word],
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterWhereClause> wordNotEqualTo(
      String word) {
    return QueryBuilder.apply(this, (query) {
      if (query.whereSort == Sort.asc) {
        return query
            .addWhereClause(IndexWhereClause.between(
              indexName: r'word',
              lower: [],
              upper: [word],
              includeUpper: false,
            ))
            .addWhereClause(IndexWhereClause.between(
              indexName: r'word',
              lower: [word],
              includeLower: false,
              upper: [],
            ));
      } else {
        return query
            .addWhereClause(IndexWhereClause.between(
              indexName: r'word',
              lower: [word],
              includeLower: false,
              upper: [],
            ))
            .addWhereClause(IndexWhereClause.between(
              indexName: r'word',
              lower: [],
              upper: [word],
              includeUpper: false,
            ));
      }
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterWhereClause> nextReviewAtIsNull() {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IndexWhereClause.equalTo(
        indexName: r'nextReviewAt',
        value: [null],
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterWhereClause>
      nextReviewAtIsNotNull() {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IndexWhereClause.between(
        indexName: r'nextReviewAt',
        lower: [null],
        includeLower: false,
        upper: [],
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterWhereClause> nextReviewAtEqualTo(
      DateTime? nextReviewAt) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IndexWhereClause.equalTo(
        indexName: r'nextReviewAt',
        value: [nextReviewAt],
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterWhereClause> nextReviewAtNotEqualTo(
      DateTime? nextReviewAt) {
    return QueryBuilder.apply(this, (query) {
      if (query.whereSort == Sort.asc) {
        return query
            .addWhereClause(IndexWhereClause.between(
              indexName: r'nextReviewAt',
              lower: [],
              upper: [nextReviewAt],
              includeUpper: false,
            ))
            .addWhereClause(IndexWhereClause.between(
              indexName: r'nextReviewAt',
              lower: [nextReviewAt],
              includeLower: false,
              upper: [],
            ));
      } else {
        return query
            .addWhereClause(IndexWhereClause.between(
              indexName: r'nextReviewAt',
              lower: [nextReviewAt],
              includeLower: false,
              upper: [],
            ))
            .addWhereClause(IndexWhereClause.between(
              indexName: r'nextReviewAt',
              lower: [],
              upper: [nextReviewAt],
              includeUpper: false,
            ));
      }
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterWhereClause> nextReviewAtGreaterThan(
    DateTime? nextReviewAt, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IndexWhereClause.between(
        indexName: r'nextReviewAt',
        lower: [nextReviewAt],
        includeLower: include,
        upper: [],
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterWhereClause> nextReviewAtLessThan(
    DateTime? nextReviewAt, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IndexWhereClause.between(
        indexName: r'nextReviewAt',
        lower: [],
        upper: [nextReviewAt],
        includeUpper: include,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterWhereClause> nextReviewAtBetween(
    DateTime? lowerNextReviewAt,
    DateTime? upperNextReviewAt, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IndexWhereClause.between(
        indexName: r'nextReviewAt',
        lower: [lowerNextReviewAt],
        includeLower: includeLower,
        upper: [upperNextReviewAt],
        includeUpper: includeUpper,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterWhereClause> createdAtEqualTo(
      DateTime createdAt) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IndexWhereClause.equalTo(
        indexName: r'createdAt',
        value: [createdAt],
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterWhereClause> createdAtNotEqualTo(
      DateTime createdAt) {
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

  QueryBuilder<VocabWord, VocabWord, QAfterWhereClause> createdAtGreaterThan(
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

  QueryBuilder<VocabWord, VocabWord, QAfterWhereClause> createdAtLessThan(
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

  QueryBuilder<VocabWord, VocabWord, QAfterWhereClause> createdAtBetween(
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
}

extension VocabWordQueryFilter
    on QueryBuilder<VocabWord, VocabWord, QFilterCondition> {
  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> accuracyRateEqualTo(
    double value, {
    double epsilon = Query.epsilon,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'accuracyRate',
        value: value,
        epsilon: epsilon,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      accuracyRateGreaterThan(
    double value, {
    bool include = false,
    double epsilon = Query.epsilon,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'accuracyRate',
        value: value,
        epsilon: epsilon,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      accuracyRateLessThan(
    double value, {
    bool include = false,
    double epsilon = Query.epsilon,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'accuracyRate',
        value: value,
        epsilon: epsilon,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> accuracyRateBetween(
    double lower,
    double upper, {
    bool includeLower = true,
    bool includeUpper = true,
    double epsilon = Query.epsilon,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'accuracyRate',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
        epsilon: epsilon,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      consecutiveCorrectEqualTo(int value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'consecutiveCorrect',
        value: value,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      consecutiveCorrectGreaterThan(
    int value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'consecutiveCorrect',
        value: value,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      consecutiveCorrectLessThan(
    int value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'consecutiveCorrect',
        value: value,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      consecutiveCorrectBetween(
    int lower,
    int upper, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'consecutiveCorrect',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      correctReviewCountEqualTo(int value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'correctReviewCount',
        value: value,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      correctReviewCountGreaterThan(
    int value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'correctReviewCount',
        value: value,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      correctReviewCountLessThan(
    int value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'correctReviewCount',
        value: value,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      correctReviewCountBetween(
    int lower,
    int upper, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'correctReviewCount',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> createdAtEqualTo(
      DateTime value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'createdAt',
        value: value,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      createdAtGreaterThan(
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

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> createdAtLessThan(
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

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> createdAtBetween(
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

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      daysUntilReviewIsNull() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(const FilterCondition.isNull(
        property: r'daysUntilReview',
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      daysUntilReviewIsNotNull() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(const FilterCondition.isNotNull(
        property: r'daysUntilReview',
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      daysUntilReviewEqualTo(int? value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'daysUntilReview',
        value: value,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      daysUntilReviewGreaterThan(
    int? value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'daysUntilReview',
        value: value,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      daysUntilReviewLessThan(
    int? value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'daysUntilReview',
        value: value,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      daysUntilReviewBetween(
    int? lower,
    int? upper, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'daysUntilReview',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> definitionIsNull() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(const FilterCondition.isNull(
        property: r'definition',
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      definitionIsNotNull() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(const FilterCondition.isNotNull(
        property: r'definition',
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> definitionEqualTo(
    String? value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'definition',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      definitionGreaterThan(
    String? value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'definition',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> definitionLessThan(
    String? value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'definition',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> definitionBetween(
    String? lower,
    String? upper, {
    bool includeLower = true,
    bool includeUpper = true,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'definition',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      definitionStartsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.startsWith(
        property: r'definition',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> definitionEndsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.endsWith(
        property: r'definition',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> definitionContains(
      String value,
      {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.contains(
        property: r'definition',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> definitionMatches(
      String pattern,
      {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.matches(
        property: r'definition',
        wildcard: pattern,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      definitionIsEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'definition',
        value: '',
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      definitionIsNotEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        property: r'definition',
        value: '',
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      exampleSentenceIsNull() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(const FilterCondition.isNull(
        property: r'exampleSentence',
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      exampleSentenceIsNotNull() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(const FilterCondition.isNotNull(
        property: r'exampleSentence',
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      exampleSentenceEqualTo(
    String? value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'exampleSentence',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      exampleSentenceGreaterThan(
    String? value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'exampleSentence',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      exampleSentenceLessThan(
    String? value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'exampleSentence',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      exampleSentenceBetween(
    String? lower,
    String? upper, {
    bool includeLower = true,
    bool includeUpper = true,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'exampleSentence',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      exampleSentenceStartsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.startsWith(
        property: r'exampleSentence',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      exampleSentenceEndsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.endsWith(
        property: r'exampleSentence',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      exampleSentenceContains(String value, {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.contains(
        property: r'exampleSentence',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      exampleSentenceMatches(String pattern, {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.matches(
        property: r'exampleSentence',
        wildcard: pattern,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      exampleSentenceIsEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'exampleSentence',
        value: '',
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      exampleSentenceIsNotEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        property: r'exampleSentence',
        value: '',
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> idEqualTo(
      Id value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'id',
        value: value,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> idGreaterThan(
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

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> idLessThan(
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

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> idBetween(
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

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> importanceEqualTo(
      int value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'importance',
        value: value,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      importanceGreaterThan(
    int value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'importance',
        value: value,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> importanceLessThan(
    int value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'importance',
        value: value,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> importanceBetween(
    int lower,
    int upper, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'importance',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      isDueForReviewEqualTo(bool value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'isDueForReview',
        value: value,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      lastReviewAtIsNull() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(const FilterCondition.isNull(
        property: r'lastReviewAt',
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      lastReviewAtIsNotNull() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(const FilterCondition.isNotNull(
        property: r'lastReviewAt',
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> lastReviewAtEqualTo(
      DateTime? value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'lastReviewAt',
        value: value,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      lastReviewAtGreaterThan(
    DateTime? value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'lastReviewAt',
        value: value,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      lastReviewAtLessThan(
    DateTime? value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'lastReviewAt',
        value: value,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> lastReviewAtBetween(
    DateTime? lower,
    DateTime? upper, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'lastReviewAt',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      nextReviewAtIsNull() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(const FilterCondition.isNull(
        property: r'nextReviewAt',
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      nextReviewAtIsNotNull() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(const FilterCondition.isNotNull(
        property: r'nextReviewAt',
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> nextReviewAtEqualTo(
      DateTime? value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'nextReviewAt',
        value: value,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      nextReviewAtGreaterThan(
    DateTime? value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'nextReviewAt',
        value: value,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      nextReviewAtLessThan(
    DateTime? value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'nextReviewAt',
        value: value,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> nextReviewAtBetween(
    DateTime? lower,
    DateTime? upper, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'nextReviewAt',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      partOfSpeechIsNull() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(const FilterCondition.isNull(
        property: r'partOfSpeech',
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      partOfSpeechIsNotNull() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(const FilterCondition.isNotNull(
        property: r'partOfSpeech',
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> partOfSpeechEqualTo(
    String? value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'partOfSpeech',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      partOfSpeechGreaterThan(
    String? value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'partOfSpeech',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      partOfSpeechLessThan(
    String? value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'partOfSpeech',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> partOfSpeechBetween(
    String? lower,
    String? upper, {
    bool includeLower = true,
    bool includeUpper = true,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'partOfSpeech',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      partOfSpeechStartsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.startsWith(
        property: r'partOfSpeech',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      partOfSpeechEndsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.endsWith(
        property: r'partOfSpeech',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      partOfSpeechContains(String value, {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.contains(
        property: r'partOfSpeech',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> partOfSpeechMatches(
      String pattern,
      {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.matches(
        property: r'partOfSpeech',
        wildcard: pattern,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      partOfSpeechIsEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'partOfSpeech',
        value: '',
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      partOfSpeechIsNotEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        property: r'partOfSpeech',
        value: '',
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> phoneticIsNull() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(const FilterCondition.isNull(
        property: r'phonetic',
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      phoneticIsNotNull() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(const FilterCondition.isNotNull(
        property: r'phonetic',
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> phoneticEqualTo(
    String? value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'phonetic',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> phoneticGreaterThan(
    String? value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'phonetic',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> phoneticLessThan(
    String? value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'phonetic',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> phoneticBetween(
    String? lower,
    String? upper, {
    bool includeLower = true,
    bool includeUpper = true,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'phonetic',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> phoneticStartsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.startsWith(
        property: r'phonetic',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> phoneticEndsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.endsWith(
        property: r'phonetic',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> phoneticContains(
      String value,
      {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.contains(
        property: r'phonetic',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> phoneticMatches(
      String pattern,
      {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.matches(
        property: r'phonetic',
        wildcard: pattern,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> phoneticIsEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'phonetic',
        value: '',
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      phoneticIsNotEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        property: r'phonetic',
        value: '',
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> reviewCountEqualTo(
      int value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'reviewCount',
        value: value,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      reviewCountGreaterThan(
    int value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'reviewCount',
        value: value,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> reviewCountLessThan(
    int value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'reviewCount',
        value: value,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> reviewCountBetween(
    int lower,
    int upper, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'reviewCount',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      sourceTranslationIdIsNull() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(const FilterCondition.isNull(
        property: r'sourceTranslationId',
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      sourceTranslationIdIsNotNull() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(const FilterCondition.isNotNull(
        property: r'sourceTranslationId',
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      sourceTranslationIdEqualTo(
    String? value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'sourceTranslationId',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      sourceTranslationIdGreaterThan(
    String? value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'sourceTranslationId',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      sourceTranslationIdLessThan(
    String? value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'sourceTranslationId',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      sourceTranslationIdBetween(
    String? lower,
    String? upper, {
    bool includeLower = true,
    bool includeUpper = true,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'sourceTranslationId',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      sourceTranslationIdStartsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.startsWith(
        property: r'sourceTranslationId',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      sourceTranslationIdEndsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.endsWith(
        property: r'sourceTranslationId',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      sourceTranslationIdContains(String value, {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.contains(
        property: r'sourceTranslationId',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      sourceTranslationIdMatches(String pattern, {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.matches(
        property: r'sourceTranslationId',
        wildcard: pattern,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      sourceTranslationIdIsEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'sourceTranslationId',
        value: '',
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      sourceTranslationIdIsNotEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        property: r'sourceTranslationId',
        value: '',
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> tagsElementEqualTo(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'tags',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      tagsElementGreaterThan(
    String value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'tags',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> tagsElementLessThan(
    String value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'tags',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> tagsElementBetween(
    String lower,
    String upper, {
    bool includeLower = true,
    bool includeUpper = true,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'tags',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      tagsElementStartsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.startsWith(
        property: r'tags',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> tagsElementEndsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.endsWith(
        property: r'tags',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> tagsElementContains(
      String value,
      {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.contains(
        property: r'tags',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> tagsElementMatches(
      String pattern,
      {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.matches(
        property: r'tags',
        wildcard: pattern,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      tagsElementIsEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'tags',
        value: '',
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      tagsElementIsNotEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        property: r'tags',
        value: '',
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> tagsLengthEqualTo(
      int length) {
    return QueryBuilder.apply(this, (query) {
      return query.listLength(
        r'tags',
        length,
        true,
        length,
        true,
      );
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> tagsIsEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.listLength(
        r'tags',
        0,
        true,
        0,
        true,
      );
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> tagsIsNotEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.listLength(
        r'tags',
        0,
        false,
        999999,
        true,
      );
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> tagsLengthLessThan(
    int length, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.listLength(
        r'tags',
        0,
        true,
        length,
        include,
      );
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      tagsLengthGreaterThan(
    int length, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.listLength(
        r'tags',
        length,
        include,
        999999,
        true,
      );
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> tagsLengthBetween(
    int lower,
    int upper, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.listLength(
        r'tags',
        lower,
        includeLower,
        upper,
        includeUpper,
      );
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> taskIdIsNull() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(const FilterCondition.isNull(
        property: r'taskId',
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> taskIdIsNotNull() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(const FilterCondition.isNotNull(
        property: r'taskId',
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> taskIdEqualTo(
    String? value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'taskId',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> taskIdGreaterThan(
    String? value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'taskId',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> taskIdLessThan(
    String? value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'taskId',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> taskIdBetween(
    String? lower,
    String? upper, {
    bool includeLower = true,
    bool includeUpper = true,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'taskId',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> taskIdStartsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.startsWith(
        property: r'taskId',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> taskIdEndsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.endsWith(
        property: r'taskId',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> taskIdContains(
      String value,
      {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.contains(
        property: r'taskId',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> taskIdMatches(
      String pattern,
      {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.matches(
        property: r'taskId',
        wildcard: pattern,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> taskIdIsEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'taskId',
        value: '',
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> taskIdIsNotEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        property: r'taskId',
        value: '',
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> updatedAtEqualTo(
      DateTime value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'updatedAt',
        value: value,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition>
      updatedAtGreaterThan(
    DateTime value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'updatedAt',
        value: value,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> updatedAtLessThan(
    DateTime value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'updatedAt',
        value: value,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> updatedAtBetween(
    DateTime lower,
    DateTime upper, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'updatedAt',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> wordEqualTo(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'word',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> wordGreaterThan(
    String value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'word',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> wordLessThan(
    String value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'word',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> wordBetween(
    String lower,
    String upper, {
    bool includeLower = true,
    bool includeUpper = true,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'word',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> wordStartsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.startsWith(
        property: r'word',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> wordEndsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.endsWith(
        property: r'word',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> wordContains(
      String value,
      {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.contains(
        property: r'word',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> wordMatches(
      String pattern,
      {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.matches(
        property: r'word',
        wildcard: pattern,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> wordIsEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'word',
        value: '',
      ));
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterFilterCondition> wordIsNotEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        property: r'word',
        value: '',
      ));
    });
  }
}

extension VocabWordQueryObject
    on QueryBuilder<VocabWord, VocabWord, QFilterCondition> {}

extension VocabWordQueryLinks
    on QueryBuilder<VocabWord, VocabWord, QFilterCondition> {}

extension VocabWordQuerySortBy on QueryBuilder<VocabWord, VocabWord, QSortBy> {
  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> sortByAccuracyRate() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'accuracyRate', Sort.asc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> sortByAccuracyRateDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'accuracyRate', Sort.desc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> sortByConsecutiveCorrect() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'consecutiveCorrect', Sort.asc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy>
      sortByConsecutiveCorrectDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'consecutiveCorrect', Sort.desc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> sortByCorrectReviewCount() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'correctReviewCount', Sort.asc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy>
      sortByCorrectReviewCountDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'correctReviewCount', Sort.desc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> sortByCreatedAt() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'createdAt', Sort.asc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> sortByCreatedAtDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'createdAt', Sort.desc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> sortByDaysUntilReview() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'daysUntilReview', Sort.asc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> sortByDaysUntilReviewDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'daysUntilReview', Sort.desc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> sortByDefinition() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'definition', Sort.asc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> sortByDefinitionDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'definition', Sort.desc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> sortByExampleSentence() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'exampleSentence', Sort.asc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> sortByExampleSentenceDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'exampleSentence', Sort.desc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> sortByImportance() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'importance', Sort.asc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> sortByImportanceDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'importance', Sort.desc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> sortByIsDueForReview() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'isDueForReview', Sort.asc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> sortByIsDueForReviewDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'isDueForReview', Sort.desc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> sortByLastReviewAt() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'lastReviewAt', Sort.asc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> sortByLastReviewAtDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'lastReviewAt', Sort.desc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> sortByNextReviewAt() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'nextReviewAt', Sort.asc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> sortByNextReviewAtDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'nextReviewAt', Sort.desc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> sortByPartOfSpeech() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'partOfSpeech', Sort.asc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> sortByPartOfSpeechDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'partOfSpeech', Sort.desc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> sortByPhonetic() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'phonetic', Sort.asc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> sortByPhoneticDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'phonetic', Sort.desc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> sortByReviewCount() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'reviewCount', Sort.asc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> sortByReviewCountDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'reviewCount', Sort.desc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> sortBySourceTranslationId() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'sourceTranslationId', Sort.asc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy>
      sortBySourceTranslationIdDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'sourceTranslationId', Sort.desc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> sortByTaskId() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'taskId', Sort.asc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> sortByTaskIdDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'taskId', Sort.desc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> sortByUpdatedAt() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'updatedAt', Sort.asc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> sortByUpdatedAtDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'updatedAt', Sort.desc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> sortByWord() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'word', Sort.asc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> sortByWordDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'word', Sort.desc);
    });
  }
}

extension VocabWordQuerySortThenBy
    on QueryBuilder<VocabWord, VocabWord, QSortThenBy> {
  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> thenByAccuracyRate() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'accuracyRate', Sort.asc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> thenByAccuracyRateDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'accuracyRate', Sort.desc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> thenByConsecutiveCorrect() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'consecutiveCorrect', Sort.asc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy>
      thenByConsecutiveCorrectDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'consecutiveCorrect', Sort.desc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> thenByCorrectReviewCount() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'correctReviewCount', Sort.asc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy>
      thenByCorrectReviewCountDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'correctReviewCount', Sort.desc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> thenByCreatedAt() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'createdAt', Sort.asc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> thenByCreatedAtDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'createdAt', Sort.desc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> thenByDaysUntilReview() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'daysUntilReview', Sort.asc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> thenByDaysUntilReviewDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'daysUntilReview', Sort.desc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> thenByDefinition() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'definition', Sort.asc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> thenByDefinitionDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'definition', Sort.desc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> thenByExampleSentence() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'exampleSentence', Sort.asc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> thenByExampleSentenceDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'exampleSentence', Sort.desc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> thenById() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'id', Sort.asc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> thenByIdDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'id', Sort.desc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> thenByImportance() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'importance', Sort.asc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> thenByImportanceDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'importance', Sort.desc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> thenByIsDueForReview() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'isDueForReview', Sort.asc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> thenByIsDueForReviewDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'isDueForReview', Sort.desc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> thenByLastReviewAt() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'lastReviewAt', Sort.asc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> thenByLastReviewAtDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'lastReviewAt', Sort.desc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> thenByNextReviewAt() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'nextReviewAt', Sort.asc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> thenByNextReviewAtDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'nextReviewAt', Sort.desc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> thenByPartOfSpeech() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'partOfSpeech', Sort.asc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> thenByPartOfSpeechDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'partOfSpeech', Sort.desc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> thenByPhonetic() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'phonetic', Sort.asc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> thenByPhoneticDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'phonetic', Sort.desc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> thenByReviewCount() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'reviewCount', Sort.asc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> thenByReviewCountDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'reviewCount', Sort.desc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> thenBySourceTranslationId() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'sourceTranslationId', Sort.asc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy>
      thenBySourceTranslationIdDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'sourceTranslationId', Sort.desc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> thenByTaskId() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'taskId', Sort.asc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> thenByTaskIdDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'taskId', Sort.desc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> thenByUpdatedAt() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'updatedAt', Sort.asc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> thenByUpdatedAtDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'updatedAt', Sort.desc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> thenByWord() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'word', Sort.asc);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QAfterSortBy> thenByWordDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'word', Sort.desc);
    });
  }
}

extension VocabWordQueryWhereDistinct
    on QueryBuilder<VocabWord, VocabWord, QDistinct> {
  QueryBuilder<VocabWord, VocabWord, QDistinct> distinctByAccuracyRate() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'accuracyRate');
    });
  }

  QueryBuilder<VocabWord, VocabWord, QDistinct> distinctByConsecutiveCorrect() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'consecutiveCorrect');
    });
  }

  QueryBuilder<VocabWord, VocabWord, QDistinct> distinctByCorrectReviewCount() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'correctReviewCount');
    });
  }

  QueryBuilder<VocabWord, VocabWord, QDistinct> distinctByCreatedAt() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'createdAt');
    });
  }

  QueryBuilder<VocabWord, VocabWord, QDistinct> distinctByDaysUntilReview() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'daysUntilReview');
    });
  }

  QueryBuilder<VocabWord, VocabWord, QDistinct> distinctByDefinition(
      {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'definition', caseSensitive: caseSensitive);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QDistinct> distinctByExampleSentence(
      {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'exampleSentence',
          caseSensitive: caseSensitive);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QDistinct> distinctByImportance() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'importance');
    });
  }

  QueryBuilder<VocabWord, VocabWord, QDistinct> distinctByIsDueForReview() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'isDueForReview');
    });
  }

  QueryBuilder<VocabWord, VocabWord, QDistinct> distinctByLastReviewAt() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'lastReviewAt');
    });
  }

  QueryBuilder<VocabWord, VocabWord, QDistinct> distinctByNextReviewAt() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'nextReviewAt');
    });
  }

  QueryBuilder<VocabWord, VocabWord, QDistinct> distinctByPartOfSpeech(
      {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'partOfSpeech', caseSensitive: caseSensitive);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QDistinct> distinctByPhonetic(
      {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'phonetic', caseSensitive: caseSensitive);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QDistinct> distinctByReviewCount() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'reviewCount');
    });
  }

  QueryBuilder<VocabWord, VocabWord, QDistinct> distinctBySourceTranslationId(
      {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'sourceTranslationId',
          caseSensitive: caseSensitive);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QDistinct> distinctByTags() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'tags');
    });
  }

  QueryBuilder<VocabWord, VocabWord, QDistinct> distinctByTaskId(
      {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'taskId', caseSensitive: caseSensitive);
    });
  }

  QueryBuilder<VocabWord, VocabWord, QDistinct> distinctByUpdatedAt() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'updatedAt');
    });
  }

  QueryBuilder<VocabWord, VocabWord, QDistinct> distinctByWord(
      {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'word', caseSensitive: caseSensitive);
    });
  }
}

extension VocabWordQueryProperty
    on QueryBuilder<VocabWord, VocabWord, QQueryProperty> {
  QueryBuilder<VocabWord, int, QQueryOperations> idProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'id');
    });
  }

  QueryBuilder<VocabWord, double, QQueryOperations> accuracyRateProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'accuracyRate');
    });
  }

  QueryBuilder<VocabWord, int, QQueryOperations> consecutiveCorrectProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'consecutiveCorrect');
    });
  }

  QueryBuilder<VocabWord, int, QQueryOperations> correctReviewCountProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'correctReviewCount');
    });
  }

  QueryBuilder<VocabWord, DateTime, QQueryOperations> createdAtProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'createdAt');
    });
  }

  QueryBuilder<VocabWord, int?, QQueryOperations> daysUntilReviewProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'daysUntilReview');
    });
  }

  QueryBuilder<VocabWord, String?, QQueryOperations> definitionProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'definition');
    });
  }

  QueryBuilder<VocabWord, String?, QQueryOperations> exampleSentenceProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'exampleSentence');
    });
  }

  QueryBuilder<VocabWord, int, QQueryOperations> importanceProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'importance');
    });
  }

  QueryBuilder<VocabWord, bool, QQueryOperations> isDueForReviewProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'isDueForReview');
    });
  }

  QueryBuilder<VocabWord, DateTime?, QQueryOperations> lastReviewAtProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'lastReviewAt');
    });
  }

  QueryBuilder<VocabWord, DateTime?, QQueryOperations> nextReviewAtProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'nextReviewAt');
    });
  }

  QueryBuilder<VocabWord, String?, QQueryOperations> partOfSpeechProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'partOfSpeech');
    });
  }

  QueryBuilder<VocabWord, String?, QQueryOperations> phoneticProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'phonetic');
    });
  }

  QueryBuilder<VocabWord, int, QQueryOperations> reviewCountProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'reviewCount');
    });
  }

  QueryBuilder<VocabWord, String?, QQueryOperations>
      sourceTranslationIdProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'sourceTranslationId');
    });
  }

  QueryBuilder<VocabWord, List<String>, QQueryOperations> tagsProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'tags');
    });
  }

  QueryBuilder<VocabWord, String?, QQueryOperations> taskIdProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'taskId');
    });
  }

  QueryBuilder<VocabWord, DateTime, QQueryOperations> updatedAtProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'updatedAt');
    });
  }

  QueryBuilder<VocabWord, String, QQueryOperations> wordProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'word');
    });
  }
}

// coverage:ignore-file
// ignore_for_file: duplicate_ignore, non_constant_identifier_names, constant_identifier_names, invalid_use_of_protected_member, unnecessary_cast, prefer_const_constructors, lines_longer_than_80_chars, require_trailing_commas, inference_failure_on_function_invocation, unnecessary_parenthesis, unnecessary_raw_strings, unnecessary_null_checks, join_return_with_assignment, prefer_final_locals, avoid_js_rounded_ints, avoid_positional_boolean_parameters, always_specify_types

extension GetVocabReviewCollection on Isar {
  IsarCollection<VocabReview> get vocabReviews => this.collection();
}

const VocabReviewSchema = CollectionSchema(
  name: r'VocabReview',
  id: 1130987134492619130,
  properties: {
    r'remembered': PropertySchema(
      id: 0,
      name: r'remembered',
      type: IsarType.bool,
    ),
    r'responseTimeMs': PropertySchema(
      id: 1,
      name: r'responseTimeMs',
      type: IsarType.long,
    ),
    r'reviewedAt': PropertySchema(
      id: 2,
      name: r'reviewedAt',
      type: IsarType.dateTime,
    ),
    r'vocabWordId': PropertySchema(
      id: 3,
      name: r'vocabWordId',
      type: IsarType.long,
    )
  },
  estimateSize: _vocabReviewEstimateSize,
  serialize: _vocabReviewSerialize,
  deserialize: _vocabReviewDeserialize,
  deserializeProp: _vocabReviewDeserializeProp,
  idName: r'id',
  indexes: {
    r'vocabWordId': IndexSchema(
      id: -6719879673897648381,
      name: r'vocabWordId',
      unique: false,
      replace: false,
      properties: [
        IndexPropertySchema(
          name: r'vocabWordId',
          type: IndexType.value,
          caseSensitive: false,
        )
      ],
    )
  },
  links: {},
  embeddedSchemas: {},
  getId: _vocabReviewGetId,
  getLinks: _vocabReviewGetLinks,
  attach: _vocabReviewAttach,
  version: '3.1.0+1',
);

int _vocabReviewEstimateSize(
  VocabReview object,
  List<int> offsets,
  Map<Type, List<int>> allOffsets,
) {
  var bytesCount = offsets.last;
  return bytesCount;
}

void _vocabReviewSerialize(
  VocabReview object,
  IsarWriter writer,
  List<int> offsets,
  Map<Type, List<int>> allOffsets,
) {
  writer.writeBool(offsets[0], object.remembered);
  writer.writeLong(offsets[1], object.responseTimeMs);
  writer.writeDateTime(offsets[2], object.reviewedAt);
  writer.writeLong(offsets[3], object.vocabWordId);
}

VocabReview _vocabReviewDeserialize(
  Id id,
  IsarReader reader,
  List<int> offsets,
  Map<Type, List<int>> allOffsets,
) {
  final object = VocabReview();
  object.id = id;
  object.remembered = reader.readBool(offsets[0]);
  object.responseTimeMs = reader.readLong(offsets[1]);
  object.reviewedAt = reader.readDateTime(offsets[2]);
  object.vocabWordId = reader.readLong(offsets[3]);
  return object;
}

P _vocabReviewDeserializeProp<P>(
  IsarReader reader,
  int propertyId,
  int offset,
  Map<Type, List<int>> allOffsets,
) {
  switch (propertyId) {
    case 0:
      return (reader.readBool(offset)) as P;
    case 1:
      return (reader.readLong(offset)) as P;
    case 2:
      return (reader.readDateTime(offset)) as P;
    case 3:
      return (reader.readLong(offset)) as P;
    default:
      throw IsarError('Unknown property with id $propertyId');
  }
}

Id _vocabReviewGetId(VocabReview object) {
  return object.id;
}

List<IsarLinkBase<dynamic>> _vocabReviewGetLinks(VocabReview object) {
  return [];
}

void _vocabReviewAttach(
    IsarCollection<dynamic> col, Id id, VocabReview object) {
  object.id = id;
}

extension VocabReviewQueryWhereSort
    on QueryBuilder<VocabReview, VocabReview, QWhere> {
  QueryBuilder<VocabReview, VocabReview, QAfterWhere> anyId() {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(const IdWhereClause.any());
    });
  }

  QueryBuilder<VocabReview, VocabReview, QAfterWhere> anyVocabWordId() {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(
        const IndexWhereClause.any(indexName: r'vocabWordId'),
      );
    });
  }
}

extension VocabReviewQueryWhere
    on QueryBuilder<VocabReview, VocabReview, QWhereClause> {
  QueryBuilder<VocabReview, VocabReview, QAfterWhereClause> idEqualTo(Id id) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IdWhereClause.between(
        lower: id,
        upper: id,
      ));
    });
  }

  QueryBuilder<VocabReview, VocabReview, QAfterWhereClause> idNotEqualTo(
      Id id) {
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

  QueryBuilder<VocabReview, VocabReview, QAfterWhereClause> idGreaterThan(Id id,
      {bool include = false}) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(
        IdWhereClause.greaterThan(lower: id, includeLower: include),
      );
    });
  }

  QueryBuilder<VocabReview, VocabReview, QAfterWhereClause> idLessThan(Id id,
      {bool include = false}) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(
        IdWhereClause.lessThan(upper: id, includeUpper: include),
      );
    });
  }

  QueryBuilder<VocabReview, VocabReview, QAfterWhereClause> idBetween(
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

  QueryBuilder<VocabReview, VocabReview, QAfterWhereClause> vocabWordIdEqualTo(
      int vocabWordId) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IndexWhereClause.equalTo(
        indexName: r'vocabWordId',
        value: [vocabWordId],
      ));
    });
  }

  QueryBuilder<VocabReview, VocabReview, QAfterWhereClause>
      vocabWordIdNotEqualTo(int vocabWordId) {
    return QueryBuilder.apply(this, (query) {
      if (query.whereSort == Sort.asc) {
        return query
            .addWhereClause(IndexWhereClause.between(
              indexName: r'vocabWordId',
              lower: [],
              upper: [vocabWordId],
              includeUpper: false,
            ))
            .addWhereClause(IndexWhereClause.between(
              indexName: r'vocabWordId',
              lower: [vocabWordId],
              includeLower: false,
              upper: [],
            ));
      } else {
        return query
            .addWhereClause(IndexWhereClause.between(
              indexName: r'vocabWordId',
              lower: [vocabWordId],
              includeLower: false,
              upper: [],
            ))
            .addWhereClause(IndexWhereClause.between(
              indexName: r'vocabWordId',
              lower: [],
              upper: [vocabWordId],
              includeUpper: false,
            ));
      }
    });
  }

  QueryBuilder<VocabReview, VocabReview, QAfterWhereClause>
      vocabWordIdGreaterThan(
    int vocabWordId, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IndexWhereClause.between(
        indexName: r'vocabWordId',
        lower: [vocabWordId],
        includeLower: include,
        upper: [],
      ));
    });
  }

  QueryBuilder<VocabReview, VocabReview, QAfterWhereClause> vocabWordIdLessThan(
    int vocabWordId, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IndexWhereClause.between(
        indexName: r'vocabWordId',
        lower: [],
        upper: [vocabWordId],
        includeUpper: include,
      ));
    });
  }

  QueryBuilder<VocabReview, VocabReview, QAfterWhereClause> vocabWordIdBetween(
    int lowerVocabWordId,
    int upperVocabWordId, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IndexWhereClause.between(
        indexName: r'vocabWordId',
        lower: [lowerVocabWordId],
        includeLower: includeLower,
        upper: [upperVocabWordId],
        includeUpper: includeUpper,
      ));
    });
  }
}

extension VocabReviewQueryFilter
    on QueryBuilder<VocabReview, VocabReview, QFilterCondition> {
  QueryBuilder<VocabReview, VocabReview, QAfterFilterCondition> idEqualTo(
      Id value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'id',
        value: value,
      ));
    });
  }

  QueryBuilder<VocabReview, VocabReview, QAfterFilterCondition> idGreaterThan(
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

  QueryBuilder<VocabReview, VocabReview, QAfterFilterCondition> idLessThan(
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

  QueryBuilder<VocabReview, VocabReview, QAfterFilterCondition> idBetween(
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

  QueryBuilder<VocabReview, VocabReview, QAfterFilterCondition>
      rememberedEqualTo(bool value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'remembered',
        value: value,
      ));
    });
  }

  QueryBuilder<VocabReview, VocabReview, QAfterFilterCondition>
      responseTimeMsEqualTo(int value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'responseTimeMs',
        value: value,
      ));
    });
  }

  QueryBuilder<VocabReview, VocabReview, QAfterFilterCondition>
      responseTimeMsGreaterThan(
    int value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'responseTimeMs',
        value: value,
      ));
    });
  }

  QueryBuilder<VocabReview, VocabReview, QAfterFilterCondition>
      responseTimeMsLessThan(
    int value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'responseTimeMs',
        value: value,
      ));
    });
  }

  QueryBuilder<VocabReview, VocabReview, QAfterFilterCondition>
      responseTimeMsBetween(
    int lower,
    int upper, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'responseTimeMs',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
      ));
    });
  }

  QueryBuilder<VocabReview, VocabReview, QAfterFilterCondition>
      reviewedAtEqualTo(DateTime value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'reviewedAt',
        value: value,
      ));
    });
  }

  QueryBuilder<VocabReview, VocabReview, QAfterFilterCondition>
      reviewedAtGreaterThan(
    DateTime value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'reviewedAt',
        value: value,
      ));
    });
  }

  QueryBuilder<VocabReview, VocabReview, QAfterFilterCondition>
      reviewedAtLessThan(
    DateTime value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'reviewedAt',
        value: value,
      ));
    });
  }

  QueryBuilder<VocabReview, VocabReview, QAfterFilterCondition>
      reviewedAtBetween(
    DateTime lower,
    DateTime upper, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'reviewedAt',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
      ));
    });
  }

  QueryBuilder<VocabReview, VocabReview, QAfterFilterCondition>
      vocabWordIdEqualTo(int value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'vocabWordId',
        value: value,
      ));
    });
  }

  QueryBuilder<VocabReview, VocabReview, QAfterFilterCondition>
      vocabWordIdGreaterThan(
    int value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'vocabWordId',
        value: value,
      ));
    });
  }

  QueryBuilder<VocabReview, VocabReview, QAfterFilterCondition>
      vocabWordIdLessThan(
    int value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'vocabWordId',
        value: value,
      ));
    });
  }

  QueryBuilder<VocabReview, VocabReview, QAfterFilterCondition>
      vocabWordIdBetween(
    int lower,
    int upper, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'vocabWordId',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
      ));
    });
  }
}

extension VocabReviewQueryObject
    on QueryBuilder<VocabReview, VocabReview, QFilterCondition> {}

extension VocabReviewQueryLinks
    on QueryBuilder<VocabReview, VocabReview, QFilterCondition> {}

extension VocabReviewQuerySortBy
    on QueryBuilder<VocabReview, VocabReview, QSortBy> {
  QueryBuilder<VocabReview, VocabReview, QAfterSortBy> sortByRemembered() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'remembered', Sort.asc);
    });
  }

  QueryBuilder<VocabReview, VocabReview, QAfterSortBy> sortByRememberedDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'remembered', Sort.desc);
    });
  }

  QueryBuilder<VocabReview, VocabReview, QAfterSortBy> sortByResponseTimeMs() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'responseTimeMs', Sort.asc);
    });
  }

  QueryBuilder<VocabReview, VocabReview, QAfterSortBy>
      sortByResponseTimeMsDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'responseTimeMs', Sort.desc);
    });
  }

  QueryBuilder<VocabReview, VocabReview, QAfterSortBy> sortByReviewedAt() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'reviewedAt', Sort.asc);
    });
  }

  QueryBuilder<VocabReview, VocabReview, QAfterSortBy> sortByReviewedAtDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'reviewedAt', Sort.desc);
    });
  }

  QueryBuilder<VocabReview, VocabReview, QAfterSortBy> sortByVocabWordId() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'vocabWordId', Sort.asc);
    });
  }

  QueryBuilder<VocabReview, VocabReview, QAfterSortBy> sortByVocabWordIdDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'vocabWordId', Sort.desc);
    });
  }
}

extension VocabReviewQuerySortThenBy
    on QueryBuilder<VocabReview, VocabReview, QSortThenBy> {
  QueryBuilder<VocabReview, VocabReview, QAfterSortBy> thenById() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'id', Sort.asc);
    });
  }

  QueryBuilder<VocabReview, VocabReview, QAfterSortBy> thenByIdDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'id', Sort.desc);
    });
  }

  QueryBuilder<VocabReview, VocabReview, QAfterSortBy> thenByRemembered() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'remembered', Sort.asc);
    });
  }

  QueryBuilder<VocabReview, VocabReview, QAfterSortBy> thenByRememberedDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'remembered', Sort.desc);
    });
  }

  QueryBuilder<VocabReview, VocabReview, QAfterSortBy> thenByResponseTimeMs() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'responseTimeMs', Sort.asc);
    });
  }

  QueryBuilder<VocabReview, VocabReview, QAfterSortBy>
      thenByResponseTimeMsDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'responseTimeMs', Sort.desc);
    });
  }

  QueryBuilder<VocabReview, VocabReview, QAfterSortBy> thenByReviewedAt() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'reviewedAt', Sort.asc);
    });
  }

  QueryBuilder<VocabReview, VocabReview, QAfterSortBy> thenByReviewedAtDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'reviewedAt', Sort.desc);
    });
  }

  QueryBuilder<VocabReview, VocabReview, QAfterSortBy> thenByVocabWordId() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'vocabWordId', Sort.asc);
    });
  }

  QueryBuilder<VocabReview, VocabReview, QAfterSortBy> thenByVocabWordIdDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'vocabWordId', Sort.desc);
    });
  }
}

extension VocabReviewQueryWhereDistinct
    on QueryBuilder<VocabReview, VocabReview, QDistinct> {
  QueryBuilder<VocabReview, VocabReview, QDistinct> distinctByRemembered() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'remembered');
    });
  }

  QueryBuilder<VocabReview, VocabReview, QDistinct> distinctByResponseTimeMs() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'responseTimeMs');
    });
  }

  QueryBuilder<VocabReview, VocabReview, QDistinct> distinctByReviewedAt() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'reviewedAt');
    });
  }

  QueryBuilder<VocabReview, VocabReview, QDistinct> distinctByVocabWordId() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'vocabWordId');
    });
  }
}

extension VocabReviewQueryProperty
    on QueryBuilder<VocabReview, VocabReview, QQueryProperty> {
  QueryBuilder<VocabReview, int, QQueryOperations> idProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'id');
    });
  }

  QueryBuilder<VocabReview, bool, QQueryOperations> rememberedProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'remembered');
    });
  }

  QueryBuilder<VocabReview, int, QQueryOperations> responseTimeMsProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'responseTimeMs');
    });
  }

  QueryBuilder<VocabReview, DateTime, QQueryOperations> reviewedAtProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'reviewedAt');
    });
  }

  QueryBuilder<VocabReview, int, QQueryOperations> vocabWordIdProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'vocabWordId');
    });
  }
}
