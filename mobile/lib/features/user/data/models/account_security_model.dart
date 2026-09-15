class SocialAccountStatusModel {
  SocialAccountStatusModel({
    required this.provider,
    required this.linked,
  });

  factory SocialAccountStatusModel.fromJson(Map<String, dynamic> json) =>
      SocialAccountStatusModel(
        provider: json['provider'] as String? ?? '',
        linked: json['linked'] as bool? ?? false,
      );

  final String provider;
  final bool linked;
}

class UserSessionModel {
  UserSessionModel({
    required this.sessionId,
    required this.isActive,
    required this.isCurrent,
    required this.createdAt,
    required this.lastActiveAt,
    this.deviceId,
    this.deviceName,
    this.deviceType,
    this.ipAddress,
    this.userAgent,
  });

  factory UserSessionModel.fromJson(Map<String, dynamic> json) =>
      UserSessionModel(
        sessionId: json['session_id'] as String? ?? '',
        isActive: json['is_active'] as bool? ?? false,
        isCurrent: json['is_current'] as bool? ?? false,
        createdAt: DateTime.parse(json['created_at'] as String),
        lastActiveAt: DateTime.parse(json['last_active_at'] as String),
        deviceId: json['device_id'] as String?,
        deviceName: json['device_name'] as String?,
        deviceType: json['device_type'] as String?,
        ipAddress: json['ip_address'] as String?,
        userAgent: json['user_agent'] as String?,
      );

  final String sessionId;
  final String? deviceId;
  final String? deviceName;
  final String? deviceType;
  final String? ipAddress;
  final String? userAgent;
  final bool isActive;
  final bool isCurrent;
  final DateTime createdAt;
  final DateTime lastActiveAt;
}

class AuthAuditLogModel {
  AuthAuditLogModel({
    required this.action,
    required this.occurredAt,
    this.ipAddress,
    this.userAgent,
    this.metadata,
  });

  factory AuthAuditLogModel.fromJson(Map<String, dynamic> json) =>
      AuthAuditLogModel(
        action: json['action'] as String? ?? '',
        occurredAt: DateTime.parse(json['occurred_at'] as String),
        ipAddress: json['ip_address'] as String?,
        userAgent: json['user_agent'] as String?,
        metadata: json['metadata'] as Map<String, dynamic>?,
      );

  final String action;
  final String? ipAddress;
  final String? userAgent;
  final Map<String, dynamic>? metadata;
  final DateTime occurredAt;
}
