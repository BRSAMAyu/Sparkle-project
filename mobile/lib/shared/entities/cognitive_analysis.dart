/// 认知维度枚举 (Bloom's Taxonomy Revised)
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
    switch (this) {
      case CognitiveDimension.memory:
        return '记忆';
      case CognitiveDimension.understanding:
        return '理解';
      case CognitiveDimension.application:
        return '应用';
      case CognitiveDimension.analysis:
        return '分析';
      case CognitiveDimension.evaluation:
        return '评价';
      case CognitiveDimension.creation:
        return '创造';
    }
  }

  String get code => toString().split('.').last;
}
