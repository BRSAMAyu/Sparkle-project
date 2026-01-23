// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'translation_record.dart';

// **************************************************************************
// IsarCollectionGenerator
// **************************************************************************

// coverage:ignore-file
// ignore_for_file: duplicate_ignore, non_constant_identifier_names, constant_identifier_names, invalid_use_of_protected_member, unnecessary_cast, prefer_const_constructors, lines_longer_than_80_chars, require_trailing_commas, inference_failure_on_function_invocation, unnecessary_parenthesis, unnecessary_raw_strings, unnecessary_null_checks, join_return_with_assignment, prefer_final_locals, avoid_js_rounded_ints, avoid_positional_boolean_parameters, always_specify_types

extension GetTranslationRecordCollection on Isar {
  IsarCollection<TranslationRecord> get translationRecords => this.collection();
}

const TranslationRecordSchema = CollectionSchema(
  name: r'TranslationRecord',
  id: -641002333582827518,
  properties: {
    r'createdAt': PropertySchema(
      id: 0,
      name: r'createdAt',
      type: IsarType.dateTime,
    ),
    r'isFavorited': PropertySchema(
      id: 1,
      name: r'isFavorited',
      type: IsarType.bool,
    ),
    r'lastViewedAt': PropertySchema(
      id: 2,
      name: r'lastViewedAt',
      type: IsarType.dateTime,
    ),
    r'originalText': PropertySchema(
      id: 3,
      name: r'originalText',
      type: IsarType.string,
    ),
    r'rating': PropertySchema(
      id: 4,
      name: r'rating',
      type: IsarType.long,
    ),
    r'sourceLanguage': PropertySchema(
      id: 5,
      name: r'sourceLanguage',
      type: IsarType.string,
    ),
    r'targetLanguage': PropertySchema(
      id: 6,
      name: r'targetLanguage',
      type: IsarType.string,
    ),
    r'translatedText': PropertySchema(
      id: 7,
      name: r'translatedText',
      type: IsarType.string,
    ),
    r'viewCount': PropertySchema(
      id: 8,
      name: r'viewCount',
      type: IsarType.long,
    )
  },
  estimateSize: _translationRecordEstimateSize,
  serialize: _translationRecordSerialize,
  deserialize: _translationRecordDeserialize,
  deserializeProp: _translationRecordDeserializeProp,
  idName: r'id',
  indexes: {
    r'originalText': IndexSchema(
      id: 6693995755071819741,
      name: r'originalText',
      unique: false,
      replace: false,
      properties: [
        IndexPropertySchema(
          name: r'originalText',
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
    )
  },
  links: {
    r'extractedWords': LinkSchema(
      id: -1741083970351173293,
      name: r'extractedWords',
      target: r'TranslationWordLink',
      single: false,
    )
  },
  embeddedSchemas: {},
  getId: _translationRecordGetId,
  getLinks: _translationRecordGetLinks,
  attach: _translationRecordAttach,
  version: '3.1.0+1',
);

int _translationRecordEstimateSize(
  TranslationRecord object,
  List<int> offsets,
  Map<Type, List<int>> allOffsets,
) {
  var bytesCount = offsets.last;
  bytesCount += 3 + object.originalText.length * 3;
  bytesCount += 3 + object.sourceLanguage.length * 3;
  bytesCount += 3 + object.targetLanguage.length * 3;
  bytesCount += 3 + object.translatedText.length * 3;
  return bytesCount;
}

void _translationRecordSerialize(
  TranslationRecord object,
  IsarWriter writer,
  List<int> offsets,
  Map<Type, List<int>> allOffsets,
) {
  writer.writeDateTime(offsets[0], object.createdAt);
  writer.writeBool(offsets[1], object.isFavorited);
  writer.writeDateTime(offsets[2], object.lastViewedAt);
  writer.writeString(offsets[3], object.originalText);
  writer.writeLong(offsets[4], object.rating);
  writer.writeString(offsets[5], object.sourceLanguage);
  writer.writeString(offsets[6], object.targetLanguage);
  writer.writeString(offsets[7], object.translatedText);
  writer.writeLong(offsets[8], object.viewCount);
}

TranslationRecord _translationRecordDeserialize(
  Id id,
  IsarReader reader,
  List<int> offsets,
  Map<Type, List<int>> allOffsets,
) {
  final object = TranslationRecord();
  object.createdAt = reader.readDateTime(offsets[0]);
  object.id = id;
  object.isFavorited = reader.readBool(offsets[1]);
  object.lastViewedAt = reader.readDateTimeOrNull(offsets[2]);
  object.originalText = reader.readString(offsets[3]);
  object.rating = reader.readLong(offsets[4]);
  object.sourceLanguage = reader.readString(offsets[5]);
  object.targetLanguage = reader.readString(offsets[6]);
  object.translatedText = reader.readString(offsets[7]);
  object.viewCount = reader.readLong(offsets[8]);
  return object;
}

P _translationRecordDeserializeProp<P>(
  IsarReader reader,
  int propertyId,
  int offset,
  Map<Type, List<int>> allOffsets,
) {
  switch (propertyId) {
    case 0:
      return (reader.readDateTime(offset)) as P;
    case 1:
      return (reader.readBool(offset)) as P;
    case 2:
      return (reader.readDateTimeOrNull(offset)) as P;
    case 3:
      return (reader.readString(offset)) as P;
    case 4:
      return (reader.readLong(offset)) as P;
    case 5:
      return (reader.readString(offset)) as P;
    case 6:
      return (reader.readString(offset)) as P;
    case 7:
      return (reader.readString(offset)) as P;
    case 8:
      return (reader.readLong(offset)) as P;
    default:
      throw IsarError('Unknown property with id $propertyId');
  }
}

Id _translationRecordGetId(TranslationRecord object) {
  return object.id;
}

List<IsarLinkBase<dynamic>> _translationRecordGetLinks(
    TranslationRecord object) {
  return [object.extractedWords];
}

void _translationRecordAttach(
    IsarCollection<dynamic> col, Id id, TranslationRecord object) {
  object.id = id;
  object.extractedWords.attach(
      col, col.isar.collection<TranslationWordLink>(), r'extractedWords', id);
}

extension TranslationRecordQueryWhereSort
    on QueryBuilder<TranslationRecord, TranslationRecord, QWhere> {
  QueryBuilder<TranslationRecord, TranslationRecord, QAfterWhere> anyId() {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(const IdWhereClause.any());
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterWhere>
      anyCreatedAt() {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(
        const IndexWhereClause.any(indexName: r'createdAt'),
      );
    });
  }
}

extension TranslationRecordQueryWhere
    on QueryBuilder<TranslationRecord, TranslationRecord, QWhereClause> {
  QueryBuilder<TranslationRecord, TranslationRecord, QAfterWhereClause>
      idEqualTo(Id id) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IdWhereClause.between(
        lower: id,
        upper: id,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterWhereClause>
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

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterWhereClause>
      idGreaterThan(Id id, {bool include = false}) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(
        IdWhereClause.greaterThan(lower: id, includeLower: include),
      );
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterWhereClause>
      idLessThan(Id id, {bool include = false}) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(
        IdWhereClause.lessThan(upper: id, includeUpper: include),
      );
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterWhereClause>
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

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterWhereClause>
      originalTextEqualTo(String originalText) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IndexWhereClause.equalTo(
        indexName: r'originalText',
        value: [originalText],
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterWhereClause>
      originalTextNotEqualTo(String originalText) {
    return QueryBuilder.apply(this, (query) {
      if (query.whereSort == Sort.asc) {
        return query
            .addWhereClause(IndexWhereClause.between(
              indexName: r'originalText',
              lower: [],
              upper: [originalText],
              includeUpper: false,
            ))
            .addWhereClause(IndexWhereClause.between(
              indexName: r'originalText',
              lower: [originalText],
              includeLower: false,
              upper: [],
            ));
      } else {
        return query
            .addWhereClause(IndexWhereClause.between(
              indexName: r'originalText',
              lower: [originalText],
              includeLower: false,
              upper: [],
            ))
            .addWhereClause(IndexWhereClause.between(
              indexName: r'originalText',
              lower: [],
              upper: [originalText],
              includeUpper: false,
            ));
      }
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterWhereClause>
      createdAtEqualTo(DateTime createdAt) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IndexWhereClause.equalTo(
        indexName: r'createdAt',
        value: [createdAt],
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterWhereClause>
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

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterWhereClause>
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

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterWhereClause>
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

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterWhereClause>
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
}

extension TranslationRecordQueryFilter
    on QueryBuilder<TranslationRecord, TranslationRecord, QFilterCondition> {
  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      createdAtEqualTo(DateTime value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'createdAt',
        value: value,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
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

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      createdAtLessThan(
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

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      createdAtBetween(
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

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      idEqualTo(Id value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'id',
        value: value,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
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

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
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

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
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

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      isFavoritedEqualTo(bool value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'isFavorited',
        value: value,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      lastViewedAtIsNull() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(const FilterCondition.isNull(
        property: r'lastViewedAt',
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      lastViewedAtIsNotNull() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(const FilterCondition.isNotNull(
        property: r'lastViewedAt',
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      lastViewedAtEqualTo(DateTime? value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'lastViewedAt',
        value: value,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      lastViewedAtGreaterThan(
    DateTime? value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'lastViewedAt',
        value: value,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      lastViewedAtLessThan(
    DateTime? value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'lastViewedAt',
        value: value,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      lastViewedAtBetween(
    DateTime? lower,
    DateTime? upper, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'lastViewedAt',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      originalTextEqualTo(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'originalText',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      originalTextGreaterThan(
    String value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'originalText',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      originalTextLessThan(
    String value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'originalText',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      originalTextBetween(
    String lower,
    String upper, {
    bool includeLower = true,
    bool includeUpper = true,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'originalText',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      originalTextStartsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.startsWith(
        property: r'originalText',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      originalTextEndsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.endsWith(
        property: r'originalText',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      originalTextContains(String value, {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.contains(
        property: r'originalText',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      originalTextMatches(String pattern, {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.matches(
        property: r'originalText',
        wildcard: pattern,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      originalTextIsEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'originalText',
        value: '',
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      originalTextIsNotEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        property: r'originalText',
        value: '',
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      ratingEqualTo(int value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'rating',
        value: value,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      ratingGreaterThan(
    int value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'rating',
        value: value,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      ratingLessThan(
    int value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'rating',
        value: value,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      ratingBetween(
    int lower,
    int upper, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'rating',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      sourceLanguageEqualTo(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'sourceLanguage',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      sourceLanguageGreaterThan(
    String value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'sourceLanguage',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      sourceLanguageLessThan(
    String value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'sourceLanguage',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      sourceLanguageBetween(
    String lower,
    String upper, {
    bool includeLower = true,
    bool includeUpper = true,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'sourceLanguage',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      sourceLanguageStartsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.startsWith(
        property: r'sourceLanguage',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      sourceLanguageEndsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.endsWith(
        property: r'sourceLanguage',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      sourceLanguageContains(String value, {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.contains(
        property: r'sourceLanguage',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      sourceLanguageMatches(String pattern, {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.matches(
        property: r'sourceLanguage',
        wildcard: pattern,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      sourceLanguageIsEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'sourceLanguage',
        value: '',
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      sourceLanguageIsNotEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        property: r'sourceLanguage',
        value: '',
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      targetLanguageEqualTo(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'targetLanguage',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      targetLanguageGreaterThan(
    String value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'targetLanguage',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      targetLanguageLessThan(
    String value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'targetLanguage',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      targetLanguageBetween(
    String lower,
    String upper, {
    bool includeLower = true,
    bool includeUpper = true,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'targetLanguage',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      targetLanguageStartsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.startsWith(
        property: r'targetLanguage',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      targetLanguageEndsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.endsWith(
        property: r'targetLanguage',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      targetLanguageContains(String value, {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.contains(
        property: r'targetLanguage',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      targetLanguageMatches(String pattern, {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.matches(
        property: r'targetLanguage',
        wildcard: pattern,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      targetLanguageIsEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'targetLanguage',
        value: '',
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      targetLanguageIsNotEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        property: r'targetLanguage',
        value: '',
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      translatedTextEqualTo(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'translatedText',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      translatedTextGreaterThan(
    String value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'translatedText',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      translatedTextLessThan(
    String value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'translatedText',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      translatedTextBetween(
    String lower,
    String upper, {
    bool includeLower = true,
    bool includeUpper = true,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'translatedText',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      translatedTextStartsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.startsWith(
        property: r'translatedText',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      translatedTextEndsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.endsWith(
        property: r'translatedText',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      translatedTextContains(String value, {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.contains(
        property: r'translatedText',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      translatedTextMatches(String pattern, {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.matches(
        property: r'translatedText',
        wildcard: pattern,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      translatedTextIsEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'translatedText',
        value: '',
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      translatedTextIsNotEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        property: r'translatedText',
        value: '',
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      viewCountEqualTo(int value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'viewCount',
        value: value,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      viewCountGreaterThan(
    int value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'viewCount',
        value: value,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      viewCountLessThan(
    int value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'viewCount',
        value: value,
      ));
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      viewCountBetween(
    int lower,
    int upper, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'viewCount',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
      ));
    });
  }
}

extension TranslationRecordQueryObject
    on QueryBuilder<TranslationRecord, TranslationRecord, QFilterCondition> {}

extension TranslationRecordQueryLinks
    on QueryBuilder<TranslationRecord, TranslationRecord, QFilterCondition> {
  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      extractedWords(FilterQuery<TranslationWordLink> q) {
    return QueryBuilder.apply(this, (query) {
      return query.link(q, r'extractedWords');
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      extractedWordsLengthEqualTo(int length) {
    return QueryBuilder.apply(this, (query) {
      return query.linkLength(r'extractedWords', length, true, length, true);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      extractedWordsIsEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.linkLength(r'extractedWords', 0, true, 0, true);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      extractedWordsIsNotEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.linkLength(r'extractedWords', 0, false, 999999, true);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      extractedWordsLengthLessThan(
    int length, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.linkLength(r'extractedWords', 0, true, length, include);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      extractedWordsLengthGreaterThan(
    int length, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.linkLength(r'extractedWords', length, include, 999999, true);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterFilterCondition>
      extractedWordsLengthBetween(
    int lower,
    int upper, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.linkLength(
          r'extractedWords', lower, includeLower, upper, includeUpper);
    });
  }
}

extension TranslationRecordQuerySortBy
    on QueryBuilder<TranslationRecord, TranslationRecord, QSortBy> {
  QueryBuilder<TranslationRecord, TranslationRecord, QAfterSortBy>
      sortByCreatedAt() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'createdAt', Sort.asc);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterSortBy>
      sortByCreatedAtDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'createdAt', Sort.desc);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterSortBy>
      sortByIsFavorited() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'isFavorited', Sort.asc);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterSortBy>
      sortByIsFavoritedDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'isFavorited', Sort.desc);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterSortBy>
      sortByLastViewedAt() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'lastViewedAt', Sort.asc);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterSortBy>
      sortByLastViewedAtDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'lastViewedAt', Sort.desc);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterSortBy>
      sortByOriginalText() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'originalText', Sort.asc);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterSortBy>
      sortByOriginalTextDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'originalText', Sort.desc);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterSortBy>
      sortByRating() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'rating', Sort.asc);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterSortBy>
      sortByRatingDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'rating', Sort.desc);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterSortBy>
      sortBySourceLanguage() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'sourceLanguage', Sort.asc);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterSortBy>
      sortBySourceLanguageDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'sourceLanguage', Sort.desc);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterSortBy>
      sortByTargetLanguage() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'targetLanguage', Sort.asc);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterSortBy>
      sortByTargetLanguageDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'targetLanguage', Sort.desc);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterSortBy>
      sortByTranslatedText() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'translatedText', Sort.asc);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterSortBy>
      sortByTranslatedTextDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'translatedText', Sort.desc);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterSortBy>
      sortByViewCount() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'viewCount', Sort.asc);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterSortBy>
      sortByViewCountDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'viewCount', Sort.desc);
    });
  }
}

extension TranslationRecordQuerySortThenBy
    on QueryBuilder<TranslationRecord, TranslationRecord, QSortThenBy> {
  QueryBuilder<TranslationRecord, TranslationRecord, QAfterSortBy>
      thenByCreatedAt() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'createdAt', Sort.asc);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterSortBy>
      thenByCreatedAtDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'createdAt', Sort.desc);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterSortBy> thenById() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'id', Sort.asc);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterSortBy>
      thenByIdDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'id', Sort.desc);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterSortBy>
      thenByIsFavorited() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'isFavorited', Sort.asc);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterSortBy>
      thenByIsFavoritedDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'isFavorited', Sort.desc);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterSortBy>
      thenByLastViewedAt() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'lastViewedAt', Sort.asc);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterSortBy>
      thenByLastViewedAtDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'lastViewedAt', Sort.desc);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterSortBy>
      thenByOriginalText() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'originalText', Sort.asc);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterSortBy>
      thenByOriginalTextDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'originalText', Sort.desc);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterSortBy>
      thenByRating() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'rating', Sort.asc);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterSortBy>
      thenByRatingDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'rating', Sort.desc);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterSortBy>
      thenBySourceLanguage() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'sourceLanguage', Sort.asc);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterSortBy>
      thenBySourceLanguageDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'sourceLanguage', Sort.desc);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterSortBy>
      thenByTargetLanguage() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'targetLanguage', Sort.asc);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterSortBy>
      thenByTargetLanguageDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'targetLanguage', Sort.desc);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterSortBy>
      thenByTranslatedText() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'translatedText', Sort.asc);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterSortBy>
      thenByTranslatedTextDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'translatedText', Sort.desc);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterSortBy>
      thenByViewCount() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'viewCount', Sort.asc);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QAfterSortBy>
      thenByViewCountDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'viewCount', Sort.desc);
    });
  }
}

extension TranslationRecordQueryWhereDistinct
    on QueryBuilder<TranslationRecord, TranslationRecord, QDistinct> {
  QueryBuilder<TranslationRecord, TranslationRecord, QDistinct>
      distinctByCreatedAt() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'createdAt');
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QDistinct>
      distinctByIsFavorited() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'isFavorited');
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QDistinct>
      distinctByLastViewedAt() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'lastViewedAt');
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QDistinct>
      distinctByOriginalText({bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'originalText', caseSensitive: caseSensitive);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QDistinct>
      distinctByRating() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'rating');
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QDistinct>
      distinctBySourceLanguage({bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'sourceLanguage',
          caseSensitive: caseSensitive);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QDistinct>
      distinctByTargetLanguage({bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'targetLanguage',
          caseSensitive: caseSensitive);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QDistinct>
      distinctByTranslatedText({bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'translatedText',
          caseSensitive: caseSensitive);
    });
  }

  QueryBuilder<TranslationRecord, TranslationRecord, QDistinct>
      distinctByViewCount() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'viewCount');
    });
  }
}

extension TranslationRecordQueryProperty
    on QueryBuilder<TranslationRecord, TranslationRecord, QQueryProperty> {
  QueryBuilder<TranslationRecord, int, QQueryOperations> idProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'id');
    });
  }

  QueryBuilder<TranslationRecord, DateTime, QQueryOperations>
      createdAtProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'createdAt');
    });
  }

  QueryBuilder<TranslationRecord, bool, QQueryOperations>
      isFavoritedProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'isFavorited');
    });
  }

  QueryBuilder<TranslationRecord, DateTime?, QQueryOperations>
      lastViewedAtProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'lastViewedAt');
    });
  }

  QueryBuilder<TranslationRecord, String, QQueryOperations>
      originalTextProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'originalText');
    });
  }

  QueryBuilder<TranslationRecord, int, QQueryOperations> ratingProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'rating');
    });
  }

  QueryBuilder<TranslationRecord, String, QQueryOperations>
      sourceLanguageProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'sourceLanguage');
    });
  }

  QueryBuilder<TranslationRecord, String, QQueryOperations>
      targetLanguageProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'targetLanguage');
    });
  }

  QueryBuilder<TranslationRecord, String, QQueryOperations>
      translatedTextProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'translatedText');
    });
  }

  QueryBuilder<TranslationRecord, int, QQueryOperations> viewCountProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'viewCount');
    });
  }
}

// coverage:ignore-file
// ignore_for_file: duplicate_ignore, non_constant_identifier_names, constant_identifier_names, invalid_use_of_protected_member, unnecessary_cast, prefer_const_constructors, lines_longer_than_80_chars, require_trailing_commas, inference_failure_on_function_invocation, unnecessary_parenthesis, unnecessary_raw_strings, unnecessary_null_checks, join_return_with_assignment, prefer_final_locals, avoid_js_rounded_ints, avoid_positional_boolean_parameters, always_specify_types

extension GetTranslationWordLinkCollection on Isar {
  IsarCollection<TranslationWordLink> get translationWordLinks =>
      this.collection();
}

const TranslationWordLinkSchema = CollectionSchema(
  name: r'TranslationWordLink',
  id: -2052165459506868265,
  properties: {
    r'translationRecordId': PropertySchema(
      id: 0,
      name: r'translationRecordId',
      type: IsarType.long,
    ),
    r'word': PropertySchema(
      id: 1,
      name: r'word',
      type: IsarType.string,
    )
  },
  estimateSize: _translationWordLinkEstimateSize,
  serialize: _translationWordLinkSerialize,
  deserialize: _translationWordLinkDeserialize,
  deserializeProp: _translationWordLinkDeserializeProp,
  idName: r'id',
  indexes: {
    r'translationRecordId': IndexSchema(
      id: -5590309821998644523,
      name: r'translationRecordId',
      unique: false,
      replace: false,
      properties: [
        IndexPropertySchema(
          name: r'translationRecordId',
          type: IndexType.value,
          caseSensitive: false,
        )
      ],
    )
  },
  links: {},
  embeddedSchemas: {},
  getId: _translationWordLinkGetId,
  getLinks: _translationWordLinkGetLinks,
  attach: _translationWordLinkAttach,
  version: '3.1.0+1',
);

int _translationWordLinkEstimateSize(
  TranslationWordLink object,
  List<int> offsets,
  Map<Type, List<int>> allOffsets,
) {
  var bytesCount = offsets.last;
  bytesCount += 3 + object.word.length * 3;
  return bytesCount;
}

void _translationWordLinkSerialize(
  TranslationWordLink object,
  IsarWriter writer,
  List<int> offsets,
  Map<Type, List<int>> allOffsets,
) {
  writer.writeLong(offsets[0], object.translationRecordId);
  writer.writeString(offsets[1], object.word);
}

TranslationWordLink _translationWordLinkDeserialize(
  Id id,
  IsarReader reader,
  List<int> offsets,
  Map<Type, List<int>> allOffsets,
) {
  final object = TranslationWordLink();
  object.id = id;
  object.translationRecordId = reader.readLong(offsets[0]);
  object.word = reader.readString(offsets[1]);
  return object;
}

P _translationWordLinkDeserializeProp<P>(
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
    default:
      throw IsarError('Unknown property with id $propertyId');
  }
}

Id _translationWordLinkGetId(TranslationWordLink object) {
  return object.id;
}

List<IsarLinkBase<dynamic>> _translationWordLinkGetLinks(
    TranslationWordLink object) {
  return [];
}

void _translationWordLinkAttach(
    IsarCollection<dynamic> col, Id id, TranslationWordLink object) {
  object.id = id;
}

extension TranslationWordLinkQueryWhereSort
    on QueryBuilder<TranslationWordLink, TranslationWordLink, QWhere> {
  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterWhere> anyId() {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(const IdWhereClause.any());
    });
  }

  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterWhere>
      anyTranslationRecordId() {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(
        const IndexWhereClause.any(indexName: r'translationRecordId'),
      );
    });
  }
}

extension TranslationWordLinkQueryWhere
    on QueryBuilder<TranslationWordLink, TranslationWordLink, QWhereClause> {
  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterWhereClause>
      idEqualTo(Id id) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IdWhereClause.between(
        lower: id,
        upper: id,
      ));
    });
  }

  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterWhereClause>
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

  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterWhereClause>
      idGreaterThan(Id id, {bool include = false}) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(
        IdWhereClause.greaterThan(lower: id, includeLower: include),
      );
    });
  }

  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterWhereClause>
      idLessThan(Id id, {bool include = false}) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(
        IdWhereClause.lessThan(upper: id, includeUpper: include),
      );
    });
  }

  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterWhereClause>
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

  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterWhereClause>
      translationRecordIdEqualTo(int translationRecordId) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IndexWhereClause.equalTo(
        indexName: r'translationRecordId',
        value: [translationRecordId],
      ));
    });
  }

  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterWhereClause>
      translationRecordIdNotEqualTo(int translationRecordId) {
    return QueryBuilder.apply(this, (query) {
      if (query.whereSort == Sort.asc) {
        return query
            .addWhereClause(IndexWhereClause.between(
              indexName: r'translationRecordId',
              lower: [],
              upper: [translationRecordId],
              includeUpper: false,
            ))
            .addWhereClause(IndexWhereClause.between(
              indexName: r'translationRecordId',
              lower: [translationRecordId],
              includeLower: false,
              upper: [],
            ));
      } else {
        return query
            .addWhereClause(IndexWhereClause.between(
              indexName: r'translationRecordId',
              lower: [translationRecordId],
              includeLower: false,
              upper: [],
            ))
            .addWhereClause(IndexWhereClause.between(
              indexName: r'translationRecordId',
              lower: [],
              upper: [translationRecordId],
              includeUpper: false,
            ));
      }
    });
  }

  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterWhereClause>
      translationRecordIdGreaterThan(
    int translationRecordId, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IndexWhereClause.between(
        indexName: r'translationRecordId',
        lower: [translationRecordId],
        includeLower: include,
        upper: [],
      ));
    });
  }

  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterWhereClause>
      translationRecordIdLessThan(
    int translationRecordId, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IndexWhereClause.between(
        indexName: r'translationRecordId',
        lower: [],
        upper: [translationRecordId],
        includeUpper: include,
      ));
    });
  }

  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterWhereClause>
      translationRecordIdBetween(
    int lowerTranslationRecordId,
    int upperTranslationRecordId, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IndexWhereClause.between(
        indexName: r'translationRecordId',
        lower: [lowerTranslationRecordId],
        includeLower: includeLower,
        upper: [upperTranslationRecordId],
        includeUpper: includeUpper,
      ));
    });
  }
}

extension TranslationWordLinkQueryFilter on QueryBuilder<TranslationWordLink,
    TranslationWordLink, QFilterCondition> {
  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterFilterCondition>
      idEqualTo(Id value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'id',
        value: value,
      ));
    });
  }

  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterFilterCondition>
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

  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterFilterCondition>
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

  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterFilterCondition>
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

  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterFilterCondition>
      translationRecordIdEqualTo(int value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'translationRecordId',
        value: value,
      ));
    });
  }

  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterFilterCondition>
      translationRecordIdGreaterThan(
    int value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'translationRecordId',
        value: value,
      ));
    });
  }

  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterFilterCondition>
      translationRecordIdLessThan(
    int value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'translationRecordId',
        value: value,
      ));
    });
  }

  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterFilterCondition>
      translationRecordIdBetween(
    int lower,
    int upper, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'translationRecordId',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
      ));
    });
  }

  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterFilterCondition>
      wordEqualTo(
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

  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterFilterCondition>
      wordGreaterThan(
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

  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterFilterCondition>
      wordLessThan(
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

  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterFilterCondition>
      wordBetween(
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

  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterFilterCondition>
      wordStartsWith(
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

  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterFilterCondition>
      wordEndsWith(
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

  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterFilterCondition>
      wordContains(String value, {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.contains(
        property: r'word',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterFilterCondition>
      wordMatches(String pattern, {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.matches(
        property: r'word',
        wildcard: pattern,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterFilterCondition>
      wordIsEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'word',
        value: '',
      ));
    });
  }

  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterFilterCondition>
      wordIsNotEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        property: r'word',
        value: '',
      ));
    });
  }
}

extension TranslationWordLinkQueryObject on QueryBuilder<TranslationWordLink,
    TranslationWordLink, QFilterCondition> {}

extension TranslationWordLinkQueryLinks on QueryBuilder<TranslationWordLink,
    TranslationWordLink, QFilterCondition> {}

extension TranslationWordLinkQuerySortBy
    on QueryBuilder<TranslationWordLink, TranslationWordLink, QSortBy> {
  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterSortBy>
      sortByTranslationRecordId() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'translationRecordId', Sort.asc);
    });
  }

  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterSortBy>
      sortByTranslationRecordIdDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'translationRecordId', Sort.desc);
    });
  }

  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterSortBy>
      sortByWord() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'word', Sort.asc);
    });
  }

  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterSortBy>
      sortByWordDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'word', Sort.desc);
    });
  }
}

extension TranslationWordLinkQuerySortThenBy
    on QueryBuilder<TranslationWordLink, TranslationWordLink, QSortThenBy> {
  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterSortBy>
      thenById() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'id', Sort.asc);
    });
  }

  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterSortBy>
      thenByIdDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'id', Sort.desc);
    });
  }

  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterSortBy>
      thenByTranslationRecordId() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'translationRecordId', Sort.asc);
    });
  }

  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterSortBy>
      thenByTranslationRecordIdDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'translationRecordId', Sort.desc);
    });
  }

  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterSortBy>
      thenByWord() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'word', Sort.asc);
    });
  }

  QueryBuilder<TranslationWordLink, TranslationWordLink, QAfterSortBy>
      thenByWordDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'word', Sort.desc);
    });
  }
}

extension TranslationWordLinkQueryWhereDistinct
    on QueryBuilder<TranslationWordLink, TranslationWordLink, QDistinct> {
  QueryBuilder<TranslationWordLink, TranslationWordLink, QDistinct>
      distinctByTranslationRecordId() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'translationRecordId');
    });
  }

  QueryBuilder<TranslationWordLink, TranslationWordLink, QDistinct>
      distinctByWord({bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'word', caseSensitive: caseSensitive);
    });
  }
}

extension TranslationWordLinkQueryProperty
    on QueryBuilder<TranslationWordLink, TranslationWordLink, QQueryProperty> {
  QueryBuilder<TranslationWordLink, int, QQueryOperations> idProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'id');
    });
  }

  QueryBuilder<TranslationWordLink, int, QQueryOperations>
      translationRecordIdProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'translationRecordId');
    });
  }

  QueryBuilder<TranslationWordLink, String, QQueryOperations> wordProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'word');
    });
  }
}
