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

import 'java_features.pbenum.dart';

export 'java_features.pbenum.dart';

class JavaFeatures_NestInFileClassFeature extends $pb.GeneratedMessage {
  factory JavaFeatures_NestInFileClassFeature() => create();
  JavaFeatures_NestInFileClassFeature._() : super();
  factory JavaFeatures_NestInFileClassFeature.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory JavaFeatures_NestInFileClassFeature.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'JavaFeatures.NestInFileClassFeature', package: const $pb.PackageName(_omitMessageNames ? '' : 'pb'), createEmptyInstance: create)
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  JavaFeatures_NestInFileClassFeature clone() => JavaFeatures_NestInFileClassFeature()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  JavaFeatures_NestInFileClassFeature copyWith(void Function(JavaFeatures_NestInFileClassFeature) updates) => super.copyWith((message) => updates(message as JavaFeatures_NestInFileClassFeature)) as JavaFeatures_NestInFileClassFeature;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static JavaFeatures_NestInFileClassFeature create() => JavaFeatures_NestInFileClassFeature._();
  JavaFeatures_NestInFileClassFeature createEmptyInstance() => create();
  static $pb.PbList<JavaFeatures_NestInFileClassFeature> createRepeated() => $pb.PbList<JavaFeatures_NestInFileClassFeature>();
  @$core.pragma('dart2js:noInline')
  static JavaFeatures_NestInFileClassFeature getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<JavaFeatures_NestInFileClassFeature>(create);
  static JavaFeatures_NestInFileClassFeature? _defaultInstance;
}

class JavaFeatures extends $pb.GeneratedMessage {
  factory JavaFeatures({
    $core.bool? legacyClosedEnum,
    JavaFeatures_Utf8Validation? utf8Validation,
    $core.bool? largeEnum,
    $core.bool? useOldOuterClassnameDefault,
    JavaFeatures_NestInFileClassFeature_NestInFileClass? nestInFileClass,
  }) {
    final $result = create();
    if (legacyClosedEnum != null) {
      $result.legacyClosedEnum = legacyClosedEnum;
    }
    if (utf8Validation != null) {
      $result.utf8Validation = utf8Validation;
    }
    if (largeEnum != null) {
      $result.largeEnum = largeEnum;
    }
    if (useOldOuterClassnameDefault != null) {
      $result.useOldOuterClassnameDefault = useOldOuterClassnameDefault;
    }
    if (nestInFileClass != null) {
      $result.nestInFileClass = nestInFileClass;
    }
    return $result;
  }
  JavaFeatures._() : super();
  factory JavaFeatures.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory JavaFeatures.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'JavaFeatures', package: const $pb.PackageName(_omitMessageNames ? '' : 'pb'), createEmptyInstance: create)
    ..aOB(1, _omitFieldNames ? '' : 'legacyClosedEnum')
    ..e<JavaFeatures_Utf8Validation>(2, _omitFieldNames ? '' : 'utf8Validation', $pb.PbFieldType.OE, defaultOrMaker: JavaFeatures_Utf8Validation.UTF8_VALIDATION_UNKNOWN, valueOf: JavaFeatures_Utf8Validation.valueOf, enumValues: JavaFeatures_Utf8Validation.values)
    ..aOB(3, _omitFieldNames ? '' : 'largeEnum')
    ..aOB(4, _omitFieldNames ? '' : 'useOldOuterClassnameDefault')
    ..e<JavaFeatures_NestInFileClassFeature_NestInFileClass>(5, _omitFieldNames ? '' : 'nestInFileClass', $pb.PbFieldType.OE, defaultOrMaker: JavaFeatures_NestInFileClassFeature_NestInFileClass.NEST_IN_FILE_CLASS_UNKNOWN, valueOf: JavaFeatures_NestInFileClassFeature_NestInFileClass.valueOf, enumValues: JavaFeatures_NestInFileClassFeature_NestInFileClass.values)
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  JavaFeatures clone() => JavaFeatures()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  JavaFeatures copyWith(void Function(JavaFeatures) updates) => super.copyWith((message) => updates(message as JavaFeatures)) as JavaFeatures;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static JavaFeatures create() => JavaFeatures._();
  JavaFeatures createEmptyInstance() => create();
  static $pb.PbList<JavaFeatures> createRepeated() => $pb.PbList<JavaFeatures>();
  @$core.pragma('dart2js:noInline')
  static JavaFeatures getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<JavaFeatures>(create);
  static JavaFeatures? _defaultInstance;

  /// Whether or not to treat an enum field as closed.  This option is only
  /// applicable to enum fields, and will be removed in the future.  It is
  /// consistent with the legacy behavior of using proto3 enum types for proto2
  /// fields.
  @$pb.TagNumber(1)
  $core.bool get legacyClosedEnum => $_getBF(0);
  @$pb.TagNumber(1)
  set legacyClosedEnum($core.bool v) { $_setBool(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasLegacyClosedEnum() => $_has(0);
  @$pb.TagNumber(1)
  void clearLegacyClosedEnum() => clearField(1);

  @$pb.TagNumber(2)
  JavaFeatures_Utf8Validation get utf8Validation => $_getN(1);
  @$pb.TagNumber(2)
  set utf8Validation(JavaFeatures_Utf8Validation v) { setField(2, v); }
  @$pb.TagNumber(2)
  $core.bool hasUtf8Validation() => $_has(1);
  @$pb.TagNumber(2)
  void clearUtf8Validation() => clearField(2);

  /// Allows creation of large Java enums, extending beyond the standard
  /// constant limits imposed by the Java language.
  @$pb.TagNumber(3)
  $core.bool get largeEnum => $_getBF(2);
  @$pb.TagNumber(3)
  set largeEnum($core.bool v) { $_setBool(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasLargeEnum() => $_has(2);
  @$pb.TagNumber(3)
  void clearLargeEnum() => clearField(3);

  ///  Whether to use the old default outer class name scheme, or the new feature
  ///  which adds a "Proto" suffix to the outer class name.
  ///
  ///  Users will not be able to set this option, because we removed it in the
  ///  same edition that it was introduced. But we use it to determine which
  ///  naming scheme to use for outer class name defaults.
  @$pb.TagNumber(4)
  $core.bool get useOldOuterClassnameDefault => $_getBF(3);
  @$pb.TagNumber(4)
  set useOldOuterClassnameDefault($core.bool v) { $_setBool(3, v); }
  @$pb.TagNumber(4)
  $core.bool hasUseOldOuterClassnameDefault() => $_has(3);
  @$pb.TagNumber(4)
  void clearUseOldOuterClassnameDefault() => clearField(4);

  /// Whether to nest the generated class in the generated file class. This is
  /// only applicable to *top-level* messages, enums, and services.
  @$pb.TagNumber(5)
  JavaFeatures_NestInFileClassFeature_NestInFileClass get nestInFileClass => $_getN(4);
  @$pb.TagNumber(5)
  set nestInFileClass(JavaFeatures_NestInFileClassFeature_NestInFileClass v) { setField(5, v); }
  @$pb.TagNumber(5)
  $core.bool hasNestInFileClass() => $_has(4);
  @$pb.TagNumber(5)
  void clearNestInFileClass() => clearField(5);
}

class Java_features {
  static final java = $pb.Extension<JavaFeatures>(_omitMessageNames ? '' : 'google.protobuf.FeatureSet', _omitFieldNames ? '' : 'java', 1001, $pb.PbFieldType.OM, defaultOrMaker: JavaFeatures.getDefault, subBuilder: JavaFeatures.create);
  static void registerAllExtensions($pb.ExtensionRegistry registry) {
    registry.add(java);
  }
}


const _omitFieldNames = $core.bool.fromEnvironment('protobuf.omit_field_names');
const _omitMessageNames = $core.bool.fromEnvironment('protobuf.omit_message_names');
