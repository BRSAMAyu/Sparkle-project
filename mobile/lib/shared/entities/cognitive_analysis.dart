/// 认知维度枚举 (Bloom's Taxonomy Revised)
import 'package:sparkle/core/services/i18n_service.dart';

enum CognitiveDimension {
  memory, // 记忆
  understanding, // 理解
  application, // 应用
  analysis, // 分析
  evaluation, // 评价
  creation // 创造
}

/// 认知维度扩展方法
extension CognitiveDimensionExtension on CognitiveDimension {
  String get label {
    final l10n = I18nService.instance.l10n;
    switch (this) {
      case CognitiveDimension.memory:
        return l10n.cognitiveDimensionMemory;
      case CognitiveDimension.understanding:
        return l10n.cognitiveDimensionUnderstanding;
      case CognitiveDimension.application:
        return l10n.cognitiveDimensionApplication;
      case CognitiveDimension.analysis:
        return l10n.cognitiveDimensionAnalysis;
      case CognitiveDimension.evaluation:
        return l10n.cognitiveDimensionEvaluation;
      case CognitiveDimension.creation:
        return l10n.cognitiveDimensionCreation;
    }
  }

  String get code => toString().split('.').last;
}
