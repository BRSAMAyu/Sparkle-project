//
//  Generated code. Do not modify.
//  source: google/protobuf/java_features.proto
//
// @dart = 2.12

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_final_fields
// ignore_for_file: unnecessary_import, unnecessary_this, unused_import

import 'dart:core' as $core;

import 'package:protobuf/protobuf.dart' as $pb;

/// The UTF8 validation strategy to use.
class JavaFeatures_Utf8Validation extends $pb.ProtobufEnum {
  static const JavaFeatures_Utf8Validation UTF8_VALIDATION_UNKNOWN = JavaFeatures_Utf8Validation._(0, _omitEnumNames ? '' : 'UTF8_VALIDATION_UNKNOWN');
  static const JavaFeatures_Utf8Validation DEFAULT = JavaFeatures_Utf8Validation._(1, _omitEnumNames ? '' : 'DEFAULT');
  static const JavaFeatures_Utf8Validation VERIFY = JavaFeatures_Utf8Validation._(2, _omitEnumNames ? '' : 'VERIFY');

  static const $core.List<JavaFeatures_Utf8Validation> values = <JavaFeatures_Utf8Validation> [
    UTF8_VALIDATION_UNKNOWN,
    DEFAULT,
    VERIFY,
  ];

  static final $core.Map<$core.int, JavaFeatures_Utf8Validation> _byValue = $pb.ProtobufEnum.initByValue(values);
  static JavaFeatures_Utf8Validation? valueOf($core.int value) => _byValue[value];

  const JavaFeatures_Utf8Validation._($core.int v, $core.String n) : super(v, n);
}

class JavaFeatures_NestInFileClassFeature_NestInFileClass extends $pb.ProtobufEnum {
  static const JavaFeatures_NestInFileClassFeature_NestInFileClass NEST_IN_FILE_CLASS_UNKNOWN = JavaFeatures_NestInFileClassFeature_NestInFileClass._(0, _omitEnumNames ? '' : 'NEST_IN_FILE_CLASS_UNKNOWN');
  static const JavaFeatures_NestInFileClassFeature_NestInFileClass NO = JavaFeatures_NestInFileClassFeature_NestInFileClass._(1, _omitEnumNames ? '' : 'NO');
  static const JavaFeatures_NestInFileClassFeature_NestInFileClass YES = JavaFeatures_NestInFileClassFeature_NestInFileClass._(2, _omitEnumNames ? '' : 'YES');
  static const JavaFeatures_NestInFileClassFeature_NestInFileClass LEGACY = JavaFeatures_NestInFileClassFeature_NestInFileClass._(3, _omitEnumNames ? '' : 'LEGACY');

  static const $core.List<JavaFeatures_NestInFileClassFeature_NestInFileClass> values = <JavaFeatures_NestInFileClassFeature_NestInFileClass> [
    NEST_IN_FILE_CLASS_UNKNOWN,
    NO,
    YES,
    LEGACY,
  ];

  static final $core.Map<$core.int, JavaFeatures_NestInFileClassFeature_NestInFileClass> _byValue = $pb.ProtobufEnum.initByValue(values);
  static JavaFeatures_NestInFileClassFeature_NestInFileClass? valueOf($core.int value) => _byValue[value];

  const JavaFeatures_NestInFileClassFeature_NestInFileClass._($core.int v, $core.String n) : super(v, n);
}


const _omitEnumNames = $core.bool.fromEnvironment('protobuf.omit_enum_names');
