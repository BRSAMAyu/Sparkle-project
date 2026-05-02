class DirectiveAuditEntry {
  const DirectiveAuditEntry({
    required this.traceId,
    required this.directiveId,
    required this.directiveType,
    required this.displayType,
    required this.createdAt,
    required this.targetModule,
    required this.scope,
    required this.userVisibleReason,
    this.triggerSignal,
    this.policy,
    this.actualResult,
    this.rawDirective = const <String, dynamic>{},
  });

  factory DirectiveAuditEntry.fromJson(Map<String, dynamic> json) {
    Map<String, dynamic>? optionalMap(String key) {
      final value = json[key];
      if (value is Map<String, dynamic>) return value;
      if (value is Map) return Map<String, dynamic>.from(value);
      return null;
    }

    return DirectiveAuditEntry(
      traceId: (json['trace_id'] ?? json['traceId'] ?? '').toString(),
      directiveId:
          (json['directive_id'] ?? json['directiveId'] ?? '').toString(),
      directiveType:
          (json['directive_type'] ?? json['directiveType'] ?? '').toString(),
      displayType:
          (json['display_type'] ?? json['displayType'] ?? '').toString(),
      createdAt: DateTime.tryParse(
            (json['created_at'] ?? json['createdAt'] ?? '').toString(),
          ) ??
          DateTime.fromMillisecondsSinceEpoch(0),
      targetModule:
          (json['target_module'] ?? json['targetModule'] ?? '').toString(),
      scope: (json['scope'] ?? '').toString(),
      userVisibleReason:
          (json['user_visible_reason'] ?? json['userVisibleReason'] ?? '')
              .toString(),
      triggerSignal:
          optionalMap('trigger_signal') ?? optionalMap('triggerSignal'),
      policy: optionalMap('policy'),
      actualResult: optionalMap('actual_result') ?? optionalMap('actualResult'),
      rawDirective: optionalMap('raw_directive') ??
          optionalMap('rawDirective') ??
          const <String, dynamic>{},
    );
  }

  final String traceId;
  final String directiveId;
  final String directiveType;
  final String displayType;
  final DateTime createdAt;
  final String targetModule;
  final String scope;
  final String userVisibleReason;
  final Map<String, dynamic>? triggerSignal;
  final Map<String, dynamic>? policy;
  final Map<String, dynamic>? actualResult;
  final Map<String, dynamic> rawDirective;

  bool get wasApplied => actualResult?['applied'] == true;
}

class DirectiveAuditFilter {
  const DirectiveAuditFilter({
    this.directiveType,
    this.hours = 24 * 7,
    this.limit = 20,
  });

  final String? directiveType;
  final int hours;
  final int limit;

  @override
  bool operator ==(Object other) =>
      other is DirectiveAuditFilter &&
      other.directiveType == directiveType &&
      other.hours == hours &&
      other.limit == limit;

  @override
  int get hashCode => Object.hash(directiveType, hours, limit);
}
